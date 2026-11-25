"""Audit entries for course, module, lesson, landing and gallery changes.

Entries record who changed which entity and which fields. Values are kept
only for short scalar fields (prices, duration, publication and preview flags,
ordering, titles); HTML bodies, descriptions and other free text are named but
never copied, so the append-only log holds no lesson content or personal data.
"""

from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit_service import append_audit_log


AUDITED_VALUE_FIELDS = frozenset(
    {
        "title",
        "landing_title",
        "price_self",
        "price_support",
        "access_days",
        "is_published",
        "is_preview",
        "order_index",
        "duration_seconds",
    }
)
MAX_TEXT_LENGTH = 255


def _short_value(value: Any) -> Any:
    if isinstance(value, str):
        return value[:MAX_TEXT_LENGTH]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return None


def snapshot(entity: Any) -> dict[str, Any]:
    """The audited scalar values an entity currently has."""
    return {
        field: _short_value(getattr(entity, field))
        for field in sorted(AUDITED_VALUE_FIELDS)
        if hasattr(entity, field)
    }


def changed_fields(entity: Any, update_data: dict[str, Any]) -> list[str]:
    return sorted(
        field for field, value in update_data.items() if getattr(entity, field) != value
    )


def audit_content_update(
    db: AsyncSession,
    request: Request,
    actor_id: UUID,
    *,
    object_type: str,
    object_id: UUID,
    entity: Any,
    update_data: dict[str, Any],
) -> None:
    """Record an update; call before the new values are applied to entity."""
    fields = changed_fields(entity, update_data)
    if not fields:
        return
    old_value = {
        field: _short_value(getattr(entity, field))
        for field in fields
        if field in AUDITED_VALUE_FIELDS
    }
    new_value = {
        field: _short_value(update_data[field])
        for field in fields
        if field in AUDITED_VALUE_FIELDS
    }
    append_audit_log(
        db,
        actor_user_id=actor_id,
        action=f"{object_type}.update",
        object_type=object_type,
        object_id=str(object_id),
        old_value=old_value,
        new_value={"changed_fields": fields, **new_value},
        correlation_id=request.state.correlation_id,
    )


def audit_content_event(
    db: AsyncSession,
    request: Request,
    actor_id: UUID,
    *,
    action: str,
    object_type: str,
    object_id: UUID | None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
) -> None:
    append_audit_log(
        db,
        actor_user_id=actor_id,
        action=f"{object_type}.{action}",
        object_type=object_type,
        object_id=str(object_id) if object_id is not None else None,
        old_value=old_value,
        new_value=new_value,
        correlation_id=request.state.correlation_id,
    )
