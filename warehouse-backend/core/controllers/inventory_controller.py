from datetime import datetime, timezone

from core.exceptions import AppError
from cruds.base_crud import CRUDRepository
from models.user_model import User
from schemas.domain_schemas import InventoryAdjustment
from services.inventory_service import change_quantities, list_inventory

transaction_repo = CRUDRepository("inventory_transactions")


async def adjust(payload: InventoryAdjustment, user: User) -> dict:
    """Apply an owner or manager inventory correction with complete history."""
    warehouse_id = payload.warehouse_id if user.role.value == "OWNER" else user.warehouse_id
    if not warehouse_id:
        raise AppError(400, "WAREHOUSE_REQUIRED", "warehouse_id is required.")
    return await change_quantities(
        warehouse_id, payload.sku.upper(), {"on_hand_quantity": payload.quantity_change},
        "ADJUSTMENT", "MANUAL_ADJUSTMENT", datetime.now(timezone.utc).isoformat(), user,
    )


async def history(user: User, warehouse_id: str | None = None) -> list[dict]:
    """List stock transaction history with warehouse isolation."""
    effective = warehouse_id if user.role.value == "OWNER" else user.warehouse_id
    if user.role.value != "OWNER" and warehouse_id and warehouse_id != user.warehouse_id:
        raise AppError(403, "FORBIDDEN", "You cannot access another warehouse.")
    return await transaction_repo.list({"warehouse_id": effective} if effective else {})
