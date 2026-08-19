"""PostgreSQL/Supabase connection and safe query helpers."""
import json
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any
from urllib.parse import quote_plus, urlparse
from uuid import UUID
import asyncpg
from core.config import settings

pool: asyncpg.Pool | None = None
transaction_connection: ContextVar[asyncpg.Connection | None] = ContextVar("transaction_connection", default=None)

def get_postgres_dsn() -> str:
    url = settings.database_url
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if url:
        return url
    if settings.supabase_db_password:
        project_ref = urlparse(settings.supabase_url).hostname.split(".")[0]
        password = quote_plus(settings.supabase_db_password)
        region = settings.supabase_db_region
        return f"postgresql://postgres.{project_ref}:{password}@aws-0-{region}.pooler.supabase.com:5432/postgres?sslmode=require"
    return ""

async def connect_postgres() -> None:
    global pool
    pool = await asyncpg.create_pool(dsn=get_postgres_dsn(), min_size=1, max_size=10, timeout=10, command_timeout=30)

async def close_postgres() -> None:
    global pool
    if pool:
        await pool.close()
    pool = None

def get_pool() -> asyncpg.Pool:
    if pool is None:
        raise RuntimeError("PostgreSQL/Supabase connection pool is not initialized")
    return pool


@asynccontextmanager
async def connection_scope():
    """Reuse the active transaction connection or acquire a pooled connection."""
    connection = transaction_connection.get()
    if connection is not None:
        yield connection
        return
    async with get_pool().acquire() as acquired:
        yield acquired


@asynccontextmanager
async def transaction():
    """Run all repository calls in one atomic PostgreSQL transaction."""
    existing = transaction_connection.get()
    if existing is not None:
        async with existing.transaction():
            yield existing
        return
    async with get_pool().acquire() as connection:
        token = transaction_connection.set(connection)
        try:
            async with connection.transaction():
                yield connection
        finally:
            transaction_connection.reset(token)

async def postgres_health() -> dict[str, str]:
    async with get_pool().acquire() as connection:
        value = await connection.fetchval("SELECT 1")
    return {"status": "connected" if value == 1 else "unhealthy", "type": "supabase_postgresql"}

def _json_default(value: Any) -> Any:
    """Convert domain values nested in JSONB documents to JSON-safe values."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (Enum, UUID)):
        return str(value.value if isinstance(value, Enum) else value)
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _serialize_value(value: Any) -> Any:
    return json.dumps(value, default=_json_default) if isinstance(value, (dict, list)) else value

def _deserialize_record(row: asyncpg.Record | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    for key, value in data.items():
        if isinstance(value, str) and value[:1] in ("{", "["):
            try:
                data[key] = json.loads(value)
            except (TypeError, ValueError):
                pass
        elif isinstance(value, datetime):
            data[key] = value.isoformat()
    if "id" in data:
        data["id"] = str(data["id"])
    return data

def _field_expression(field: str) -> str:
    # Nested fields in this app are JSON arrays; text search is sufficient for global search.
    return f'"{field.split(".", 1)[0]}"::text' if "." in field else f'"{field}"'

def _compile_query(query: dict[str, Any] | None, start: int = 1) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    def condition(field: str, value: Any) -> str:
        expression = _field_expression("id" if field == "_id" else field)
        if isinstance(value, dict) and "$regex" in value:
            params.append(str(value["$regex"]).strip("^$"))
            return f"{expression} ILIKE '%' || ${start + len(params) - 1} || '%'"
        if isinstance(value, dict) and "$in" in value:
            choices = list(value["$in"])
            if not choices:
                return "FALSE"
            positions = []
            for choice in choices:
                params.append(_serialize_value(choice))
                positions.append(f"${start + len(params) - 1}")
            return f"{expression} IN ({', '.join(positions)})"
        for operator, sql_operator in (("$gt", ">"), ("$gte", ">="), ("$lt", "<"), ("$lte", "<="), ("$ne", "<>")):
            if isinstance(value, dict) and operator in value:
                params.append(_serialize_value(value[operator]))
                return f"{expression} {sql_operator} ${start + len(params) - 1}"
        params.append(_serialize_value(str(value) if field == "_id" else value))
        return f"{expression} = ${start + len(params) - 1}"
    for field, value in (query or {}).items():
        if field == "$or":
            branches = []
            for branch in value:
                branch_field, branch_value = next(iter(branch.items()))
                branches.append(condition(branch_field, branch_value))
            clauses.append(f"({' OR '.join(branches)})" if branches else "FALSE")
        else:
            clauses.append(condition(field, value))
    return (" AND ".join(clauses) if clauses else "TRUE"), params

async def insert_record(table: str, data: dict[str, Any]) -> dict[str, Any]:
    doc = dict(data)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    now = datetime.now(timezone.utc)
    doc.setdefault("created_at", now); doc.setdefault("updated_at", now)
    columns = list(doc); values = [_serialize_value(doc[column]) for column in columns]
    names = ", ".join(f'"{column}"' for column in columns)
    placeholders = ", ".join(f"${index}" for index in range(1, len(columns) + 1))
    async with connection_scope() as connection:
        row = await connection.fetchrow(f'INSERT INTO "{table}" ({names}) VALUES ({placeholders}) RETURNING *', *values)
    return _deserialize_record(row) or doc

async def find_record_by_id(table: str, record_id: str) -> dict[str, Any] | None:
    return await find_one_record(table, {"id": str(record_id)})

async def find_one_record(table: str, query: dict[str, Any]) -> dict[str, Any] | None:
    where, params = _compile_query(query)
    async with connection_scope() as connection:
        row = await connection.fetchrow(f'SELECT * FROM "{table}" WHERE {where} LIMIT 1', *params)
    return _deserialize_record(row)

async def list_records(table: str, query: dict[str, Any] | None = None, limit: int = 200, skip: int = 0) -> list[dict[str, Any]]:
    where, params = _compile_query(query)
    limit_pos, skip_pos = len(params) + 1, len(params) + 2
    params.extend([min(limit, 500), skip])
    async with connection_scope() as connection:
        rows = await connection.fetch(f'SELECT * FROM "{table}" WHERE {where} ORDER BY "created_at" DESC LIMIT ${limit_pos} OFFSET ${skip_pos}', *params)
    return [_deserialize_record(row) for row in rows]

async def count_records(table: str, query: dict[str, Any] | None = None) -> int:
    where, params = _compile_query(query)
    async with connection_scope() as connection:
        return int(await connection.fetchval(f'SELECT COUNT(*) FROM "{table}" WHERE {where}', *params))

async def update_where_record(table: str, query: dict[str, Any], values: dict[str, Any] | None = None, increments: dict[str, int | float] | None = None) -> dict[str, Any] | None:
    doc = dict(values or {}); doc.pop("id", None); doc.pop("_id", None)
    doc["updated_at"] = doc.get("updated_at", datetime.now(timezone.utc))
    where, params = _compile_query(query)
    assignments: list[str] = []
    for column, value in doc.items():
        params.append(_serialize_value(value)); assignments.append(f'"{column}" = ${len(params)}')
    for column, amount in (increments or {}).items():
        params.append(amount); assignments.append(f'"{column}" = "{column}" + ${len(params)}')
    async with connection_scope() as connection:
        row = await connection.fetchrow(f'UPDATE "{table}" SET {", ".join(assignments)} WHERE {where} RETURNING *', *params)
    return _deserialize_record(row)

async def update_record(table: str, record_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
    return await update_where_record(table, {"id": str(record_id)}, values)

async def delete_record(table: str, record_id: str) -> bool:
    async with connection_scope() as connection:
        result = await connection.execute(f'DELETE FROM "{table}" WHERE id = $1', str(record_id))
    return result == "DELETE 1"
