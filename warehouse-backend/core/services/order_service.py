from datetime import datetime, timezone
from uuid import uuid4

from core.exceptions import AppError
from cruds.base_crud import CRUDRepository, serialize
from models.order_model import Order
from models.audit_log_model import AuditLog
from models.inventory_transaction_model import InventoryTransaction
from models.package_model import Package
from models.user_model import User
from schemas.domain_schemas import OrderCreate, PackageCreate, PickRequest
from services.audit_service import record
from services.inventory_service import available, change_quantities, inventory_repo, product_repo, record_transaction

order_repo = CRUDRepository("orders")
package_repo = CRUDRepository("packages")
warehouse_repo = CRUDRepository("warehouses")
seller_repo = CRUDRepository("sellers")


async def eligible_warehouses(items: list[dict]) -> list[str]:
    """Return active warehouses that can fulfill every order line without splitting."""
    eligible = []
    for warehouse in await warehouse_repo.list({"is_active": True}):
        qualifies = True
        for line in items:
            inventory = await inventory_repo.find_one({"warehouse_id": warehouse["id"], "sku": line["sku"]})
            if not inventory or available(inventory) < line["quantity"]:
                qualifies = False
                break
        if qualifies:
            eligible.append(warehouse["id"])
    return eligible


async def create_order(payload: OrderCreate, user: User) -> dict:
    """Validate SKU lines and create an order with computed warehouse eligibility."""
    normalized = []
    if payload.seller_id:
        seller = await seller_repo.get(payload.seller_id)
        if not seller or not seller.get("is_active", True):
            raise AppError(404, "SELLER_NOT_FOUND", "Seller was not found or is inactive.")
    for line in payload.items:
        sku = line.sku.strip().upper()
        if not await product_repo.find_one({"sku": sku, "is_active": True}):
            raise AppError(404, "PRODUCT_NOT_FOUND", f"Product {sku} was not found or is inactive.")
        normalized.append({"sku": sku, "quantity": line.quantity})
    eligible = await eligible_warehouses(normalized)
    status = "AWAITING_WAREHOUSE_SELECTION" if eligible else "PENDING"
    model = Order(
        order_id=f"ORD-{uuid4().hex[:10].upper()}", created_by=user.id,
        eligible_warehouse_ids=eligible, status=status,
        **payload.model_dump(exclude={"items"}), items=normalized,
    )
    created = await order_repo.create(model.to_document())
    await record(user, "CREATE", "ORDER", created["id"], None, new=created, metadata={"eligible_warehouses": eligible})
    return created


async def assign_and_reserve(record_id: str, warehouse_id: str, user: User) -> dict:
    """Recheck eligibility and atomically reserve every line in the selected warehouse."""
    order = await order_repo.get(record_id)
    if not order:
        raise AppError(404, "ORDER_NOT_FOUND", "Order was not found.")
    if order["status"] not in ("PENDING", "AWAITING_WAREHOUSE_SELECTION"):
        raise AppError(409, "INVALID_ORDER_STATUS", "Order cannot be assigned in its current status.")
    eligible = await eligible_warehouses(order["items"])
    if warehouse_id not in eligible:
        raise AppError(409, "INSUFFICIENT_STOCK", "Selected warehouse cannot fulfill the complete order.")
    reserved = []
    try:
        for line in order["items"]:
            current = await inventory_repo.find_one({"warehouse_id": warehouse_id, "sku": line["sku"]})
            if not current or available(current) < line["quantity"]:
                raise AppError(409, "INSUFFICIENT_STOCK", "Inventory changed before reservation completed.")
            updated_inventory = await inventory_repo.update_where(
                {"_id": current["id"], "reserved_quantity": current["reserved_quantity"]},
                increments={"reserved_quantity": line["quantity"]},
            )
            if not updated_inventory:
                raise AppError(409, "INSUFFICIENT_STOCK", "Inventory changed before reservation completed.")
            reserved.append(line)
        updated_order = await order_repo.update_where(
            {"_id": record_id, "status": {"$in": ["PENDING", "AWAITING_WAREHOUSE_SELECTION"]}},
            {"assigned_warehouse_id": warehouse_id, "eligible_warehouse_ids": eligible, "status": "CREATED"},
        )
        if not updated_order:
            raise AppError(409, "INVALID_ORDER_STATUS", "Order changed before reservation completed.")
    except Exception:
        for line in reserved:
            await inventory_repo.update_where(
                {"warehouse_id": warehouse_id, "sku": line["sku"]}, increments={"reserved_quantity": -line["quantity"]}
            )
        raise
    for line in reserved:
        await record_transaction(warehouse_id, line["sku"], "RESERVE", line["quantity"], "ORDER", order["order_id"], user)
    await record(user, "ASSIGN_AND_RESERVE", "ORDER", record_id, warehouse_id, order, {"status": "CREATED", "assigned_warehouse_id": warehouse_id})
    updated = await order_repo.get(record_id)
    return updated


def authorize_order(order: dict, user: User) -> None:
    """Permit owners or assigned-warehouse managers and outbound staff to process an order."""
    if user.role.value == "OWNER":
        return
    if user.role.value not in ("MANAGER", "OUTBOUND") or order.get("assigned_warehouse_id") != user.warehouse_id:
        raise AppError(403, "FORBIDDEN", "This order is not assigned to your warehouse team.")


async def transition(record_id: str, expected: tuple[str, ...], target: str, user: User, values: dict | None = None) -> dict:
    """Authorize and perform a guarded outbound order status transition."""
    order = await order_repo.get(record_id)
    if not order:
        raise AppError(404, "ORDER_NOT_FOUND", "Order was not found.")
    authorize_order(order, user)
    if order["status"] not in expected:
        raise AppError(409, "INVALID_ORDER_STATUS", f"Order must be in {', '.join(expected)} status.")
    updated = await order_repo.update(record_id, {"status": target, "updated_at": datetime.now(timezone.utc)} | (values or {}))
    await record(user, target, "ORDER", record_id, order.get("assigned_warehouse_id"), order, updated)
    return updated


async def pick(record_id: str, payload: PickRequest, user: User) -> dict:
    """Validate picked lines match the order and save the picking result."""
    order = await order_repo.get(record_id)
    if not order:
        raise AppError(404, "ORDER_NOT_FOUND", "Order was not found.")
    expected = {item["sku"]: item["quantity"] for item in order["items"]}
    actual = {item.sku.upper(): item.quantity for item in payload.items}
    if actual != expected:
        raise AppError(400, "INVALID_QUANTITY", "Picked items must exactly match the order.")
    return await transition(record_id, ("PICKING",), "PICKING", user, {"picked_items": payload.model_dump()["items"], "picked_by": user.id})


async def pack(record_id: str, payload: PackageCreate, user: User) -> dict:
    """Create a package for a picked order and move the order to packed status."""
    order = await order_repo.get(record_id)
    if not order:
        raise AppError(404, "ORDER_NOT_FOUND", "Order was not found.")
    authorize_order(order, user)
    if order["status"] != "PICKED":
        raise AppError(409, "INVALID_ORDER_STATUS", "Only picked orders can be packed.")
    if await package_repo.find_one({"tracking_number": payload.tracking_number}):
        raise AppError(409, "DUPLICATE_TRACKING_NUMBER", "Tracking number already exists.")
    package = Package(
        package_id=f"PKG-{uuid4().hex[:10].upper()}", order_id=order["order_id"], warehouse_id=order["assigned_warehouse_id"],
        packed_by=user.id, packed_at=datetime.now(timezone.utc).isoformat(), **payload.model_dump(),
    )
    created = await package_repo.create(package.to_document())
    await transition(record_id, ("PICKED",), "PACKED", user, {"package_id": created["id"]})
    await record(user, "PACK", "PACKAGE", created["id"], order["assigned_warehouse_id"], new=created)
    return created


async def cancel(record_id: str, user: User) -> dict:
    """Cancel an unshipped order and release any reserved quantities."""
    order = await order_repo.get(record_id)
    if not order:
        raise AppError(404, "ORDER_NOT_FOUND", "Order was not found.")
    if order["status"] == "SHIPPED":
        raise AppError(409, "ORDER_ALREADY_SHIPPED", "A shipped order cannot be cancelled.")
    if order["status"] == "CANCELLED":
        raise AppError(409, "ORDER_ALREADY_CANCELLED", "Order is already cancelled.")
    cancellable = ("PENDING", "AWAITING_WAREHOUSE_SELECTION", "CREATED", "PICKING", "PICKED", "PACKED")
    if order["status"] not in cancellable:
        raise AppError(409, "INVALID_ORDER_STATUS", "Order cannot be cancelled in its current status.")
    authorize_order(order, user)
    claim = await order_repo.update_where(
        {"_id": record_id, "status": order["status"]},
        {"status": "CANCELLING", "updated_at": datetime.now(timezone.utc)},
    )
    if not claim:
        raise AppError(409, "INVALID_ORDER_STATUS", "Order changed before cancellation completed.")
    try:
        if order.get("assigned_warehouse_id") and order["status"] in ("CREATED", "PICKING", "PICKED", "PACKED"):
            for line in order["items"]:
                await change_quantities(order["assigned_warehouse_id"], line["sku"], {"reserved_quantity": -line["quantity"]}, "RELEASE", "ORDER", order["order_id"], user)
        updated = await order_repo.update(record_id, {"status": "CANCELLED", "updated_at": datetime.now(timezone.utc)})
        await record(user, "CANCEL", "ORDER", record_id, order.get("assigned_warehouse_id"), order, updated)
        return updated
    except Exception:
        await order_repo.update(record_id, {"status": order["status"], "updated_at": datetime.now(timezone.utc)})
        raise


async def ship_package(package_id: str, user: User) -> dict:
    """Ship a packed package and consume both on-hand and reserved inventory."""
    package = await package_repo.get(package_id)
    if not package:
        raise AppError(404, "PACKAGE_NOT_FOUND", "Package was not found.")
    order = await order_repo.find_one({"order_id": package["order_id"]})
    if not order:
        raise AppError(404, "ORDER_NOT_FOUND", "Order was not found.")
    authorize_order(order, user)
    if order["status"] != "PACKED" or package["status"] != "PACKED":
        raise AppError(409, "INVALID_ORDER_STATUS", "Only packed orders can be shipped.")
    package_claim = await package_repo.update_where({"_id": package_id, "status": "PACKED"}, {"status": "SHIPPING"})
    order_claim = await order_repo.update_where({"_id": order["id"], "status": "PACKED"}, {"status": "SHIPPING"})
    if not package_claim or not order_claim:
        if package_claim:
            await package_repo.update(package_id, {"status": "PACKED"})
        raise AppError(409, "INVALID_ORDER_STATUS", "Package is already being shipped.")
    applied = []
    try:
        for line in order["items"]:
            changes = {"on_hand_quantity": -line["quantity"], "reserved_quantity": -line["quantity"]}
            await change_quantities(
                order["assigned_warehouse_id"], line["sku"], changes,
                "SHIP", "ORDER", order["order_id"], user,
            )
            applied.append((line["sku"], changes))
        await package_repo.update(package_id, {"status": "SHIPPED", "updated_at": datetime.now(timezone.utc)})
        updated = await order_repo.update(order["id"], {"status": "SHIPPED", "updated_at": datetime.now(timezone.utc)})
        await record(user, "SHIP", "ORDER", order["id"], order["assigned_warehouse_id"], order, updated)
        return updated
    except Exception:
        for sku, changes in applied:
            await inventory_repo.update_where(
                {"warehouse_id": order["assigned_warehouse_id"], "sku": sku},
                increments={field: -quantity for field, quantity in changes.items()},
            )
        await package_repo.update(package_id, {"status": "PACKED"})
        await order_repo.update(order["id"], {"status": "PACKED"})
        raise
