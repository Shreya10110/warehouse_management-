from datetime import datetime, timezone
from uuid import uuid4
from bson import ObjectId
from core.database import get_database

from core.exceptions import AppError
from cruds.base_crud import CRUDRepository
from models.damage_report_model import DamageReport
from models.inbound_shipment_model import InboundShipment
from models.user_model import User
from schemas.domain_schemas import DamageCreate, ShipmentCreate, ShipmentReceive
from services.audit_service import record
from services.inventory_service import change_quantities, product_repo

shipment_repo = CRUDRepository("inbound_shipments")
damage_repo = CRUDRepository("damage_reports")


def warehouse_for(user: User, requested: str | None) -> str:
    """Resolve warehouse from identity and never trust staff-supplied warehouse IDs."""
    if user.role.value == "OWNER":
        if not requested:
            raise AppError(400, "WAREHOUSE_REQUIRED", "warehouse_id is required for owners.")
        return requested
    if not user.warehouse_id:
        raise AppError(403, "FORBIDDEN", "No warehouse is assigned to this user.")
    return user.warehouse_id


async def create_shipment(payload: ShipmentCreate, user: User) -> dict:
    """Validate products and unique references, then register an inbound shipment."""
    warehouse_id = warehouse_for(user, payload.warehouse_id)
    if payload.tracking_number and await shipment_repo.find_one({"tracking_number": payload.tracking_number}):
        raise AppError(409, "DUPLICATE_TRACKING_NUMBER", "Tracking number already exists.")
    if payload.ticket_number and await shipment_repo.find_one({"ticket_number": payload.ticket_number}):
        raise AppError(409, "DUPLICATE_TICKET_NUMBER", "Ticket number already exists.")
    expected = []
    for item in payload.expected_items:
        if not await product_repo.find_one({"sku": item.sku}):
            raise AppError(404, "PRODUCT_NOT_FOUND", f"Product {item.sku} was not found.")
        expected.append(item.model_dump())
    model = InboundShipment(
        shipment_id=f"IN-{uuid4().hex[:10].upper()}", warehouse_id=warehouse_id,
        created_by=user.id, expected_items=expected, **payload.model_dump(exclude={"warehouse_id", "expected_items"}),
    )
    created = await shipment_repo.create(model.to_document())
    await record(user, "CREATE", "INBOUND_SHIPMENT", created["id"], warehouse_id, new=created)
    return created


async def receive_shipment(record_id: str, payload: ShipmentReceive, user: User) -> dict:
    """Post an inspected inbound receipt once and update inventory with full history."""
    shipment = await shipment_repo.get(record_id)
    if not shipment:
        raise AppError(404, "SHIPMENT_NOT_FOUND", "Inbound shipment was not found.")
    if shipment["warehouse_id"] != warehouse_for(user, shipment["warehouse_id"]):
        raise AppError(403, "FORBIDDEN", "Shipment belongs to another warehouse.")
    if shipment["status"] == "COMPLETED":
        raise AppError(409, "SHIPMENT_ALREADY_COMPLETED", "This shipment has already been posted.")
    if shipment["status"] not in ("CREATED", "INSPECTION"):
        raise AppError(409, "INVALID_SHIPMENT_STATUS", "This shipment is already being received.")
    expected = {item["sku"]: item["expected_quantity"] for item in shipment["expected_items"]}
    received = []
    for item in payload.items:
        if item.sku not in expected:
            raise AppError(400, "INVALID_SKU", f"SKU {item.sku} was not expected on this shipment.")
        difference = item.received_quantity - expected[item.sku]
        status = "MATCHED" if difference == 0 else ("SHORT_RECEIVED" if difference < 0 else "OVER_RECEIVED")
        detail = item.model_dump() | {"expected_quantity": expected[item.sku], "difference": difference, "quantity_status": status}
        received.append(detail)
    claim = await get_database().inbound_shipments.update_one(
        {"_id": ObjectId(record_id), "status": shipment["status"]},
        {"$set": {"status": "RECEIVING", "updated_at": datetime.now(timezone.utc)}},
    )
    if claim.modified_count != 1:
        raise AppError(409, "SHIPMENT_ALREADY_COMPLETED", "This shipment is already being received or completed.")
    applied = []
    try:
        for item in payload.items:
            changes = {"on_hand_quantity": item.received_quantity, "damaged_quantity": item.damaged_quantity, "quarantine_quantity": item.quarantine_quantity}
            await change_quantities(
                shipment["warehouse_id"], item.sku, changes,
                "INBOUND", "INBOUND_SHIPMENT", shipment["shipment_id"], user,
            )
            applied.append((item.sku, changes))
    except Exception:
        for sku, changes in applied:
            await get_database().inventory.update_one(
                {"warehouse_id": shipment["warehouse_id"], "sku": sku},
                {"$inc": {field: -quantity for field, quantity in changes.items()}},
            )
        await shipment_repo.update(record_id, {"status": shipment["status"], "updated_at": datetime.now(timezone.utc)})
        raise
    now = datetime.now(timezone.utc).isoformat()
    updated = await shipment_repo.update(record_id, {"received_items": received, "received_by": user.id, "received_at": now, "completed_at": now, "status": "COMPLETED", "updated_at": datetime.now(timezone.utc)})
    await record(user, "COMPLETE", "INBOUND_SHIPMENT", record_id, shipment["warehouse_id"], shipment, updated)
    return updated


async def create_damage(record_id: str, payload: DamageCreate, user: User) -> dict:
    """Create a damage report tied to a shipment in the user's warehouse."""
    shipment = await shipment_repo.get(record_id)
    if not shipment:
        raise AppError(404, "SHIPMENT_NOT_FOUND", "Inbound shipment was not found.")
    if shipment["warehouse_id"] != warehouse_for(user, shipment["warehouse_id"]):
        raise AppError(403, "FORBIDDEN", "Shipment belongs to another warehouse.")
    model = DamageReport(
        damage_report_id=f"DMG-{uuid4().hex[:10].upper()}", shipment_id=shipment["shipment_id"],
        warehouse_id=shipment["warehouse_id"], reported_by=user.id,
        reported_at=datetime.now(timezone.utc).isoformat(), **payload.model_dump(),
    )
    created = await damage_repo.create(model.to_document())
    await record(user, "REPORT_DAMAGE", "DAMAGE_REPORT", created["id"], shipment["warehouse_id"], new=created)
    return created
