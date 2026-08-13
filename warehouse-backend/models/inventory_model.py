from models.base import MongoModel


class Inventory(MongoModel):
    """Warehouse-specific quantities for one SKU."""
    warehouse_id: str
    product_id: str
    sku: str
    on_hand_quantity: int = 0
    reserved_quantity: int = 0
    damaged_quantity: int = 0
    quarantine_quantity: int = 0

    @property
    def available_quantity(self) -> int:
        """Calculate stock that can be allocated to outbound orders."""
        return self.on_hand_quantity - self.reserved_quantity - self.damaged_quantity - self.quarantine_quantity
