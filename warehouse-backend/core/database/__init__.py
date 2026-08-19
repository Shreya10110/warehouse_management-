from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from core.config import settings
from core.database.postgres import close_postgres, connect_postgres, get_postgres_dsn, postgres_health

from commons.logger import configure_logging

logger = configure_logging()

client: AsyncIOMotorClient | None = None
database: AsyncIOMotorDatabase | None = None
_is_postgres: bool = False


def is_postgres_active() -> bool:
    """Return True when the application is connected to PostgreSQL / Supabase."""
    return _is_postgres


async def connect_to_mongo() -> None:
    """Connect to configured database (Supabase PostgreSQL or MongoDB)."""
    global client, database, _is_postgres
    pg_dsn = get_postgres_dsn()
    if pg_dsn:
        try:
            await connect_postgres()
            _is_postgres = True
            return
        except Exception as err:
            logger.warning("PostgreSQL connection failed (%s), falling back to MongoDB", err)

    _is_postgres = False
    client = AsyncIOMotorClient(settings.mongodb_url, serverSelectionTimeoutMS=5000)
    await client.admin.command("ping")
    database = client[settings.mongodb_database]


async def close_mongo_connection() -> None:
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


def get_database() -> AsyncIOMotorDatabase:
    """Return the connected MongoDB database or fail when startup did not complete."""
    if database is None and not _is_postgres:
        raise RuntimeError("Database is not connected")
    return database


async def database_health() -> dict[str, str]:
    """Verify database readiness and return active engine status."""
    if _is_postgres:
        return await postgres_health()
    if client is None or database is None:
        raise RuntimeError("MongoDB is not connected")
    await client.admin.command("ping")
    return {"status": "connected", "name": database.name}


__all__ = [
    "client",
    "database",
    "connect_to_mongo",
    "close_mongo_connection",
    "database_health",
    "get_database",
    "is_postgres_active",
]
