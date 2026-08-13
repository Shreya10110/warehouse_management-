from typing import Any

from models.base import MongoModel


class InventoryTransaction(MongoModel):
    """Immutable stock movement history for a warehouse SKU."""
    warehouse_id: str
    sku: str
    transaction_type: str
    quantity: int
    before_values: dict[str, Any]
    after_values: dict[str, Any]
    reference_type: str
    reference_id: str
    performed_by: str
