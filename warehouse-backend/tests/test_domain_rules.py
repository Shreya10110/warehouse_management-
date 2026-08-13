import pytest
from pydantic import ValidationError

from models.inventory_model import Inventory
from models.user_model import User, UserRole
from schemas.domain_schemas import OrderCreate, ReceivedItem, ShipmentCreate
from services.inbound_service import warehouse_for
from services.inventory_service import available


def make_user(role: UserRole, warehouse_id: str | None = None) -> User:
    """Create a valid test user for pure authorization rules."""
    return User(first_name="Test", last_name="User", email=f"{role.lower()}@example.com", mobile="9999999999", password_hash="hash", role=role, warehouse_id=warehouse_id)


def test_available_quantity_excludes_non_sellable_stock() -> None:
    """Available stock excludes reserved, damaged and quarantined units."""
    item = Inventory(warehouse_id="w1", product_id="p1", sku="SKU-1", on_hand_quantity=100, reserved_quantity=10, damaged_quantity=4, quarantine_quantity=2)
    assert item.available_quantity == 84
    assert available(item.model_dump()) == 84


def test_inspection_breakdown_must_equal_received() -> None:
    """Reject an inbound inspection whose component quantities do not balance."""
    with pytest.raises(ValidationError, match="INVALID_INSPECTION_QUANTITY"):
        ReceivedItem(sku="SKU-1", received_quantity=10, good_quantity=8, damaged_quantity=1, quarantine_quantity=0)


def test_staff_warehouse_comes_from_identity() -> None:
    """Ignore a staff-supplied warehouse identifier and use their assignment."""
    user = make_user(UserRole.INBOUND, "warehouse-one")
    assert warehouse_for(user, "warehouse-two") == "warehouse-one"


def test_owner_must_supply_warehouse_for_inbound() -> None:
    """Require owners to select a warehouse for warehouse-scoped receiving."""
    with pytest.raises(Exception, match="warehouse_id is required"):
        warehouse_for(make_user(UserRole.OWNER), None)


def test_source_reference_matches_inbound_type() -> None:
    """Require carrier tracking numbers and manual-drop ticket numbers."""
    with pytest.raises(ValidationError):
        ShipmentCreate(source_type="CARRIER", supplier_name="Supplier", expected_items=[{"sku": "SKU-1", "expected_quantity": 1}])


def test_order_requires_positive_quantity_and_address() -> None:
    """Reject empty shipping addresses and non-positive order lines."""
    with pytest.raises(ValidationError):
        OrderCreate(customer_name="Customer", customer_phone="9999999999", shipping_address={}, items=[{"sku": "SKU-1", "quantity": 0}])
