from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument

from core.database import get_database, is_postgres_active
from core.database import postgres


def serialize(document: dict[str, Any] | None) -> dict[str, Any] | None:
    """Convert a database document identifier into JSON-safe text."""
    if document is None:
        return None
    value = dict(document)
    if "_id" in value:
        value["id"] = str(value.pop("_id"))
    elif "id" in value:
        value["id"] = str(value["id"])
    return value


class CRUDRepository:
    """Reusable database persistence wrapper for collections and SQL tables."""
    def __init__(self, collection: str):
        """Bind this repository to a named collection or table."""
        self.collection_name = collection

    @property
    def collection(self):
        """Return the active MongoDB database collection."""
        return get_database()[self.collection_name]

    async def create(self, document: dict[str, Any]) -> dict[str, Any]:
        """Insert and return one domain record."""
        if is_postgres_active():
            return await postgres.insert_record(self.collection_name, document)

        value = dict(document)
        value.setdefault("_id", ObjectId())
        if isinstance(value["_id"], str) and ObjectId.is_valid(value["_id"]):
            value["_id"] = ObjectId(value["_id"])
        await self.collection.insert_one(value)
        return serialize(value)

    async def get(self, record_id: str) -> dict[str, Any] | None:
        """Read one document by its identifier."""
        if is_postgres_active():
            return await postgres.find_record_by_id(self.collection_name, record_id)

        if not ObjectId.is_valid(record_id):
            return None
        return serialize(await self.collection.find_one({"_id": ObjectId(record_id)}))

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        """Read the first document matching a query."""
        if is_postgres_active():
            return await postgres.find_one_record(self.collection_name, query)
        return serialize(await self.collection.find_one(query))

    async def list(self, query: dict[str, Any] | None = None, limit: int = 200, skip: int = 0) -> list[dict[str, Any]]:
        """List recent documents matching a query."""
        if is_postgres_active():
            return await postgres.list_records(self.collection_name, query, limit=limit, skip=skip)

        cursor = self.collection.find(query or {}).sort("created_at", -1).skip(skip).limit(min(limit, 500))
        return [serialize(item) async for item in cursor]

    async def update(self, record_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
        """Update and return a document by identifier."""
        if is_postgres_active():
            return await postgres.update_record(self.collection_name, record_id, values)

        if not ObjectId.is_valid(record_id):
            return None
        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(record_id)}, {"$set": values}, return_document=ReturnDocument.AFTER
        )
        return serialize(result)

    async def update_where(
        self, query: dict[str, Any], values: dict[str, Any] | None = None,
        increments: dict[str, int | float] | None = None,
    ) -> dict[str, Any] | None:
        """Atomically update the first matching record and return it."""
        if is_postgres_active():
            return await postgres.update_where_record(self.collection_name, query, values, increments)
        mongo_query = dict(query)
        if "_id" in mongo_query and isinstance(mongo_query["_id"], str) and ObjectId.is_valid(mongo_query["_id"]):
            mongo_query["_id"] = ObjectId(mongo_query["_id"])
        update: dict[str, Any] = {}
        if values:
            update["$set"] = values
        if increments:
            update["$inc"] = increments
        result = await self.collection.find_one_and_update(mongo_query, update, return_document=ReturnDocument.AFTER)
        return serialize(result)

    async def count(self, query: dict[str, Any] | None = None) -> int:
        """Count records matching a query on either supported database."""
        if is_postgres_active():
            return await postgres.count_records(self.collection_name, query)
        return await self.collection.count_documents(query or {})
