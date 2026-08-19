from datetime import datetime, timezone

from bson import ObjectId
from pymongo import ASCENDING, ReturnDocument

from core.database import get_database, is_postgres_active
from core.database import postgres
from models.user_model import User


async def ensure_user_indexes() -> None:
    """Create the unique user email index required by the domain."""
    if not is_postgres_active():
        await get_database().users.create_index([("email", ASCENDING)], unique=True)


async def find_user_by_email(email: str) -> User | None:
    """Find one user by normalized email address."""
    norm_email = email.strip().lower()
    if is_postgres_active():
        doc = await postgres.find_one_record("users", {"email": norm_email})
        if not doc:
            return None
        return User.model_validate(doc)

    document = await get_database().users.find_one({"email": norm_email})
    if not document:
        return None
    document["_id"] = str(document["_id"])
    return User.model_validate(document)


async def find_user_by_id(user_id: str) -> User | None:
    """Find one user by identifier."""
    if is_postgres_active():
        doc = await postgres.find_record_by_id("users", user_id)
        if not doc:
            return None
        return User.model_validate(doc)

    if not ObjectId.is_valid(user_id):
        return None
    document = await get_database().users.find_one({"_id": ObjectId(user_id)})
    if not document:
        return None
    document["_id"] = str(document["_id"])
    return User.model_validate(document)


async def create_user(user: User) -> User:
    """Persist a validated user record."""
    if is_postgres_active():
        user_dict = user.model_dump(by_alias=False)
        inserted = await postgres.insert_record("users", user_dict)
        return User.model_validate(inserted)

    await get_database().users.insert_one(user.to_document())
    return user


async def update_last_login(user_id: str) -> datetime:
    """Store and return the user's latest successful login time."""
    timestamp = datetime.now(timezone.utc)
    if is_postgres_active():
        await postgres.update_record("users", user_id, {"last_login": timestamp})
        return timestamp

    await get_database().users.update_one({"_id": ObjectId(user_id)}, {"$set": {"last_login": timestamp}})
    return timestamp


async def list_users(query: dict | None = None) -> list[User]:
    """List users matching an optional warehouse or role query."""
    if is_postgres_active():
        rows = await postgres.list_records("users", query)
        return [User.model_validate(r) for r in rows]

    users = []
    async for document in get_database().users.find(query or {}).sort("created_at", -1):
        document["_id"] = str(document["_id"])
        users.append(User.model_validate(document))
    return users


async def update_user(user_id: str, values: dict) -> User | None:
    """Update a user and return the resulting validated record."""
    if is_postgres_active():
        updated = await postgres.update_record("users", user_id, values)
        if not updated:
            return None
        return User.model_validate(updated)

    if not ObjectId.is_valid(user_id):
        return None
    document = await get_database().users.find_one_and_update(
        {"_id": ObjectId(user_id)}, {"$set": values}, return_document=ReturnDocument.AFTER
    )
    if not document:
        return None
    document["_id"] = str(document["_id"])
    return User.model_validate(document)
