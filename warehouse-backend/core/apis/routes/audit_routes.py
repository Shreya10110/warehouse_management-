from fastapi import APIRouter, Depends

from core.exceptions import AppError
from dependencies.auth import get_current_user
from models.user_model import User
from services.audit_service import audit_repo

router = APIRouter(tags=["Audit"])


@router.get("/audit-logs")
async def audit_logs(entity_type: str | None = None, action: str | None = None, skip: int = 0, limit: int = 100, user: User = Depends(get_current_user)):
    """List company audit logs for owners or own-warehouse events for managers."""
    if user.role.value not in ("OWNER", "MANAGER"):
        raise AppError(403, "FORBIDDEN", "Audit logs are restricted to owners and managers.")
    query = {} if user.role.value == "OWNER" else {"warehouse_id": user.warehouse_id}
    if entity_type:
        query["entity_type"] = entity_type
    if action:
        query["action"] = action
    return await audit_repo.list(query, limit=limit, skip=skip)


@router.get("/warehouses/{warehouse_id}/audit-logs")
async def warehouse_audit_logs(warehouse_id: str, user: User = Depends(get_current_user)):
    """List audit events for one authorized warehouse."""
    if user.role.value != "OWNER" and (user.role.value != "MANAGER" or user.warehouse_id != warehouse_id):
        raise AppError(403, "FORBIDDEN", "You cannot access this warehouse's audit logs.")
    return await audit_repo.list({"warehouse_id": warehouse_id})
