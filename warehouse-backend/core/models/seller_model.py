from models.base import MongoModel


class Seller(MongoModel):
    """Approved supplier or merchant used by inbound and outbound documents."""
    seller_code: str
    name: str
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    is_active: bool = True
