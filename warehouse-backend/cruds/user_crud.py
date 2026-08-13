from datetime import datetime, timezone

from bson import ObjectId
from pymongo import ASCENDING

from core.database import get_database
from models.user_model import User


async def ensure_user_indexes() -> None:
    await get_database().users.create_index([("email", ASCENDING)], unique=True)


async def find_user_by_email(email: str) -> User | None:
    document = await get_database().users.find_one({"email": email.strip().lower()})
    if not document:
        return None
    document["_id"] = str(document["_id"])
    return User.model_validate(document)


async def find_user_by_id(user_id: str) -> User | None:
    if not ObjectId.is_valid(user_id):
        return None
    document = await get_database().users.find_one({"_id": ObjectId(user_id)})
    if not document:
        return None
    document["_id"] = str(document["_id"])
    return User.model_validate(document)


async def create_user(user: User) -> User:
    await get_database().users.insert_one(user.to_document())
    return user


async def update_last_login(user_id: str) -> datetime:
    timestamp = datetime.now(timezone.utc)
    await get_database().users.update_one({"_id": ObjectId(user_id)}, {"$set": {"last_login": timestamp}})
    return timestamp
