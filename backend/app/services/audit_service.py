"""Single append-only entrypoint for administrative audit events."""

import re
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

# Shown instead of operator free text to an audit reader without pii.read.
REDACTED_FREE_TEXT = "[скрыто: нет доступа к персональным данным]"
# Actions whose reason and note fields are operator free text about a customer.
_FREE_TEXT_ACTION_PREFIXES = ("refund.", "student.note.")
_FREE_TEXT_KEYS = frozenset({"reason", "note", "body"})
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# Digits with phone separators, not glued to letters, dashes or other digits, so
# UUIDs, ISO dates and plain numbers are left alone.
_PHONE_RE = re.compile(r"(?<![\w\-+])\+?\d[\d\s()\-]{8,}\d(?![\w\-])")


def _mask_email(match: re.Match[str]) -> str:
    local, _, domain = match.group(0).partition("@")
    return f"{local[:1]}***@{domain}"


def _mask_phone(match: re.Match[str]) -> str:
    digits = "".join(character for character in match.group(0) if character.isdigit())
    # E.164 numbers have at most 15 digits; longer runs are identifiers.
    if not 10 <= len(digits) <= 15:
        return match.group(0)
    return f"***{digits[-4:]}"


def mask_personal_data(value: Any) -> Any:
    """Mask emails and phone numbers inside strings, recursively."""
    if isinstance(value, str):
        return _PHONE_RE.sub(_mask_phone, _EMAIL_RE.sub(_mask_email, value))
    if isinstance(value, dict):
        return {key: mask_personal_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [mask_personal_data(item) for item in value]
    return value


def _redact_free_text(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                REDACTED_FREE_TEXT
                if key in _FREE_TEXT_KEYS and isinstance(item, str) and item
                else _redact_free_text(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_free_text(item) for item in value]
    return value


def redact_audit_entry(entry: AuditLog) -> dict[str, Any]:
    """Reader view of an audit record for someone without pii.read."""
    free_text = entry.action.startswith(_FREE_TEXT_ACTION_PREFIXES)
    old_value = entry.old_value
    new_value = entry.new_value
    reason = entry.reason
    if free_text:
        old_value = _redact_free_text(old_value)
        new_value = _redact_free_text(new_value)
        reason = REDACTED_FREE_TEXT if reason else reason
    return {
        "id": entry.id,
        "actor_user_id": entry.actor_user_id,
        "action": entry.action,
        "object_type": entry.object_type,
        "object_id": entry.object_id,
        "old_value": mask_personal_data(old_value),
        "new_value": mask_personal_data(new_value),
        "reason": mask_personal_data(reason),
        "correlation_id": entry.correlation_id,
        "created_at": entry.created_at,
    }


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
