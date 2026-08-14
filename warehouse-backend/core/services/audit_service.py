from models.audit_log_model import AuditLog
from models.user_model import User
from cruds.base_crud import CRUDRepository

audit_repo = CRUDRepository("audit_logs")


async def record(user: User, action: str, entity_type: str, entity_id: str, warehouse_id: str | None, old=None, new=None, metadata=None) -> dict:
    """Persist an immutable audit event for a domain change."""
    event = AuditLog(
        user_id=user.id, user_role=user.role.value, warehouse_id=warehouse_id,
        action=action, entity_type=entity_type, entity_id=entity_id,
        old_value=old, new_value=new, metadata=metadata or {},
    )
    return await audit_repo.create(event.to_document())
