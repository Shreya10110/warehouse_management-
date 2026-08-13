from models.base import MongoModel


class Package(MongoModel):
    """Packed outbound parcel and shipping label metadata."""
    package_id: str
    order_id: str
    warehouse_id: str
    weight: float
    length: float
    width: float
    height: float
    packed_by: str
    packed_at: str
    carrier: str
    tracking_number: str
    label_url: str | None = None
    status: str = "PACKED"
