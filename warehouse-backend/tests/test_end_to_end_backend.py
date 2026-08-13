import asyncio

from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

import core.database as database_module
from core.security import hash_password
from main import app
from models.user_model import User, UserRole
from models.product_model import Product
from models.warehouse_model import Warehouse


def test_complete_inbound_and_outbound_workflows() -> None:
    """Exercise the connected backend from login through receiving, reservation and shipping."""
    mock_client = AsyncMongoMockClient()
    database_module.client = mock_client
    database_module.database = mock_client.warehouse_test
    owner = User(
        first_name="Warehouse", last_name="Owner", email="owner@example.com",
        mobile="9999999999", password_hash=hash_password("StrongPass123"), role=UserRole.OWNER,
    )
    asyncio.run(database_module.database.users.insert_one(owner.to_document()))
    client = TestClient(app, raise_server_exceptions=False)

    login = client.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": "StrongPass123"})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    warehouse = client.post("/api/v1/warehouses", headers=headers, json={
        "warehouse_code": "WH-BLR-01", "name": "Whitefield Fulfillment Center",
        "address_line_1": "42 Industrial Layout", "city": "Bengaluru", "state": "Karnataka",
        "postal_code": "560066", "country": "India", "contact_phone": "9999999999",
        "contact_email": "whitefield@example.com",
    })
    assert warehouse.status_code == 200, warehouse.text
    warehouse_id = warehouse.json()["id"]

    product = client.post("/api/v1/products", headers=headers, json={
        "sku": "SKU-CHAIR-01", "name": "Warehouse Chair", "category": "Furniture", "unit": "EA",
    })
    assert product.status_code == 200, product.text

    shipment = client.post("/api/v1/inbound/shipments", headers=headers, json={
        "warehouse_id": warehouse_id, "source_type": "CARRIER", "tracking_number": "TRACK-001",
        "supplier_name": "Acme Supply", "expected_items": [{"sku": "SKU-CHAIR-01", "expected_quantity": 100}],
    })
    assert shipment.status_code == 200, shipment.text
    shipment_id = shipment.json()["id"]
    receipt = client.post(f"/api/v1/inbound/shipments/{shipment_id}/receive", headers=headers, json={
        "items": [{"sku": "SKU-CHAIR-01", "received_quantity": 100, "good_quantity": 94, "damaged_quantity": 4, "quarantine_quantity": 2}],
    })
    assert receipt.status_code == 200, receipt.text
    assert receipt.json()["received_items"][0]["quantity_status"] == "MATCHED"
    duplicate_receipt = client.post(f"/api/v1/inbound/shipments/{shipment_id}/receive", headers=headers, json={
        "items": [{"sku": "SKU-CHAIR-01", "received_quantity": 100, "good_quantity": 94, "damaged_quantity": 4, "quarantine_quantity": 2}],
    })
    assert duplicate_receipt.status_code == 409

    order = client.post("/api/v1/orders", headers=headers, json={
        "customer_name": "Asha Customer", "customer_phone": "8888888888",
        "shipping_address": {"address_line_1": "12 Market Road", "city": "Bengaluru", "postal_code": "560001"},
        "items": [{"sku": "SKU-CHAIR-01", "quantity": 5}],
    })
    assert order.status_code == 200, order.text
    order_data = order.json()
    assert order_data["eligible_warehouse_ids"] == [warehouse_id]
    order_id = order_data["id"]

    reservation = client.post(f"/api/v1/orders/{order_id}/assign-warehouse", headers=headers, json={"warehouse_id": warehouse_id})
    assert reservation.status_code == 200, reservation.text
    assert reservation.json()["status"] == "RESERVED"
    assert client.post(f"/api/v1/orders/{order_id}/start-picking", headers=headers).json()["status"] == "PICKING"
    pick = client.post(f"/api/v1/orders/{order_id}/pick", headers=headers, json={"items": [{"sku": "SKU-CHAIR-01", "quantity": 5}]})
    assert pick.status_code == 200, pick.text
    assert client.post(f"/api/v1/orders/{order_id}/complete-picking", headers=headers).json()["status"] == "PICKED"

    package = client.post(f"/api/v1/orders/{order_id}/pack", headers=headers, json={
        "weight": 12.5, "length": 80, "width": 60, "height": 50,
        "carrier": "BlueDart", "tracking_number": "BD-OUT-001",
    })
    assert package.status_code == 200, package.text
    package_id = package.json()["id"]
    generated = client.post(f"/api/v1/packages/{package_id}/generate-label", headers=headers)
    assert generated.status_code == 200, generated.text
    label = client.get(f"/api/v1/packages/{package_id}/label", headers=headers)
    assert label.status_code == 200
    assert "data:image/png;base64" in label.text
    shipped = client.post(f"/api/v1/packages/{package_id}/ship", headers=headers)
    assert shipped.status_code == 200, shipped.text
    assert shipped.json()["status"] == "SHIPPED"
    assert client.post(f"/api/v1/packages/{package_id}/ship", headers=headers).status_code == 409

    inventory = client.get(f"/api/v1/warehouses/{warehouse_id}/inventory/SKU-CHAIR-01", headers=headers)
    assert inventory.status_code == 200, inventory.text
    assert inventory.json()["on_hand_quantity"] == 95
    assert inventory.json()["reserved_quantity"] == 0
    assert inventory.json()["available_quantity"] == 89
    assert len(client.get("/api/v1/inventory-transactions", headers=headers).json()) >= 3
    assert len(client.get("/api/v1/audit-logs", headers=headers).json()) >= 8


def test_warehouse_isolation_and_role_permissions() -> None:
    """Prove warehouse staff cannot read or manipulate a different warehouse."""
    mock_client = AsyncMongoMockClient()
    database_module.client = mock_client
    database_module.database = mock_client.isolation_test
    first = Warehouse(
        warehouse_code="WH-ONE", name="Warehouse One", address_line_1="One Road", city="Bengaluru",
        state="Karnataka", postal_code="560001", contact_phone="9999999999", contact_email="one@example.com",
    )
    second = Warehouse(
        warehouse_code="WH-TWO", name="Warehouse Two", address_line_1="Two Road", city="Mysuru",
        state="Karnataka", postal_code="570001", contact_phone="8888888888", contact_email="two@example.com",
    )
    manager = User(
        first_name="First", last_name="Manager", email="manager@example.com", mobile="7777777777",
        password_hash=hash_password("StrongPass123"), role=UserRole.MANAGER, warehouse_id=first.id,
    )
    outbound = User(
        first_name="Outbound", last_name="Staff", email="outbound@example.com", mobile="6666666666",
        password_hash=hash_password("StrongPass123"), role=UserRole.OUTBOUND, warehouse_id=first.id,
    )
    product = Product(sku="SKU-ONE", name="Test Product", category="Test")

    async def seed() -> None:
        """Insert isolated test identities and master data."""
        await database_module.database.warehouses.insert_many([first.to_document(), second.to_document()])
        await database_module.database.users.insert_many([manager.to_document(), outbound.to_document()])
        await database_module.database.products.insert_one(product.to_document())

    asyncio.run(seed())
    client = TestClient(app, raise_server_exceptions=False)
    manager_login = client.post("/api/v1/auth/login", json={"email": manager.email, "password": "StrongPass123"}).json()
    manager_headers = {"Authorization": f"Bearer {manager_login['access_token']}"}
    denied = client.get(f"/api/v1/warehouses/{second.id}", headers=manager_headers)
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "FORBIDDEN"
    assert client.get(f"/api/v1/warehouses/{second.id}/inventory", headers=manager_headers).status_code == 403
    assert client.get(f"/api/v1/warehouses/{second.id}/audit-logs", headers=manager_headers).status_code == 403

    shipment = client.post("/api/v1/inbound/shipments", headers=manager_headers, json={
        "warehouse_id": second.id, "source_type": "MANUAL_DROP", "ticket_number": "TICKET-ISOLATION",
        "supplier_name": "Test Supplier", "expected_items": [{"sku": product.sku, "expected_quantity": 1}],
    })
    assert shipment.status_code == 200, shipment.text
    assert shipment.json()["warehouse_id"] == first.id

    outbound_login = client.post("/api/v1/auth/login", json={"email": outbound.email, "password": "StrongPass123"}).json()
    outbound_headers = {"Authorization": f"Bearer {outbound_login['access_token']}"}
    forbidden_inbound = client.post("/api/v1/inbound/shipments", headers=outbound_headers, json={
        "source_type": "MANUAL_DROP", "ticket_number": "TICKET-OUTBOUND",
        "supplier_name": "Supplier", "expected_items": [{"sku": product.sku, "expected_quantity": 1}],
    })
    assert forbidden_inbound.status_code == 403
    assert client.post("/api/v1/auth/logout", headers=outbound_headers).status_code == 200
    revoked = client.get("/api/v1/auth/me", headers=outbound_headers)
    assert revoked.status_code == 401
    assert revoked.json()["detail"]["code"] == "UNAUTHORIZED"
