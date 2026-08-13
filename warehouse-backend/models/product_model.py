from models.base import MongoModel


class Product(MongoModel):
    """Company-wide product and SKU master record."""
    sku: str
    name: str
    description: str | None = None
    category: str
    brand: str | None = None
    unit: str = "EA"
    barcode: str | None = None
    is_active: bool = True
