from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, model_validator


class WarehouseCreate(BaseModel):
    """Warehouse creation and full update payload."""
    warehouse_code: str = Field(min_length=2, max_length=30)
    name: str = Field(min_length=2, max_length=150)
    address_line_1: str
    address_line_2: str | None = None
    city: str
    state: str
    postal_code: str
    country: str = "India"
    manager_id: str | None = None
    contact_phone: str
    contact_email: EmailStr
    image_url: str | None = None


class ProductCreate(BaseModel):
    """Product and globally unique SKU creation payload."""
    sku: str = Field(min_length=1, max_length=80)
    name: str
    description: str | None = None
    category: str
    brand: str | None = None
    unit: str = "EA"
    barcode: str | None = None


class ShipmentItem(BaseModel):
    """Expected line item on an inbound shipment."""
    sku: str
    expected_quantity: int = Field(gt=0)


class ShipmentCreate(BaseModel):
    """Inbound shipment registration payload."""
    warehouse_id: str | None = None
    source_type: Literal["CARRIER", "MANUAL_DROP"]
    tracking_number: str | None = None
    ticket_number: str | None = None
    supplier_name: str
    supplier_reference: str | None = None
    expected_items: list[ShipmentItem] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_reference(self) -> "ShipmentCreate":
        """Require the reference identifier that matches the source type."""
        if self.source_type == "CARRIER" and not self.tracking_number:
            raise ValueError("Carrier shipments require tracking_number")
        if self.source_type == "MANUAL_DROP" and not self.ticket_number:
            raise ValueError("Manual drops require ticket_number")
        return self


class ReceivedItem(BaseModel):
    """Received and inspected quantity breakdown for one SKU."""
    sku: str
    received_quantity: int = Field(ge=0)
    good_quantity: int = Field(ge=0)
    damaged_quantity: int = Field(ge=0)
    quarantine_quantity: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_inspection(self) -> "ReceivedItem":
        """Require received quantity to equal good, damaged and quarantined units."""
        if self.received_quantity != self.good_quantity + self.damaged_quantity + self.quarantine_quantity:
            raise ValueError("INVALID_INSPECTION_QUANTITY")
        return self


class ShipmentReceive(BaseModel):
    """Complete inspected receipt payload for an inbound shipment."""
    items: list[ReceivedItem] = Field(min_length=1)


class DirectReceiptItem(BaseModel):
    """Worker-entered quantities for one directly received product."""
    sku: str | None = None
    barcode: str | None = None
    received_quantity: int = Field(gt=0)
    damaged_quantity: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_item(self) -> "DirectReceiptItem":
        """Require a product identifier and keep damage within the physical count."""
        if not (self.sku and self.sku.strip()) and not (self.barcode and self.barcode.strip()):
            raise ValueError("Select a product or scan a barcode")
        if self.damaged_quantity > self.received_quantity:
            raise ValueError("Damaged quantity cannot exceed received quantity")
        return self


class DirectReceiptCreate(BaseModel):
    """One-step inbound receipt whose derived fields are calculated by the server."""
    warehouse_id: str | None = None
    source_type: Literal["CARRIER", "MANUAL_DROP"]
    tracking_number: str | None = None
    ticket_number: str | None = None
    supplier_name: str = Field(min_length=2)
    supplier_reference: str | None = None
    items: list[DirectReceiptItem] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_reference(self) -> "DirectReceiptCreate":
        """Require the delivery identifier that matches the selected arrival type."""
        if self.source_type == "CARRIER" and not self.tracking_number:
            raise ValueError("Carrier deliveries require a tracking number")
        if self.source_type == "MANUAL_DROP" and not self.ticket_number:
            raise ValueError("Seller drop-offs require a ticket number")
        return self


class DamageCreate(BaseModel):
    """Damage report payload for an inbound shipment line."""
    sku: str
    damage_quantity: int = Field(gt=0)
    damage_type: Literal["TORN", "WET", "CRUSHED", "BROKEN", "OPEN_PACKAGE", "WRONG_ITEM", "OTHER"]
    damage_reason: str
    notes: str | None = None
    image_urls: list[str] = Field(default_factory=list)


class InventoryAdjustment(BaseModel):
    """Authorized manual stock adjustment payload."""
    sku: str
    quantity_change: int
    reason: str = Field(min_length=3)
    warehouse_id: str | None = None


class ResolutionRequest(BaseModel):
    """Damage or quarantine disposition decision."""
    resolution: Literal["RETURN_TO_SUPPLIER", "DISPOSE", "MOVE_TO_GOOD_STOCK", "KEEP_QUARANTINED"]


class StatusRequest(BaseModel):
    """Shared active-status update payload."""
    is_active: bool


class ImageRequest(BaseModel):
    """Image URL attachment payload after cloud upload."""
    image_urls: list[str] = Field(min_length=1)


class GenericResponse(BaseModel):
    """Flexible response model for domain documents."""
    data: Any


class OrderItem(BaseModel):
    """Requested SKU and positive quantity on an outbound order."""
    sku: str
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    """Validated customer order creation payload."""
    customer_name: str = Field(min_length=2)
    customer_phone: str = Field(min_length=7)
    customer_email: EmailStr | None = None
    shipping_address: dict[str, Any]
    items: list[OrderItem] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_shipping_address(self) -> "OrderCreate":
        """Require a non-empty address suitable for a shipping label."""
        if not self.shipping_address or not any(str(value).strip() for value in self.shipping_address.values()):
            raise ValueError("Shipping address is required")
        return self


class WarehouseAssignment(BaseModel):
    """Owner-selected eligible warehouse for an outbound order."""
    warehouse_id: str


class RejectionRequest(BaseModel):
    """Owner rejection reason for an unfulfillable order."""
    reason: str = "INSUFFICIENT_STOCK"


class PickRequest(BaseModel):
    """Actual picked quantities for all order lines."""
    items: list[OrderItem] = Field(min_length=1)


class PackageCreate(BaseModel):
    """Package dimensions and carrier information for a picked order."""
    weight: float = Field(gt=0)
    length: float = Field(gt=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    carrier: str
    tracking_number: str
