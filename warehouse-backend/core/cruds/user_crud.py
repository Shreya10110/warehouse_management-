from datetime import datetime, timezone

from bson import ObjectId
from pymongo import ASCENDING, ReturnDocument

from core.database import get_database
from models.user_model import User


async def ensure_user_indexes() -> None:
    """Create the unique user email index required by the domain."""
    await get_database().users.create_index([("email", ASCENDING)], unique=True)


async def find_user_by_email(email: str) -> User | None:
    """Find one user by normalized email address."""
    document = await get_database().users.find_one({"email": email.strip().lower()})
    if not document:
        return None
    document["_id"] = str(document["_id"])
    return User.model_validate(document)


async def find_user_by_id(user_id: str) -> User | None:
    """Find one user by MongoDB identifier."""
    if not ObjectId.is_valid(user_id):
        return None
    document = await get_database().users.find_one({"_id": ObjectId(user_id)})
    if not document:
        return None
    document["_id"] = str(document["_id"])
    return User.model_validate(document)


async def create_user(user: User) -> User:
    """Persist a validated user record."""
    await get_database().users.insert_one(user.to_document())
    return user


async def update_last_login(user_id: str) -> datetime:
    """Store and return the user's latest successful login time."""
    timestamp = datetime.now(timezone.utc)
    await get_database().users.update_one({"_id": ObjectId(user_id)}, {"$set": {"last_login": timestamp}})
    return timestamp


async def list_users(query: dict | None = None) -> list[User]:
    """List users matching an optional warehouse or role query."""
    users = []
    async for document in get_database().users.find(query or {}).sort("created_at", -1):
        document["_id"] = str(document["_id"])
        users.append(User.model_validate(document))
    return users


async def update_user(user_id: str, values: dict) -> User | None:
    """Update a user and return the resulting validated record."""
    if not ObjectId.is_valid(user_id):
        return None
    document = await get_database().users.find_one_and_update(
        {"_id": ObjectId(user_id)}, {"$set": values}, return_document=ReturnDocument.AFTER
    )
    if not document:
        return None
    document["_id"] = str(document["_id"])
    return User.model_validate(document)
