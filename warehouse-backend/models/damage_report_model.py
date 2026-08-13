from typing import Any
from pydantic import Field

from models.base import MongoModel


class DamageReport(MongoModel):
    """Damage evidence and resolution record linked to inbound inventory."""
    damage_report_id: str
    shipment_id: str
    warehouse_id: str
    sku: str
    damage_quantity: int
    damage_type: str
    damage_reason: str
    notes: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    reported_by: str
    reported_at: str
    resolution_status: str = "OPEN"
    resolved_by: str | None = None
    resolved_at: str | None = None
    resolution: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
