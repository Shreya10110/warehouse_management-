from datetime import datetime, timezone
from uuid import uuid4

from core.exceptions import AppError
from cruds.base_crud import CRUDRepository
from models.issue_request_model import IssueRequest
from models.user_model import User
from schemas.domain_schemas import IssueCreate, IssueResolution
from services.audit_service import record

issue_repo = CRUDRepository("issue_requests")


async def create_issue(payload: IssueCreate, user: User) -> dict:
    """Create a warehouse-scoped manager escalation for Admin review."""
    if not user.warehouse_id:
        raise AppError(400, "WAREHOUSE_REQUIRED", "A manager must be assigned to a warehouse.")
    model = IssueRequest(
        issue_id=f"ISS-{uuid4().hex[:10].upper()}", warehouse_id=user.warehouse_id,
        raised_by=user.id, **payload.model_dump(),
    )
    created = await issue_repo.create(model.to_document())
    await record(user, "CREATE", "ISSUE_REQUEST", created["id"], user.warehouse_id, new=created)
    return created


async def list_issues(user: User, status: str | None = None) -> list[dict]:
    """List all issues for Admin or only the manager's assigned warehouse."""
    query = {} if user.role.value == "OWNER" else {"warehouse_id": user.warehouse_id}
    if status:
        query["status"] = status
    return await issue_repo.list(query)


async def resolve_issue(record_id: str, payload: IssueResolution, user: User) -> dict:
    """Record the Admin decision and immutable audit history for an issue."""
    issue = await issue_repo.get(record_id)
    if not issue:
        raise AppError(404, "ISSUE_NOT_FOUND", "Issue request was not found.")
    if issue["status"] != "OPEN":
        raise AppError(409, "ISSUE_ALREADY_RESOLVED", "Issue request already has a final decision.")
    now = datetime.now(timezone.utc)
    updated = await issue_repo.update(record_id, payload.model_dump() | {
        "resolved_by": user.id, "resolved_at": now.isoformat(), "updated_at": now,
    })
    await record(user, "RESOLVE", "ISSUE_REQUEST", record_id, issue["warehouse_id"], issue, updated)
    return updated
