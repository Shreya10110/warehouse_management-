from typing import Any
from pydantic import Field

from datetime import datetime
from models.base import MongoModel, utc_now


class AuditLog(MongoModel):
    """Immutable accountability event for domain changes."""
    user_id: str
    user_role: str
    warehouse_id: str | None = None
    action: str
    entity_type: str
    entity_id: str
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)
