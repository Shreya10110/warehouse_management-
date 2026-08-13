from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument

from core.database import get_database


def serialize(document: dict[str, Any] | None) -> dict[str, Any] | None:
    """Convert a MongoDB document identifier into JSON-safe text."""
    if document is None:
        return None
    value = dict(document)
    value["id"] = str(value.pop("_id"))
    return value


class CRUDRepository:
    """Small reusable MongoDB persistence wrapper for domain collections."""
    def __init__(self, collection: str):
        """Bind this repository to a named MongoDB collection."""
        self.collection_name = collection

    @property
    def collection(self):
        """Return the active database collection."""
        return get_database()[self.collection_name]

    async def create(self, document: dict[str, Any]) -> dict[str, Any]:
        """Insert and return one domain document."""
        value = dict(document)
        value.setdefault("_id", ObjectId())
        if isinstance(value["_id"], str):
            value["_id"] = ObjectId(value["_id"])
        await self.collection.insert_one(value)
        return serialize(value)

    async def get(self, record_id: str) -> dict[str, Any] | None:
        """Read one document by its MongoDB identifier."""
        if not ObjectId.is_valid(record_id):
            return None
        return serialize(await self.collection.find_one({"_id": ObjectId(record_id)}))

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        """Read the first document matching a query."""
        return serialize(await self.collection.find_one(query))

    async def list(self, query: dict[str, Any] | None = None, limit: int = 200, skip: int = 0) -> list[dict[str, Any]]:
        """List recent documents matching a query."""
        cursor = self.collection.find(query or {}).sort("created_at", -1).skip(skip).limit(min(limit, 500))
        return [serialize(item) async for item in cursor]

    async def update(self, record_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
        """Update and return a document by identifier."""
        if not ObjectId.is_valid(record_id):
            return None
        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(record_id)}, {"$set": values}, return_document=ReturnDocument.AFTER
        )
        return serialize(result)
