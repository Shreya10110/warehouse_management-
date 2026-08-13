"""Run an isolated in-memory WMS API for local UI verification only."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["CORS_ORIGINS"] = "http://127.0.0.1:5199"

import uvicorn
from mongomock_motor import AsyncMongoMockClient

import core.database as database_module
from core.security import hash_password
from main import app
from models.product_model import Product
from models.user_model import User, UserRole
from models.warehouse_model import Warehouse


async def seed() -> None:
    """Create an in-memory database and a predictable owner login."""
    client = AsyncMongoMockClient()
    database_module.client = client
    database_module.database = client.wms_browser
    owner = User(
        first_name="Warehouse", last_name="Owner", email="owner@example.com", mobile="9999999999",
        password_hash=hash_password("StrongPass123"), role=UserRole.OWNER,
    )
    warehouse = Warehouse(
        warehouse_code="WH-WFD-01", name="Whitfield Fulfillment", address_line_1="42 Industrial Layout",
        city="Bengaluru", state="Karnataka", postal_code="560066", country="India",
        contact_phone="9999999999", contact_email="ops@whitfield.example.com",
    )
    manager = User(first_name="Maya", last_name="Manager", email="manager@example.com", mobile="9999999998", password_hash=hash_password("StrongPass123"), role=UserRole.MANAGER, warehouse_id=warehouse.id)
    inbound = User(first_name="Isha", last_name="Inbound", email="inbound@example.com", mobile="9999999997", password_hash=hash_password("StrongPass123"), role=UserRole.INBOUND, warehouse_id=warehouse.id, approved_by=manager.id)
    outbound = User(first_name="Omar", last_name="Outbound", email="outbound@example.com", mobile="9999999996", password_hash=hash_password("StrongPass123"), role=UserRole.OUTBOUND, warehouse_id=warehouse.id, approved_by=manager.id)
    warehouse.manager_id = manager.id
    product = Product(sku="LIP-RED-001", name="Red Lipstick", category="Cosmetics", brand="Whitfield Beauty", barcode="8901234567890")
    await database_module.database.warehouses.insert_one(warehouse.to_document())
    await database_module.database.users.insert_many([owner.to_document(), manager.to_document(), inbound.to_document(), outbound.to_document()])
    await database_module.database.products.insert_one(product.to_document())


if __name__ == "__main__":
    asyncio.run(seed())
    uvicorn.run(app, host="127.0.0.1", port=8011, lifespan="off")
