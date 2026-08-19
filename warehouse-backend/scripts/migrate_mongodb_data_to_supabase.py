"""Merge all WMS MongoDB records into Supabase/PostgreSQL.

The migration keeps MongoDB identifiers, maps duplicate users by email, preserves
existing Supabase password hashes, and never deletes destination records.
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import asyncpg
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import settings
from core.database.postgres import get_postgres_dsn


COLLECTIONS = (
    ("users", "users"),
    ("warehouses", "warehouses"),
    ("products", "products"),
    ("sellers", "sellers"),
    ("inbound_shipments", "inbound_shipments"),
    ("damage_reports", "damage_reports"),
    ("inventory", "inventory"),
    ("inventory_transactions", "inventory_transactions"),
    ("orders", "orders"),
    ("packages", "packages"),
    ("issue_requests", "issue_requests"),
    ("audit_logs", "audit_logs"),
    ("revoked_tokens", "revoked_tokens"),
)

USER_REFERENCE_FIELDS = {
    "manager_id", "created_by", "received_by", "receiving_started_by",
    "reported_by", "resolved_by", "performed_by", "user_id", "approved_by",
    "packed_by", "shipped_by", "picked_by", "raised_by",
}


def normalize(value: Any) -> Any:
    """Convert BSON-specific values into PostgreSQL-compatible structures."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


async def table_columns(connection: asyncpg.Connection, table: str) -> dict[str, dict[str, str]]:
    rows = await connection.fetch(
        "SELECT column_name, data_type, udt_name FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=$1",
        table,
    )
    return {row["column_name"]: dict(row) for row in rows}


def convert_value(value: Any, metadata: dict[str, str]) -> Any:
    if value is None:
        return None
    data_type = metadata["data_type"]
    if data_type == "jsonb":
        return json.dumps(
            normalize(value),
            default=lambda item: item.isoformat() if isinstance(item, datetime) else str(item),
        )
    if "timestamp" in data_type:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
    if data_type == "text" and not isinstance(value, str):
        return str(value)
    return value


def prepare_document(
    document: dict[str, Any], columns: dict[str, dict[str, str]], user_id_map: dict[str, str],
    warehouse_id_map: dict[str, str] | None = None, own_id_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = normalize(document)
    source_id = str(source.pop("_id", source.get("id")))
    source["id"] = (own_id_map or {}).get(source_id, source_id)
    for field in USER_REFERENCE_FIELDS:
        if source.get(field) is not None:
            source[field] = user_id_map.get(str(source[field]), str(source[field]))
    for field in ("warehouse_id", "assigned_warehouse_id"):
        if source.get(field) is not None:
            source[field] = (warehouse_id_map or {}).get(str(source[field]), str(source[field]))
    return {
        key: convert_value(value, columns[key])
        for key, value in source.items()
        if key in columns
    }


async def upsert_by_id(connection: asyncpg.Connection, table: str, document: dict[str, Any]) -> None:
    columns = list(document)
    names = ", ".join(f'"{column}"' for column in columns)
    placeholders = ", ".join(f"${index}" for index in range(1, len(columns) + 1))
    updates = ", ".join(f'"{column}"=EXCLUDED."{column}"' for column in columns if column != "id")
    sql = f'INSERT INTO "{table}" ({names}) VALUES ({placeholders}) ON CONFLICT (id) DO UPDATE SET {updates}'
    await connection.execute(sql, *(document[column] for column in columns))


async def migrate_users(
    connection: asyncpg.Connection, documents: list[dict[str, Any]], apply: bool,
    warehouse_id_map: dict[str, str],
) -> dict[str, str]:
    columns = await table_columns(connection, "users")
    existing = {row["email"].lower(): dict(row) for row in await connection.fetch("SELECT * FROM users")}
    user_id_map: dict[str, str] = {}
    for raw in documents:
        source_id = str(raw["_id"])
        email = str(raw["email"]).strip().lower()
        destination = existing.get(email)
        user_id_map[source_id] = str(destination["id"]) if destination else source_id
    if not apply:
        duplicates = sum(1 for item in documents if str(item["email"]).strip().lower() in existing)
        print(f"users: source={len(documents)}, existing_email_matches={duplicates}")
        return user_id_map
    for raw in documents:
        email = str(raw["email"]).strip().lower()
        destination = existing.get(email)
        document = prepare_document(raw, columns, user_id_map, warehouse_id_map)
        if destination:
            # Keep the destination identity and password so verified Supabase logins remain valid.
            document["id"] = str(destination["id"])
            document["password_hash"] = destination["password_hash"]
        await upsert_by_id(connection, "users", document)
    print(f"users: merged={len(documents)}")
    return user_id_map


async def run(apply: bool) -> None:
    mongo_client = AsyncIOMotorClient(settings.mongodb_url, serverSelectionTimeoutMS=10000)
    postgres = await asyncpg.connect(get_postgres_dsn(), timeout=20)
    try:
        await mongo_client.admin.command("ping")
        mongo = mongo_client[settings.mongodb_database]
        source_documents = {
            collection: await mongo[collection].find({}).to_list(length=None)
            for collection, _ in COLLECTIONS
        }
        print(f"Mode: {'APPLY' if apply else 'DRY RUN'}")
        print(f"MongoDB database: {settings.mongodb_database}")
        warehouse_id_map: dict[str, str] = {}
        for item in source_documents["warehouses"]:
            destination_id = await postgres.fetchval(
                'SELECT id FROM warehouses WHERE warehouse_code=$1', item["warehouse_code"]
            )
            warehouse_id_map[str(item["_id"])] = str(destination_id or item["_id"])
        if not apply:
            for table, key in (("warehouses", "warehouse_code"), ("sellers", "seller_code")):
                for item in source_documents[table]:
                    destination_id = await postgres.fetchval(
                        f'SELECT id FROM "{table}" WHERE "{key}"=$1', item[key]
                    )
                    if destination_id:
                        print(
                            f"{table}.{item[key]}: natural-key match, "
                            f"same_id={str(destination_id) == str(item['_id'])}"
                        )
        transaction = postgres.transaction()
        if apply:
            await transaction.start()
        try:
            user_id_map = await migrate_users(postgres, source_documents["users"], apply, warehouse_id_map)
            for collection, table in COLLECTIONS[1:]:
                documents = source_documents[collection]
                destination_count = await postgres.fetchval(f'SELECT COUNT(*) FROM "{table}"')
                if not apply:
                    print(f"{table}: source={len(documents)}, destination_before={destination_count}")
                    continue
                columns = await table_columns(postgres, table)
                for raw in documents:
                    own_id_map = warehouse_id_map if table == "warehouses" else None
                    document = prepare_document(raw, columns, user_id_map, warehouse_id_map, own_id_map)
                    await upsert_by_id(postgres, table, document)
                print(f"{table}: merged={len(documents)}")
            if apply:
                await transaction.commit()
                print("MongoDB to Supabase data migration: committed")
        except Exception:
            if apply:
                await transaction.rollback()
                print("MongoDB to Supabase data migration: rolled back")
            raise
    finally:
        mongo_client.close()
        await postgres.close()


parser = argparse.ArgumentParser()
parser.add_argument("--apply", action="store_true", help="Commit the merge; otherwise only report counts")

if __name__ == "__main__":
    asyncio.run(run(parser.parse_args().apply))
