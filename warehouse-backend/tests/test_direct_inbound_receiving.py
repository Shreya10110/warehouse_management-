import asyncio

from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

import core.database as database_module
from core.security import hash_password
from main import app
from models.product_model import Product
from models.user_model import User, UserRole
from models.warehouse_model import Warehouse


def test_inbound_worker_completes_receiving_with_derived_fields() -> None:
    """Post one direct receipt and verify inventory, damage, identity and audit automation."""
    mock_client = AsyncMongoMockClient()
    database_module.client = mock_client
    database_module.database = mock_client.direct_receiving_test
    warehouse = Warehouse(
        warehouse_code="WH-RENO", name="Reno", address_line_1="1 Fulfillment Way",
        city="Reno", state="Nevada", postal_code="89501", country="USA",
        contact_phone="7755550100", contact_email="reno@example.com",
    )
    worker = User(
        first_name="Inbound", last_name="Worker", email="inbound.reno@example.com",
        mobile="7755550101", password_hash=hash_password("StrongPass123"),
        role=UserRole.INBOUND, warehouse_id=warehouse.id,
    )
    product = Product(
        sku="LIP-RED-001", name="Red Lipstick", category="Cosmetics",
        barcode="8901234567890",
    )

    async def seed() -> None:
        """Insert the assigned warehouse, worker and approved product master."""
        await database_module.database.warehouses.insert_one(warehouse.to_document())
        await database_module.database.users.insert_one(worker.to_document())
        await database_module.database.products.insert_one(product.to_document())

    asyncio.run(seed())
    client = TestClient(app, raise_server_exceptions=False)
    login = client.post("/api/v1/auth/login", json={"email": worker.email, "password": "StrongPass123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    payload = {
        "warehouse_id": "507f1f77bcf86cd799439011",
        "source_type": "CARRIER", "tracking_number": "TRK-123456",
        "supplier_name": "ABC Cosmetics",
        "items": [{
            "sku": product.sku, "barcode": product.barcode,
            "received_quantity": 100, "damaged_quantity": 5,
        }],
    }

    receipt = client.post("/api/v1/inbound/receipts", headers=headers, json=payload)
    assert receipt.status_code == 200, receipt.text
    data = receipt.json()
    assert data["warehouse_id"] == warehouse.id
    assert data["status"] == "RECEIVED"
    assert data["received_by"] == worker.id
    assert data["received_at"]
    assert data["received_items"][0]["good_quantity"] == 95
    assert data["received_items"][0]["damaged_quantity"] == 5

    inventory = client.get("/api/v1/inventory", headers=headers).json()[0]
    assert inventory["on_hand_quantity"] == 100
    assert inventory["damaged_quantity"] == 5
    assert inventory["available_quantity"] == 95
    transactions = client.get("/api/v1/inventory-transactions", headers=headers).json()
    assert transactions[0]["quantity"] == 100
    reports = client.get("/api/v1/damage-reports", headers=headers).json()
    assert reports[0]["damage_quantity"] == 5
    audit_count = asyncio.run(database_module.database.audit_logs.count_documents({
        "action": "COMPLETE_RECEIVING", "user_id": worker.id,
    }))
    assert audit_count == 1

    duplicate = client.post("/api/v1/inbound/receipts", headers=headers, json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "SHIPMENT_ALREADY_RECEIVED"
