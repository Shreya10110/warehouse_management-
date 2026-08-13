"""Read-only MongoDB readiness and structure audit for Whitfield Fulfillment."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import settings
from core.database import close_mongo_connection, connect_to_mongo, get_database


async def run() -> None:
    """Print collection counts and index coverage without changing any data."""
    await connect_to_mongo()
    try:
        database = get_database()
        await database.command("ping")
        collections = sorted(await database.list_collection_names())
        print("MongoDB: connected")
        print(f"Database: {settings.mongodb_database}")
        print(f"Collections: {len(collections)}")
        for collection_name in collections:
            collection = database[collection_name]
            document_count = await collection.count_documents({})
            index_count = len(await collection.index_information())
            print(f"- {collection_name}: {document_count} documents, {index_count} indexes")
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(run())
