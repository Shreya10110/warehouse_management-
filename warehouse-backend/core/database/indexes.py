"""MongoDB uniqueness, lookup, and retention indexes."""

from pymongo import ASCENDING, DESCENDING

from core.database import get_database, is_postgres_active


async def ensure_indexes() -> None:
    """Create all unique and query indexes required by the implementation plan."""
    if is_postgres_active():
        return
    database = get_database()
    await database.users.create_index([("email", ASCENDING)], unique=True)
    await database.warehouses.create_index([("warehouse_code", ASCENDING)], unique=True)
    await database.products.create_index([("sku", ASCENDING)], unique=True)
    await database.products.create_index([("barcode", ASCENDING)], unique=True, partialFilterExpression={"barcode": {"$type": "string"}})
    await database.sellers.create_index([("seller_code", ASCENDING)], unique=True)
    await database.inventory.create_index([("warehouse_id", ASCENDING), ("sku", ASCENDING)], unique=True)
    await database.inbound_shipments.create_index([("tracking_number", ASCENDING)], unique=True, partialFilterExpression={"tracking_number": {"$type": "string"}})
    await database.inbound_shipments.create_index([("ticket_number", ASCENDING)], unique=True, partialFilterExpression={"ticket_number": {"$type": "string"}})
    await database.inbound_shipments.create_index([("shipment_id", ASCENDING)], unique=True)
    await database.damage_reports.create_index([("damage_report_id", ASCENDING)], unique=True)
    await database.orders.create_index([("order_id", ASCENDING)], unique=True)
    await database.orders.create_index([("assigned_warehouse_id", ASCENDING)])
    await database.orders.create_index([("status", ASCENDING)])
    await database.packages.create_index([("package_id", ASCENDING)], unique=True)
    await database.packages.create_index([("tracking_number", ASCENDING)], unique=True)
    await database.audit_logs.create_index([("warehouse_id", ASCENDING)])
    await database.audit_logs.create_index([("user_id", ASCENDING)])
    await database.audit_logs.create_index([("timestamp", DESCENDING)])
    await database.revoked_tokens.create_index([("jti", ASCENDING)], unique=True)
    await database.revoked_tokens.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
    await database.issue_requests.create_index([("issue_id", ASCENDING)], unique=True)
    await database.issue_requests.create_index([("warehouse_id", ASCENDING), ("status", ASCENDING)])
