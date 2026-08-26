"""Single append-only entrypoint for administrative audit events."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


def append_audit_log(
    db: AsyncSession,
    *,
    actor_user_id: UUID | None,
    action: str,
    object_type: str,
    object_id: str | None,
    correlation_id: str,
    reason: str | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        old_value=old_value,
        new_value=new_value,
        reason=reason.strip() if reason else None,
        correlation_id=correlation_id,
    )
    db.add(entry)
    return entry

