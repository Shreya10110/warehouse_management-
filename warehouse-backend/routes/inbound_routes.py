from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, UploadFile

from core.exceptions import AppError
from dependencies.auth import get_current_user, require_owner_or_manager
from models.user_model import User
from schemas.domain_schemas import DamageCreate, DirectReceiptCreate, ResolutionRequest, ShipmentCreate, ShipmentReceive
from services import inbound_service
from services.audit_service import record
from services.image_service import upload_image
from services.inventory_service import change_quantities

router = APIRouter(tags=["Inbound and Damage"])


def scoped_query(user: User) -> dict:
    """Return a warehouse query for staff or an unrestricted owner query."""
    return {} if user.role.value == "OWNER" else {"warehouse_id": user.warehouse_id}


@router.post("/inbound/shipments")
async def create_shipment(payload: ShipmentCreate, user: User = Depends(get_current_user)):
    """Register an inbound shipment in the authenticated warehouse context."""
    if user.role.value not in ("OWNER", "MANAGER", "INBOUND"):
        raise AppError(403, "FORBIDDEN", "Outbound staff cannot create inbound shipments.")
    return await inbound_service.create_shipment(payload, user)


@router.post("/inbound/receipts")
async def complete_receiving(payload: DirectReceiptCreate, user: User = Depends(get_current_user)):
    """Receive inspected stock in one worker action with server-derived fields."""
    if user.role.value not in ("OWNER", "MANAGER", "INBOUND"):
        raise AppError(403, "FORBIDDEN", "Outbound staff cannot receive inbound shipments.")
    return await inbound_service.complete_receiving(payload, user)


@router.get("/inbound/shipments")
async def shipments(status: str | None = None, search: str | None = None, skip: int = 0, limit: int = 100, user: User = Depends(get_current_user)):
    """List inbound shipments visible to the logged-in user."""
    query = scoped_query(user)
    if status:
        query["status"] = status
    if search:
        query["$or"] = [{"shipment_id": {"$regex": search, "$options": "i"}}, {"tracking_number": {"$regex": search, "$options": "i"}}, {"ticket_number": {"$regex": search, "$options": "i"}}, {"supplier_name": {"$regex": search, "$options": "i"}}]
    return await inbound_service.shipment_repo.list(query, limit=limit, skip=skip)


@router.get("/inbound/shipments/{shipment_id}")
async def shipment(shipment_id: str, user: User = Depends(get_current_user)):
    """Read one inbound shipment with warehouse isolation."""
    item = await inbound_service.shipment_repo.get(shipment_id)
    if not item:
        raise AppError(404, "SHIPMENT_NOT_FOUND", "Inbound shipment was not found.")
    if user.role.value != "OWNER" and item["warehouse_id"] != user.warehouse_id:
        raise AppError(403, "FORBIDDEN", "Shipment belongs to another warehouse.")
    return item


@router.post("/inbound/shipments/{shipment_id}/receive")
async def receive(shipment_id: str, payload: ShipmentReceive, user: User = Depends(get_current_user)):
    """Validate inspection and post an inbound shipment exactly once."""
    if user.role.value not in ("OWNER", "MANAGER", "INBOUND"):
        raise AppError(403, "FORBIDDEN", "Outbound staff cannot receive inbound shipments.")
    return await inbound_service.receive_shipment(shipment_id, payload, user)


@router.post("/inbound/shipments/{shipment_id}/damage")
async def damage(shipment_id: str, payload: DamageCreate, user: User = Depends(get_current_user)):
    """Create a damage report for an inbound shipment."""
    return await inbound_service.create_damage(shipment_id, payload, user)


@router.post("/damage-reports/{report_id}/images")
async def damage_image(report_id: str, image: UploadFile = File(...), user: User = Depends(get_current_user)):
    """Upload a damage evidence image and attach its secure URL."""
    report = await inbound_service.damage_repo.get(report_id)
    if not report:
        raise AppError(404, "DAMAGE_REPORT_NOT_FOUND", "Damage report was not found.")
    if user.role.value != "OWNER" and report["warehouse_id"] != user.warehouse_id:
        raise AppError(403, "FORBIDDEN", "Damage report belongs to another warehouse.")
    if not image.content_type or not image.content_type.startswith("image/"):
        raise AppError(400, "INVALID_IMAGE", "Only image files are supported.")
    url = await upload_image(await image.read(), image.filename or "damage-image")
    urls = report.get("image_urls", []) + [url]
    return await inbound_service.damage_repo.update(report_id, {"image_urls": urls, "updated_at": datetime.now(timezone.utc)})


@router.get("/damage-reports")
async def damage_reports(status: str | None = None, search: str | None = None, skip: int = 0, limit: int = 100, user: User = Depends(get_current_user)):
    """List damage reports visible to the logged-in user."""
    query = scoped_query(user)
    if status:
        query["resolution_status"] = status
    if search:
        query["$or"] = [{"damage_report_id": {"$regex": search, "$options": "i"}}, {"sku": {"$regex": search, "$options": "i"}}]
    return await inbound_service.damage_repo.list(query, limit=limit, skip=skip)


@router.get("/damage-reports/{report_id}")
async def damage_report(report_id: str, user: User = Depends(get_current_user)):
    """Read one damage report with warehouse isolation."""
    item = await inbound_service.damage_repo.get(report_id)
    if not item:
        raise AppError(404, "DAMAGE_REPORT_NOT_FOUND", "Damage report was not found.")
    if user.role.value != "OWNER" and item["warehouse_id"] != user.warehouse_id:
        raise AppError(403, "FORBIDDEN", "Damage report belongs to another warehouse.")
    return item


@router.post("/damage-reports/{report_id}/resolve")
async def resolve_damage(report_id: str, payload: ResolutionRequest, user: User = Depends(require_owner_or_manager)):
    """Resolve damaged or quarantined stock and create history."""
    report = await inbound_service.damage_repo.get(report_id)
    if not report:
        raise AppError(404, "DAMAGE_REPORT_NOT_FOUND", "Damage report was not found.")
    if user.role.value != "OWNER" and report["warehouse_id"] != user.warehouse_id:
        raise AppError(403, "FORBIDDEN", "Damage report belongs to another warehouse.")
    quantity = report["damage_quantity"]
    changes = {}
    if payload.resolution in ("RETURN_TO_SUPPLIER", "DISPOSE"):
        changes = {"on_hand_quantity": -quantity, "damaged_quantity": -quantity}
    elif payload.resolution == "MOVE_TO_GOOD_STOCK":
        changes = {"damaged_quantity": -quantity}
    if changes:
        await change_quantities(report["warehouse_id"], report["sku"], changes, "DISPOSE" if payload.resolution == "DISPOSE" else "ADJUSTMENT", "DAMAGE_REPORT", report["damage_report_id"], user)
    now = datetime.now(timezone.utc)
    updated = await inbound_service.damage_repo.update(report_id, {"resolution_status": "RESOLVED", "resolution": payload.resolution, "resolved_by": user.id, "resolved_at": now.isoformat(), "updated_at": now})
    await record(user, "RESOLVE", "DAMAGE_REPORT", report_id, report["warehouse_id"], report, updated)
    return updated
