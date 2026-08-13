from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Return an aware UTC timestamp for domain records."""
    return datetime.now(timezone.utc)


class MongoModel(BaseModel):
    """Base domain record using a JSON-safe identifier and UTC timestamps."""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    model_config = {"populate_by_name": True, "use_enum_values": True}

    def to_document(self) -> dict[str, Any]:
        """Convert the model to a MongoDB document with an ObjectId key."""
        value = self.model_dump(by_alias=True)
        value["_id"] = ObjectId(value["_id"])
        return value
