from fastapi import APIRouter, Depends

from dependencies.auth import get_current_user
from models.user_model import User
from schemas.user_schemas import RejectionReason
from services import approval_service

router = APIRouter(prefix="/approvals", tags=["Registration Approvals"])


@router.get("/pending")
async def pending_registrations(user: User = Depends(get_current_user)):
    """List registrations awaiting action from the logged-in owner or manager."""
    return await approval_service.pending(user)


@router.post("/{user_id}/approve")
async def approve_registration(user_id: str, user: User = Depends(get_current_user)):
    """Approve a manager as owner or an own-warehouse employee as manager."""
    return await approval_service.approve(user_id, user)


@router.post("/{user_id}/reject")
async def reject_registration(user_id: str, payload: RejectionReason, user: User = Depends(get_current_user)):
    """Reject a registration with a visible reason for the applicant."""
    return await approval_service.reject(user_id, payload.reason, user)
