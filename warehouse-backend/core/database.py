from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from core.config import settings

client: AsyncIOMotorClient | None = None
database: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    """Connect to MongoDB and verify availability with a ping."""
    global client, database
    client = AsyncIOMotorClient(settings.mongodb_url, serverSelectionTimeoutMS=5000)
    await client.admin.command("ping")
    database = client[settings.mongodb_database]


async def close_mongo_connection() -> None:
    """Close the active MongoDB client during application shutdown."""
    global client, database
    if client:
        client.close()
    client = None
    database = None


def get_database() -> AsyncIOMotorDatabase:
    """Return the connected database or fail when startup did not complete."""
    if database is None:
        raise RuntimeError("MongoDB is not connected")
    return database
