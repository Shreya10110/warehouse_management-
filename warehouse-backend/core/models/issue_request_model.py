from typing import Any

from pydantic import Field

from models.base import MongoModel


class IssueRequest(MongoModel):
    """Warehouse-manager issue or request escalated to the Admin."""
    issue_id: str
    warehouse_id: str
    raised_by: str
    category: str
    subject: str
    description: str
    priority: str = "MEDIUM"
    status: str = "OPEN"
    admin_response: str | None = None
    resolved_by: str | None = None
    resolved_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
