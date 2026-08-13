from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, Field, field_validator, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(StrEnum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class User(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    first_name: str
    last_name: str
    email: str
    mobile: str
    password_hash: str
    role: UserRole
    warehouse_id: str | None = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_login: datetime | None = None

    model_config = {"populate_by_name": True}

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def validate_warehouse_assignment(self) -> "User":
        if self.role == UserRole.OWNER and self.warehouse_id is not None:
            raise ValueError("OWNER must not have a warehouse_id")
        if self.role != UserRole.OWNER and not self.warehouse_id:
            raise ValueError(f"{self.role} must have a warehouse_id")
        return self

    def to_document(self) -> dict[str, Any]:
        document = self.model_dump(by_alias=True)
        document["_id"] = ObjectId(document["_id"])
        return document
