import asyncio

from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

import core.database as database_module
from core.security import hash_password
from main import app
from models.product_model import Product
from models.user_model import User, UserRole
from models.warehouse_model import Warehouse


def test_pdf_role_separation_expected_inbound_and_manager_escalation() -> None:
    """Enforce the Admin, Manager, Inbound, and Outbound responsibilities from the PDF."""
    mock_client = AsyncMongoMockClient()
    database_module.client = mock_client
    database_module.database = mock_client.pdf_workflows
    warehouse = Warehouse(
        warehouse_code="WH-A", name="Warehouse A", address_line_1="1 Warehouse Road",
        city="Bengaluru", state="Karnataka", postal_code="560001",
        contact_phone="9999999999", contact_email="warehouse-a@example.com",
    )
    owner = User(
        first_name="Super", last_name="Admin", email="admin@example.com", mobile="9000000001",
        password_hash=hash_password("StrongPass123"), role=UserRole.OWNER,
    )
    manager = User(
        first_name="Warehouse", last_name="Manager", email="manager-a@example.com", mobile="9000000002",
        password_hash=hash_password("StrongPass123"), role=UserRole.MANAGER, warehouse_id=warehouse.id,
    )
    inbound = User(
        first_name="Inbound", last_name="Worker", email="inbound-a@example.com", mobile="9000000003",
        password_hash=hash_password("StrongPass123"), role=UserRole.INBOUND, warehouse_id=warehouse.id,
    )
    outbound = User(
        first_name="Outbound", last_name="Worker", email="outbound-a@example.com", mobile="9000000004",
        password_hash=hash_password("StrongPass123"), role=UserRole.OUTBOUND, warehouse_id=warehouse.id,
    )
    product = Product(
        sku="LIP-RED-001", name="Red Lipstick", category="Cosmetics", barcode="8901234567890",
    )

    async def seed() -> None:
        """Seed the four-role hierarchy and one product master."""
        await database_module.database.warehouses.insert_one(warehouse.to_document())
        await database_module.database.users.insert_many([owner.to_document(), manager.to_document(), inbound.to_document(), outbound.to_document()])
        await database_module.database.products.insert_one(product.to_document())

    asyncio.run(seed())
    client = TestClient(app, raise_server_exceptions=False)

    def headers(user: User) -> dict[str, str]:
        """Authenticate one seeded user."""
        login = client.post("/api/v1/auth/login", json={"email": user.email, "password": "StrongPass123"})
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    admin_headers = headers(owner)
    manager_headers = headers(manager)
    inbound_headers = headers(inbound)
    outbound_headers = headers(outbound)

    seller = client.post("/api/v1/sellers", headers=admin_headers, json={
        "seller_code": "ABC-COS", "name": "ABC Cosmetics", "email": "seller@example.com",
    })
    assert seller.status_code == 200, seller.text
    seller_id = seller.json()["id"]

    expected_payload = {
        "warehouse_id": warehouse.id, "seller_id": seller_id, "source_type": "MANUAL_DROP",
        "supplier_name": "ABC Cosmetics",
        "expected_items": [{"sku": product.sku, "expected_quantity": 100}],
    }
    assert client.post("/api/v1/inbound/shipments", headers=manager_headers, json=expected_payload).status_code == 403
    expected = client.post("/api/v1/inbound/shipments", headers=admin_headers, json=expected_payload)
    assert expected.status_code == 200, expected.text
    expected_data = expected.json()
    assert expected_data["status"] == "EXPECTED"
    assert expected_data["ticket_number"].startswith("TKT-")
    assert expected_data["seller_id"] == seller_id

    lookup = client.post("/api/v1/inbound/shipments/lookup", headers=inbound_headers, json={
        "source_type": "MANUAL_DROP", "ticket_number": expected_data["ticket_number"],
    })
    assert lookup.status_code == 200, lookup.text
    assert lookup.json()["status"] == "RECEIVING"
    assert client.post(f"/api/v1/inbound/shipments/{expected_data['id']}/complete", headers=manager_headers, json={
        "items": [{"barcode": product.barcode, "received_quantity": 98, "damaged_quantity": 3}],
    }).status_code == 403
    completed = client.post(f"/api/v1/inbound/shipments/{expected_data['id']}/complete", headers=inbound_headers, json={
        "items": [{"barcode": product.barcode, "received_quantity": 98, "damaged_quantity": 3}],
    })
    assert completed.status_code == 200, completed.text
    line = completed.json()["received_items"][0]
    assert line | {"expected_quantity": 100, "received_quantity": 98, "good_quantity": 95, "damaged_quantity": 3} == line

    inventory = client.get("/api/v1/inventory", headers=manager_headers).json()[0]
    assert inventory["on_hand_quantity"] == 98
    assert inventory["damaged_quantity"] == 3
    assert inventory["available_quantity"] == 95

    order_payload = {
        "seller_id": seller_id, "customer_name": "Customer One", "customer_phone": "8888888888",
        "shipping_address": {"address_line_1": "10 Market Road", "city": "Bengaluru"},
        "items": [{"sku": product.sku, "quantity": 5}],
    }
    assert client.post("/api/v1/orders", headers=manager_headers, json=order_payload).status_code == 403
    order = client.post("/api/v1/orders", headers=admin_headers, json=order_payload)
    assigned = client.post(f"/api/v1/orders/{order.json()['id']}/assign-warehouse", headers=admin_headers, json={"warehouse_id": warehouse.id})
    assert assigned.json()["status"] == "CREATED"
    assert client.get(f"/api/v1/orders/{order.json()['id']}", headers=manager_headers).status_code == 200
    assert client.post(f"/api/v1/orders/{order.json()['id']}/start-picking", headers=manager_headers).status_code == 403
    assert client.post(f"/api/v1/orders/{order.json()['id']}/start-picking", headers=outbound_headers).json()["status"] == "PICKING"

    issue = client.post("/api/v1/issues", headers=manager_headers, json={
        "category": "INVENTORY", "subject": "Physical count mismatch",
        "description": "The shelf count needs an Admin review.", "priority": "HIGH",
    })
    assert issue.status_code == 200, issue.text
    assert client.get("/api/v1/issues", headers=inbound_headers).status_code == 403
    decision = client.post(f"/api/v1/issues/{issue.json()['id']}/resolve", headers=admin_headers, json={
        "status": "APPROVED", "admin_response": "Approved for a supervised recount.",
    })
    assert decision.status_code == 200, decision.text
    assert decision.json()["status"] == "APPROVED"
