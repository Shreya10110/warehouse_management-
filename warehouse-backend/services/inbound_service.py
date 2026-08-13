from datetime import datetime, timezone
from uuid import uuid4
from bson import ObjectId
from core.database import get_database

from core.exceptions import AppError
from cruds.base_crud import CRUDRepository
from models.damage_report_model import DamageReport
from models.inbound_shipment_model import InboundShipment
from models.user_model import User
from schemas.domain_schemas import DamageCreate, DirectReceiptCreate, ExpectedShipmentReceipt, ShipmentCreate, ShipmentLookup, ShipmentReceive
from services.audit_service import record
from services.inventory_service import change_quantities, product_repo

shipment_repo = CRUDRepository("inbound_shipments")
damage_repo = CRUDRepository("damage_reports")
seller_repo = CRUDRepository("sellers")


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
    if not await get_database().warehouses.find_one({"_id": ObjectId(warehouse_id), "is_active": True}):
        raise AppError(404, "WAREHOUSE_NOT_FOUND", "Destination warehouse was not found or is inactive.")
    if payload.seller_id:
        seller = await seller_repo.get(payload.seller_id)
        if not seller or not seller.get("is_active", True):
            raise AppError(404, "SELLER_NOT_FOUND", "Seller was not found or is inactive.")
    ticket_number = payload.ticket_number
    if payload.source_type == "MANUAL_DROP" and not ticket_number:
        ticket_number = f"TKT-{uuid4().hex[:10].upper()}"
    if payload.tracking_number and await shipment_repo.find_one({"tracking_number": payload.tracking_number}):
        raise AppError(409, "DUPLICATE_TRACKING_NUMBER", "Tracking number already exists.")
    if ticket_number and await shipment_repo.find_one({"ticket_number": ticket_number}):
        raise AppError(409, "DUPLICATE_TICKET_NUMBER", "Ticket number already exists.")
    expected = []
    for item in payload.expected_items:
        if not await product_repo.find_one({"sku": item.sku}):
            raise AppError(404, "PRODUCT_NOT_FOUND", f"Product {item.sku} was not found.")
        expected.append(item.model_dump())
    model = InboundShipment(
        shipment_id=f"IN-{uuid4().hex[:10].upper()}", warehouse_id=warehouse_id,
        created_by=user.id, expected_items=expected, status="EXPECTED",
        **(payload.model_dump(exclude={"warehouse_id", "expected_items", "ticket_number"}) | {"ticket_number": ticket_number}),
    )
    created = await shipment_repo.create(model.to_document())
    await record(user, "CREATE", "INBOUND_SHIPMENT", created["id"], warehouse_id, new=created)
    return created


async def lookup_expected_shipment(payload: ShipmentLookup, user: User) -> dict:
    """Find an expected shipment in the worker's warehouse and mark it receiving."""
    warehouse_id = warehouse_for(user, None)
    reference = {"tracking_number": payload.tracking_number} if payload.source_type == "CARRIER" else {"ticket_number": payload.ticket_number}
    shipment = await shipment_repo.find_one(reference | {"warehouse_id": warehouse_id})
    if not shipment:
        raise AppError(404, "SHIPMENT_NOT_FOUND", "No expected shipment matches this reference in your warehouse.")
    if shipment["status"] in ("COMPLETED", "RECEIVED"):
        raise AppError(409, "SHIPMENT_ALREADY_COMPLETED", "This shipment has already been received.")
    if shipment["status"] == "EXPECTED":
        updated = await shipment_repo.update(shipment["id"], {
            "status": "RECEIVING", "receiving_started_by": user.id,
            "receiving_started_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc),
        })
        await record(user, "START_RECEIVING", "INBOUND_SHIPMENT", shipment["id"], warehouse_id, shipment, updated)
        return updated
    if shipment["status"] != "RECEIVING":
        raise AppError(409, "INVALID_SHIPMENT_STATUS", "Shipment cannot be received in its current status.")
    return shipment


async def complete_expected_shipment(record_id: str, payload: ExpectedShipmentReceipt, user: User) -> dict:
    """Complete one expected shipment with server-calculated good and damaged quantities."""
    shipment = await shipment_repo.get(record_id)
    if not shipment:
        raise AppError(404, "SHIPMENT_NOT_FOUND", "Inbound shipment was not found.")
    warehouse_id = warehouse_for(user, None)
    if shipment["warehouse_id"] != warehouse_id:
        raise AppError(403, "FORBIDDEN", "Shipment belongs to another warehouse.")
    if shipment["status"] in ("COMPLETED", "RECEIVED"):
        raise AppError(409, "SHIPMENT_ALREADY_COMPLETED", "This shipment has already been received.")
    if shipment["status"] != "RECEIVING":
        raise AppError(409, "INVALID_SHIPMENT_STATUS", "Find the shipment by tracking or ticket before completing it.")

    expected = {item["sku"].upper(): item["expected_quantity"] for item in shipment["expected_items"]}
    received = []
    for item in payload.items:
        product = None
        if item.barcode and item.barcode.strip():
            product = await product_repo.find_one({"barcode": item.barcode.strip(), "is_active": True})
            if not product:
                raise AppError(404, "PRODUCT_NOT_FOUND", f"No active product matches barcode {item.barcode.strip()}.")
        if item.sku and item.sku.strip():
            sku_product = await product_repo.find_one({"sku": item.sku.strip().upper(), "is_active": True})
            if product and (not sku_product or product["sku"] != sku_product["sku"]):
                raise AppError(400, "PRODUCT_MISMATCH", "Scanned barcode does not match the selected product.")
            product = product or sku_product
        if not product or product["sku"] not in expected:
            raise AppError(400, "UNEXPECTED_PRODUCT", "Product is not expected on this inbound shipment.")
        good = item.received_quantity - item.damaged_quantity
        difference = item.received_quantity - expected[product["sku"]]
        received.append({
            "sku": product["sku"], "product_name": product["name"], "barcode": product.get("barcode"),
            "expected_quantity": expected[product["sku"]], "received_quantity": item.received_quantity,
            "good_quantity": good, "damaged_quantity": item.damaged_quantity,
            "difference": difference,
            "quantity_status": "MATCHED" if difference == 0 else ("SHORT_RECEIVED" if difference < 0 else "OVER_RECEIVED"),
        })
    actual_skus = [item["sku"] for item in received]
    if len(actual_skus) != len(set(actual_skus)):
        raise AppError(400, "DUPLICATE_SKU", "Each expected product can be received only once.")
    if set(actual_skus) != set(expected):
        raise AppError(400, "MISSING_EXPECTED_PRODUCT", "Receive every expected product before completing the shipment.")

    claim = await get_database().inbound_shipments.update_one(
        {"_id": ObjectId(record_id), "status": "RECEIVING"},
        {"$set": {"status": "COMPLETING", "updated_at": datetime.now(timezone.utc)}},
    )
    if claim.modified_count != 1:
        raise AppError(409, "SHIPMENT_ALREADY_COMPLETED", "Shipment is already being completed.")
    applied = []
    try:
        for item in received:
            changes = {"on_hand_quantity": item["received_quantity"], "damaged_quantity": item["damaged_quantity"]}
            await change_quantities(
                warehouse_id, item["sku"], changes, "INBOUND", "INBOUND_SHIPMENT",
                shipment["shipment_id"], user, transaction_quantity=item["received_quantity"],
            )
            applied.append((item["sku"], changes))
    except Exception:
        for sku, changes in applied:
            await get_database().inventory.update_one({"warehouse_id": warehouse_id, "sku": sku}, {"$inc": {field: -value for field, value in changes.items()}})
        await shipment_repo.update(record_id, {"status": "RECEIVING", "updated_at": datetime.now(timezone.utc)})
        raise

    now = datetime.now(timezone.utc)
    for item in received:
        if item["damaged_quantity"]:
            report = await damage_repo.create(DamageReport(
                damage_report_id=f"DMG-{uuid4().hex[:10].upper()}", shipment_id=shipment["shipment_id"],
                warehouse_id=warehouse_id, sku=item["sku"], damage_quantity=item["damaged_quantity"],
                damage_type="OTHER", damage_reason="Recorded during expected inbound receiving",
                reported_by=user.id, reported_at=now.isoformat(),
            ).to_document())
            await record(user, "REPORT_DAMAGE", "DAMAGE_REPORT", report["id"], warehouse_id, new=report)
    updated = await shipment_repo.update(record_id, {
        "received_items": received, "received_by": user.id, "received_at": now.isoformat(),
        "completed_at": now.isoformat(), "status": "COMPLETED", "updated_at": now,
    })
    await record(user, "COMPLETE", "INBOUND_SHIPMENT", record_id, warehouse_id, shipment, updated)
    return updated


async def complete_receiving(payload: DirectReceiptCreate, user: User) -> dict:
    """Validate and post a direct worker receipt with all derived fields server-side."""
    warehouse_id = warehouse_for(user, payload.warehouse_id)
    if payload.tracking_number and await shipment_repo.find_one({"tracking_number": payload.tracking_number}):
        raise AppError(409, "SHIPMENT_ALREADY_RECEIVED", "This tracking number has already been received.")
    if payload.ticket_number and await shipment_repo.find_one({"ticket_number": payload.ticket_number}):
        raise AppError(409, "SHIPMENT_ALREADY_RECEIVED", "This ticket number has already been received.")

    normalized_items = []
    for item in payload.items:
        product = None
        if item.barcode and item.barcode.strip():
            product = await product_repo.find_one({"barcode": item.barcode.strip()})
            if not product:
                raise AppError(404, "PRODUCT_NOT_FOUND", f"No active product matches barcode {item.barcode.strip()}. Ask the owner to create it in Products / SKUs.")
        if item.sku and item.sku.strip():
            sku_product = await product_repo.find_one({"sku": item.sku.strip().upper()})
            if product and (not sku_product or sku_product["sku"] != product["sku"]):
                raise AppError(400, "PRODUCT_MISMATCH", "The scanned barcode does not match the selected product.")
            product = product or sku_product
        if not product or not product.get("is_active", True):
            identifier = item.barcode or item.sku
            raise AppError(404, "PRODUCT_NOT_FOUND", f"No active product matches {identifier}. Ask the owner to create it in Products / SKUs.")
        good_quantity = item.received_quantity - item.damaged_quantity
        normalized_items.append({
            "sku": product["sku"], "product_name": product["name"], "barcode": product.get("barcode"),
            "received_quantity": item.received_quantity, "good_quantity": good_quantity,
            "damaged_quantity": item.damaged_quantity, "quarantine_quantity": 0,
        })
    skus = [item["sku"] for item in normalized_items]
    if len(skus) != len(set(skus)):
        raise AppError(400, "DUPLICATE_SKU", "Each product can appear only once on a receipt.")

    model = InboundShipment(
        shipment_id=f"IN-{uuid4().hex[:10].upper()}", warehouse_id=warehouse_id,
        source_type=payload.source_type, tracking_number=payload.tracking_number,
        ticket_number=payload.ticket_number, supplier_name=payload.supplier_name,
        supplier_reference=payload.supplier_reference, status="RECEIVING", expected_items=[],
        received_items=normalized_items, created_by=user.id, received_by=user.id,
    )
    created = await shipment_repo.create(model.to_document())
    applied = []
    try:
        for item in normalized_items:
            changes = {"on_hand_quantity": item["received_quantity"], "damaged_quantity": item["damaged_quantity"]}
            await change_quantities(
                warehouse_id, item["sku"], changes, "INBOUND", "INBOUND_SHIPMENT",
                created["shipment_id"], user, transaction_quantity=item["received_quantity"],
            )
            applied.append((item["sku"], changes))
    except Exception:
        for sku, changes in applied:
            await get_database().inventory.update_one(
                {"warehouse_id": warehouse_id, "sku": sku},
                {"$inc": {field: -quantity for field, quantity in changes.items()}},
            )
        await shipment_repo.update(created["id"], {"status": "FAILED", "updated_at": datetime.now(timezone.utc)})
        raise

    now = datetime.now(timezone.utc)
    for item in normalized_items:
        if item["damaged_quantity"]:
            damage = DamageReport(
                damage_report_id=f"DMG-{uuid4().hex[:10].upper()}", shipment_id=created["shipment_id"],
                warehouse_id=warehouse_id, sku=item["sku"], damage_quantity=item["damaged_quantity"],
                damage_type="OTHER", damage_reason="Recorded during inbound receiving",
                notes="Automatically created from the completed receipt.", reported_by=user.id,
                reported_at=now.isoformat(),
            )
            report = await damage_repo.create(damage.to_document())
            await record(user, "REPORT_DAMAGE", "DAMAGE_REPORT", report["id"], warehouse_id, new=report)
    updated = await shipment_repo.update(created["id"], {
        "status": "RECEIVED", "received_by": user.id, "received_at": now.isoformat(),
        "completed_at": now.isoformat(), "updated_at": now,
    })
    await record(user, "COMPLETE_RECEIVING", "INBOUND_SHIPMENT", created["id"], warehouse_id, created, updated)
    return updated


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
