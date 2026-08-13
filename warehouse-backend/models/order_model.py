from typing import Any
from pydantic import Field

from models.base import MongoModel


class Order(MongoModel):
    """Outbound customer order allocated to at most one warehouse."""
    order_id: str
    customer_name: str
    customer_phone: str
    customer_email: str | None = None
    shipping_address: dict[str, Any]
    items: list[dict[str, Any]]
    status: str = "PENDING"
    eligible_warehouse_ids: list[str] = Field(default_factory=list)
    assigned_warehouse_id: str | None = None
    rejection_reason: str | None = None
    created_by: str
    picked_by: str | None = None
    picked_at: str | None = None
    picked_items: list[dict[str, Any]] = Field(default_factory=list)
