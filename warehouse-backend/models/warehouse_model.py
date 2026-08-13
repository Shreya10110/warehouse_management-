from models.base import MongoModel


class Warehouse(MongoModel):
    """Physical warehouse identity, address, contact, and manager assignment."""
    warehouse_code: str
    name: str
    address_line_1: str
    address_line_2: str | None = None
    city: str
    state: str
    postal_code: str
    country: str = "India"
    manager_id: str | None = None
    contact_phone: str
    contact_email: str
    image_url: str | None = None
    is_active: bool = True
