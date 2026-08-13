from fastapi import APIRouter, Depends

from dependencies.auth import get_current_user, require_manager, require_owner
from models.user_model import User
from schemas.domain_schemas import IssueCreate, IssueResolution
from services import issue_service

router = APIRouter(tags=["Manager Issues"])


@router.post("/issues")
async def create_issue(payload: IssueCreate, user: User = Depends(require_manager)):
    """Submit a manager issue or request to Admin."""
    return await issue_service.create_issue(payload, user)


@router.get("/issues")
async def issues(status: str | None = None, user: User = Depends(get_current_user)):
    """List issue requests for Admin or the assigned warehouse manager."""
    if user.role.value not in ("OWNER", "MANAGER"):
        from core.exceptions import AppError
        raise AppError(403, "FORBIDDEN", "Only Admin and managers can access issue requests.")
    return await issue_service.list_issues(user, status)


@router.post("/issues/{issue_id}/resolve")
async def resolve_issue(issue_id: str, payload: IssueResolution, user: User = Depends(require_owner)):
    """Approve, reject, or resolve a manager issue as Admin."""
    return await issue_service.resolve_issue(issue_id, payload, user)
