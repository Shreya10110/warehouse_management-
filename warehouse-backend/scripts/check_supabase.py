"""Read-only live Supabase schema and repository audit."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.database import close_mongo_connection, connect_to_mongo, database_health
from core.database.postgres import get_pool
from cruds.base_crud import CRUDRepository

EXPECTED_TABLES = (
    "users", "warehouses", "products", "sellers", "inbound_shipments",
    "damage_reports", "inventory", "inventory_transactions", "orders",
    "packages", "issue_requests", "audit_logs", "revoked_tokens",
)


async def main() -> None:
    await connect_to_mongo()
    try:
        print(f"Database health: {await database_health()}")
        async with get_pool().acquire() as connection:
            rows = await connection.fetch(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = ANY($1::text[])",
                list(EXPECTED_TABLES),
            )
        present = {row["table_name"] for row in rows}
        missing = set(EXPECTED_TABLES) - present
        if missing:
            raise RuntimeError(f"Missing Supabase tables: {sorted(missing)}")
        for table in EXPECTED_TABLES:
            records = await CRUDRepository(table).list(limit=1)
            count = await CRUDRepository(table).count()
            print(f"- {table}: reachable, {count} rows, sample_read={bool(records)}")
        print("Supabase live audit: successful")
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
