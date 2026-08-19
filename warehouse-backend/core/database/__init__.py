from typing import Any

from core.database.postgres import close_postgres, connect_postgres, get_postgres_dsn, postgres_health

client: Any | None = None
database: Any | None = None
_is_postgres: bool = False


def is_postgres_active() -> bool:
    """Return True when the application is connected to PostgreSQL / Supabase."""
    return _is_postgres


async def connect_database() -> None:
    """Connect to the required Supabase PostgreSQL database."""
    global client, database, _is_postgres
    pg_dsn = get_postgres_dsn()
    if not pg_dsn:
        raise RuntimeError("Supabase PostgreSQL is not configured. Set DATABASE_URL or SUPABASE_DB_PASSWORD.")
    await connect_postgres()
    _is_postgres = True


async def close_database() -> None:
    """Close the active database client during application shutdown."""
    global client, database, _is_postgres
    if _is_postgres:
        await close_postgres()
        _is_postgres = False
        return
    if client:
        client.close()
    client = None
    database = None


def get_database() -> Any:
    """Return a test/legacy database injected outside the Supabase runtime."""
    if database is None and not _is_postgres:
        raise RuntimeError("Database is not connected")
    return database


async def database_health() -> dict[str, str]:
    """Verify database readiness and return active engine status."""
    if _is_postgres:
        return await postgres_health()
    if client is None or database is None:
        raise RuntimeError("Database is not connected")
    await client.admin.command("ping")
    return {"status": "connected", "name": database.name}


__all__ = [
    "client",
    "database",
    "connect_database",
    "close_database",
    "database_health",
    "get_database",
    "is_postgres_active",
]

# Backward-compatible names for older utility scripts. Runtime code uses the
# database-neutral names above and never falls back from Supabase to MongoDB.
connect_to_mongo = connect_database
close_mongo_connection = close_database
