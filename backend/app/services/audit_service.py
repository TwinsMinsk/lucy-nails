"""Single append-only entrypoint for administrative audit events."""

import re
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

# Shown instead of any value a reader without pii.read may not see.
REDACTED_FREE_TEXT = "[скрыто: нет доступа к персональным данным]"

# Structured audit fields that never hold personal data. Every other key keeps
# its name but its value is replaced, and even these keys pass only values of a
# safe shape (number, flag, id, date, lowercase code).
_SAFE_KEYS = frozenset({
    "status", "entitlement_status", "payment_status", "processed", "revoked",
    "enabled", "checkout_enabled", "reauthentication_required", "notification",
    "tariff", "role", "roles", "days", "access_days", "amount_kopecks", "attempts",
    "count", "expires_at", "purchase_expires_at", "revoked_at", "issued_at",
    "user_id", "course_id", "purchase_id", "order_id", "entitlement_id",
    "refund_id", "certificate_id", "outbox_message_id", "session_id",
    # Content and pricing changes (app/services/content_audit.py). Titles are
    # free text and stay off this list.
    "price_self", "price_support", "is_published", "is_preview", "order_index",
    "duration_seconds", "changed_fields", "module_id",
})
_UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_ISO_DATETIME_RE = re.compile(r"\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?)?")
# Lowercase codes such as "active", "dead_letter", "account_activation".
_CODE_RE = re.compile(r"[a-z][a-z_.]{0,63}")
# The shape of an id the server generates itself (uuid4); a client-supplied
# X-Correlation-ID may be anything the header pattern allows, a phone included.
_SERVER_CORRELATION_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)


def _is_safe_scalar(value: Any) -> bool:
    if value is None or isinstance(value, (bool, int, float)):
        return True
    if isinstance(value, str):
        return any(
            pattern.fullmatch(value) for pattern in (_UUID_RE, _ISO_DATETIME_RE, _CODE_RE)
        )
    return False


def _safe_value(key: str, value: Any) -> Any:
    if key in _SAFE_KEYS:
        if _is_safe_scalar(value):
            return value
        if isinstance(value, list) and all(_is_safe_scalar(item) for item in value):
            return value
        # e.g. a gallery reorder: {"<item uuid>": <order index>}.
        if isinstance(value, dict) and all(
            isinstance(item_key, str) and _UUID_RE.fullmatch(item_key) and _is_safe_scalar(item)
            for item_key, item in value.items()
        ):
            return value
    return REDACTED_FREE_TEXT


def _redact_values(values: dict | None) -> dict | None:
    if values is None:
        return None
    return {key: _safe_value(key, value) for key, value in values.items()}


def redact_audit_entry(entry: AuditLog) -> dict[str, Any]:
    """Reader view of an audit record for someone without pii.read.

    Only an allow-list of structured fields passes; reasons, notes, tags and any
    other free text are replaced by a marker.
    """
    object_id = entry.object_id
    if object_id is not None and not (_UUID_RE.fullmatch(object_id) or _CODE_RE.fullmatch(object_id)):
        object_id = REDACTED_FREE_TEXT
    return {
        "id": entry.id,
        "actor_user_id": entry.actor_user_id,
        "action": entry.action,
        "object_type": entry.object_type,
        "object_id": object_id,
        "old_value": _redact_values(entry.old_value),
        "new_value": _redact_values(entry.new_value),
        "reason": REDACTED_FREE_TEXT if entry.reason else None,
        "correlation_id": (
            entry.correlation_id
            if _SERVER_CORRELATION_RE.fullmatch(entry.correlation_id or "")
            else REDACTED_FREE_TEXT
        ),
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
