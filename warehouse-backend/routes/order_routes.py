from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from core.exceptions import AppError
from dependencies.auth import get_current_user, require_outbound, require_owner
from models.user_model import User
from schemas.domain_schemas import OrderCreate, PackageCreate, PickRequest, RejectionRequest, WarehouseAssignment
from services import order_service
from services.audit_service import record
from services.label_service import render_shipping_label

router = APIRouter(tags=["Outbound Orders"])


@router.post("/orders")
async def create_order(payload: OrderCreate, user: User = Depends(require_owner)):
    """Create an outbound order and calculate complete-stock warehouses."""
    return await order_service.create_order(payload, user)


@router.get("/orders")
async def orders(status: str | None = None, warehouse_id: str | None = None, search: str | None = None, skip: int = 0, limit: int = 100, user: User = Depends(get_current_user)):
    """List all orders for owners or assigned warehouse orders for staff."""
    query = {} if user.role.value == "OWNER" else {"assigned_warehouse_id": user.warehouse_id}
    if user.role.value == "OWNER" and warehouse_id:
        query["assigned_warehouse_id"] = warehouse_id
    if status:
        query["status"] = status
    if search:
        query["$or"] = [{"order_id": {"$regex": search, "$options": "i"}}, {"customer_name": {"$regex": search, "$options": "i"}}, {"items.sku": {"$regex": search, "$options": "i"}}]
    return await order_service.order_repo.list(query, limit=limit, skip=skip)


@router.get("/orders/my-warehouse")
async def my_orders(status: str | None = None, user: User = Depends(get_current_user)):
    """List the assigned warehouse outbound queue with an optional status filter."""
    if not user.warehouse_id:
        raise AppError(400, "WAREHOUSE_REQUIRED", "This endpoint is for warehouse teams.")
    query = {"assigned_warehouse_id": user.warehouse_id}
    if status:
        query["status"] = status
    return await order_service.order_repo.list(query)


@router.get("/orders/{order_id}")
async def order(order_id: str, user: User = Depends(get_current_user)):
    """Read an order when the user is authorized for its warehouse."""
    item = await order_service.order_repo.get(order_id)
    if not item:
        raise AppError(404, "ORDER_NOT_FOUND", "Order was not found.")
    order_service.authorize_order(item, user)
    return item


@router.post("/orders/{order_id}/reject")
async def reject(order_id: str, payload: RejectionRequest, user: User = Depends(require_owner)):
    """Reject an order that no single warehouse can fulfill."""
    item = await order_service.order_repo.get(order_id)
    if not item:
        raise AppError(404, "ORDER_NOT_FOUND", "Order was not found.")
    eligible = await order_service.eligible_warehouses(item["items"])
    if eligible:
        raise AppError(409, "INVALID_ORDER_STATUS", "The order can currently be fulfilled and should be assigned.")
    updated = await order_service.order_repo.update(order_id, {"status": "REJECTED", "rejection_reason": payload.reason})
    await record(user, "REJECT", "ORDER", order_id, None, item, updated)
    return updated


@router.post("/orders/{order_id}/assign-warehouse")
async def assign(order_id: str, payload: WarehouseAssignment, user: User = Depends(require_owner)):
    """Select an eligible warehouse and atomically reserve all order lines."""
    return await order_service.assign_and_reserve(order_id, payload.warehouse_id, user)


@router.post("/orders/{order_id}/start-picking")
async def start_picking(order_id: str, user: User = Depends(require_outbound)):
    """Move a reserved order into the picking workflow."""
    return await order_service.transition(order_id, ("CREATED",), "PICKING", user)


@router.post("/orders/{order_id}/pick")
async def pick(order_id: str, payload: PickRequest, user: User = Depends(require_outbound)):
    """Record exact picked quantities for the order."""
    return await order_service.pick(order_id, payload, user)


@router.post("/orders/{order_id}/complete-picking")
async def complete_picking(order_id: str, user: User = Depends(require_outbound)):
    """Complete picking only after all order lines were recorded."""
    item = await order_service.order_repo.get(order_id)
    if not item or not item.get("picked_items"):
        raise AppError(400, "INVALID_QUANTITY", "Record all picked items before completing picking.")
    return await order_service.transition(order_id, ("PICKING",), "PICKED", user, {"picked_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()})


@router.post("/orders/{order_id}/pack")
async def pack(order_id: str, payload: PackageCreate, user: User = Depends(require_outbound)):
    """Pack a picked order and create its package record."""
    return await order_service.pack(order_id, payload, user)


@router.get("/packages/{package_id}")
async def package(package_id: str, user: User = Depends(get_current_user)):
    """Read an authorized package record."""
    item = await order_service.package_repo.get(package_id)
    if not item:
        raise AppError(404, "PACKAGE_NOT_FOUND", "Package was not found.")
    if user.role.value != "OWNER" and item["warehouse_id"] != user.warehouse_id:
        raise AppError(403, "FORBIDDEN", "Package belongs to another warehouse.")
    return item


@router.post("/packages/{package_id}/generate-label")
async def generate_label(package_id: str, user: User = Depends(require_outbound)):
    """Generate a printable internal shipping label URL for a packed package."""
    item = await package(package_id, user)
    url = f"/api/v1/packages/{package_id}/label"
    return await order_service.package_repo.update(package_id, {"label_url": url})


@router.get("/packages/{package_id}/label", response_class=HTMLResponse)
async def label(package_id: str, user: User = Depends(get_current_user)):
    """Render a clean printable shipping label with order and warehouse identity."""
    pkg = await package(package_id, user)
    order = await order_service.order_repo.find_one({"order_id": pkg["order_id"]})
    warehouse = await order_service.warehouse_repo.get(pkg["warehouse_id"])
    return render_shipping_label(pkg, order, warehouse)


@router.post("/packages/{package_id}/ship")
async def ship(package_id: str, user: User = Depends(require_outbound)):
    """Ship a packed package and consume its reserved inventory."""
    return await order_service.ship_package(package_id, user)


@router.post("/orders/{order_id}/cancel")
async def cancel(order_id: str, user: User = Depends(require_owner)):
    """Cancel an unshipped order and release reserved stock."""
    return await order_service.cancel(order_id, user)
