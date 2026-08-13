from enum import StrEnum
from typing import Any
from pydantic import Field

from models.base import MongoModel


class ShipmentStatus(StrEnum):
    """Inbound shipment workflow states."""
    CREATED = "CREATED"
    EXPECTED = "EXPECTED"
    RECEIVING = "RECEIVING"
    INSPECTION = "INSPECTION"
    COMPLETED = "COMPLETED"
    RECEIVED = "RECEIVED"


class InboundShipment(MongoModel):
    """Inbound carrier or manual-drop receipt record."""
    shipment_id: str
    warehouse_id: str
    source_type: str
    tracking_number: str | None = None
    ticket_number: str | None = None
    supplier_name: str
    supplier_reference: str | None = None
    status: ShipmentStatus = ShipmentStatus.EXPECTED
    seller_id: str | None = None
    expected_items: list[dict[str, Any]] = Field(default_factory=list)
    received_items: list[dict[str, Any]] = Field(default_factory=list)
    created_by: str
    received_by: str | None = None
    received_at: str | None = None
    completed_at: str | None = None
