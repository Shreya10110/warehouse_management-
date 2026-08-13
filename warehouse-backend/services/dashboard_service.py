from datetime import datetime, timezone

from core.database import get_database
from core.exceptions import AppError
from models.user_model import User
from services.audit_service import audit_repo
from services.inventory_service import list_inventory
from services.order_service import order_repo, warehouse_repo
from services.inbound_service import shipment_repo


async def summary(user: User, audience: str) -> dict:
    """Build role-appropriate operational KPIs and recent activity without charts."""
    warehouse_id = None if audience == "admin" else user.warehouse_id
    if audience != "admin" and not warehouse_id:
        raise AppError(400, "WAREHOUSE_REQUIRED", "No warehouse is assigned to this user.")
    inventory = await list_inventory(user, warehouse_id=warehouse_id)
    query = {"warehouse_id": warehouse_id} if warehouse_id else {}
    today = datetime.now(timezone.utc).date().isoformat()
    shipments = await shipment_repo.list(query)
    orders = await order_repo.list({"assigned_warehouse_id": warehouse_id} if warehouse_id else {})
    warehouses = [await warehouse_repo.get(warehouse_id)] if warehouse_id else await warehouse_repo.list()
    warehouses = [warehouse for warehouse in warehouses if warehouse]
    database = get_database()
    response = {
        "total_warehouses": len(warehouses),
        "total_skus": len({item["sku"] for item in inventory}),
        "total_inventory": sum(item["on_hand_quantity"] for item in inventory),
        "available_stock": sum(item["available_quantity"] for item in inventory),
        "reserved_stock": sum(item["reserved_quantity"] for item in inventory),
        "damaged_stock": sum(item["damaged_quantity"] for item in inventory),
        "quarantine_stock": sum(item["quarantine_quantity"] for item in inventory),
        "inbound_today": sum(1 for item in shipments if str(item.get("created_at", "")).startswith(today)),
        "outbound_pending": sum(1 for item in orders if item["status"] not in ("SHIPPED", "REJECTED", "CANCELLED")),
        "warehouse": warehouses[0] if warehouse_id and warehouses else None,
        "warehouse_summary": warehouses,
        "recent_activity": await audit_repo.list(query, limit=10),
    }
    if warehouse_id:
        response["team_size"] = await database.users.count_documents({"warehouse_id": warehouse_id, "is_active": True})
    if audience == "inbound":
        response.update({
            "todays_shipments": response["inbound_today"],
            "pending_inspections": sum(1 for item in shipments if item["status"] in ("RECEIVING", "INSPECTION")),
            "completed_today": sum(1 for item in shipments if item["status"] in ("COMPLETED", "RECEIVED") and str(item.get("completed_at", "")).startswith(today)),
            "damaged_items_today": response["damaged_stock"],
            "quarantine_count": response["quarantine_stock"],
        })
    if audience == "outbound":
        for status in ("CREATED", "PICKING", "PICKED", "PACKED", "SHIPPED"):
            response[status.lower()] = sum(1 for item in orders if item["status"] == status)
        response["reserved"] = response["created"]
        response["ready_to_ship"] = response["packed"]
        response["shipped_today"] = sum(1 for item in orders if item["status"] == "SHIPPED" and str(item.get("updated_at", "")).startswith(today))
    return response


async def global_search(term: str, user: User) -> list[dict]:
    """Search operational identifiers and names across authorized collections."""
    if len(term.strip()) < 2:
        return []
    regex = {"$regex": term.strip(), "$options": "i"}
    scope = {} if user.role.value == "OWNER" else {"warehouse_id": user.warehouse_id}
    configurations = [
        ("orders", ["order_id", "customer_name", "items.sku"]),
        ("inbound_shipments", ["shipment_id", "tracking_number", "ticket_number", "supplier_name"]),
        ("damage_reports", ["damage_report_id", "sku"]),
        ("products", ["sku", "name"]),
        ("warehouses", ["warehouse_code", "name"]),
        ("users", ["email", "first_name", "last_name"]),
    ]
    database = get_database()
    results = []
    for collection_name, fields in configurations:
        query = {"$or": [{field: regex} for field in fields]}
        if scope and collection_name not in ("products",):
            query |= scope
        async for document in database[collection_name].find(query).limit(10):
            document["id"] = str(document.pop("_id"))
            document["result_type"] = collection_name
            document.pop("password_hash", None)
            results.append(document)
    return results
