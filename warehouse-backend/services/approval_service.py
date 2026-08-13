from datetime import datetime, timezone

from core.exceptions import AppError
from cruds.base_crud import CRUDRepository
from cruds.user_crud import find_user_by_id, list_users, update_user
from models.user_model import ApprovalStatus, User, UserRole
from services.audit_service import record
from services.auth_service import public_user

warehouse_repo = CRUDRepository("warehouses")


def can_review(reviewer: User, applicant: User) -> bool:
    """Return whether the reviewer owns the applicant's required approval step."""
    if reviewer.role == UserRole.OWNER:
        return applicant.role == UserRole.MANAGER and applicant.approval_status == ApprovalStatus.PENDING_OWNER_APPROVAL
    if reviewer.role == UserRole.MANAGER:
        return (
            applicant.role in (UserRole.INBOUND, UserRole.OUTBOUND)
            and applicant.warehouse_id == reviewer.warehouse_id
            and applicant.approval_status == ApprovalStatus.PENDING_MANAGER_APPROVAL
        )
    return False


async def pending(reviewer: User) -> list[dict]:
    """List manager registrations for owners or own-warehouse employees for managers."""
    if reviewer.role == UserRole.OWNER:
        query = {"role": UserRole.MANAGER.value, "approval_status": ApprovalStatus.PENDING_OWNER_APPROVAL.value}
    elif reviewer.role == UserRole.MANAGER:
        query = {
            "role": {"$in": [UserRole.INBOUND.value, UserRole.OUTBOUND.value]},
            "warehouse_id": reviewer.warehouse_id,
            "approval_status": ApprovalStatus.PENDING_MANAGER_APPROVAL.value,
        }
    else:
        raise AppError(403, "FORBIDDEN", "Only owners and managers can review registrations.")
    return [public_user(user).model_dump(mode="json") for user in await list_users(query)]


async def approve(applicant_id: str, reviewer: User) -> dict:
    """Approve an account only through its designated owner or warehouse manager."""
    applicant = await find_user_by_id(applicant_id)
    if not applicant:
        raise AppError(404, "USER_NOT_FOUND", "Registration was not found.")
    if not can_review(reviewer, applicant):
        raise AppError(403, "FORBIDDEN", "You cannot approve this registration.")
    warehouse = await warehouse_repo.get(applicant.warehouse_id) if applicant.role == UserRole.MANAGER else None
    now = datetime.now(timezone.utc)
    updated = await update_user(applicant.id, {
        "approval_status": ApprovalStatus.APPROVED.value, "is_active": True,
        "approved_by": reviewer.id, "approved_at": now, "rejection_reason": None, "updated_at": now,
    })
    if applicant.role == UserRole.MANAGER and warehouse and not warehouse.get("manager_id"):
        await warehouse_repo.update(applicant.warehouse_id, {"manager_id": applicant.id, "updated_at": now})
    result = public_user(updated).model_dump(mode="json")
    await record(reviewer, "APPROVE_REGISTRATION", "USER", applicant.id, applicant.warehouse_id, public_user(applicant).model_dump(mode="json"), result)
    return result


async def reject(applicant_id: str, reason: str, reviewer: User) -> dict:
    """Reject a pending registration through its designated reviewer."""
    applicant = await find_user_by_id(applicant_id)
    if not applicant:
        raise AppError(404, "USER_NOT_FOUND", "Registration was not found.")
    if not can_review(reviewer, applicant):
        raise AppError(403, "FORBIDDEN", "You cannot reject this registration.")
    now = datetime.now(timezone.utc)
    updated = await update_user(applicant.id, {
        "approval_status": ApprovalStatus.REJECTED.value, "is_active": False,
        "approved_by": reviewer.id, "approved_at": now, "rejection_reason": reason, "updated_at": now,
    })
    result = public_user(updated).model_dump(mode="json")
    await record(reviewer, "REJECT_REGISTRATION", "USER", applicant.id, applicant.warehouse_id, public_user(applicant).model_dump(mode="json"), result, {"reason": reason})
    return result
