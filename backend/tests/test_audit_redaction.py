"""Audit log reader view without pii.read (audit B6)."""

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.audit_log import AuditLog
from app.models.rbac import Permission, Role, UserRoleAssignment
from app.models.user import User
from app.services.audit_service import REDACTED_FREE_TEXT, mask_personal_data


async def _login(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    response = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    client.cookies.clear()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _staff(
    client: AsyncClient, db: AsyncSession, email: str, permissions: list[str]
) -> dict[str, str]:
    user = User(
        email_verified_at=datetime.utcnow(),
        email=email,
        password_hash=get_password_hash("staffpass1"),
        role="student",
    )
    role = Role(name=f"role-{email}", description="test", is_system=True)
    role.permissions = [
        Permission(name=f"{name}", description=name) for name in permissions
    ]
    db.add_all([user, role])
    await db.flush()
    db.add(UserRoleAssignment(user_id=user.id, role_id=role.id))
    await db.commit()
    return await _login(client, email, "staffpass1")


async def _seed_audit(db: AsyncSession) -> None:
    db.add_all(
        [
            AuditLog(
                action="refund.create",
                object_type="refund_request",
                object_id="r1",
                reason="Клиентка anna.k@example.com просит вернуть, тел. +7 (999) 123-45-67",
                new_value={"purchase_id": "8d0e1f2a-3b4c-4d5e-8f90-123456789abc", "amount_kopecks": 500000},
                correlation_id="c1",
            ),
            AuditLog(
                action="refund.status.update",
                object_type="refund_request",
                object_id="r1",
                reason="Возврат подтверждён в кабинете",
                old_value={"status": "submitted", "note": None},
                new_value={"status": "processed", "provider_reference": "P-1", "note": "Позвонила 89991234567"},
                correlation_id="c2",
            ),
            AuditLog(
                action="student.note.create",
                object_type="student_note",
                object_id="n1",
                reason="Записала: ученица болеет",
                new_value={"user_id": "11111111-2222-3333-4444-555555555555"},
                correlation_id="c3",
            ),
            AuditLog(
                action="entitlement.grant",
                object_type="entitlement",
                object_id="e1",
                reason="Подарок для maria@example.com",
                new_value={"user_email": "maria@example.com", "expires_at": "2026-12-25T10:00:00"},
                correlation_id="c4",
            ),
        ]
    )
    await db.commit()


@pytest.mark.asyncio
async def test_audit_reader_without_pii_read_sees_masked_records(
    client: AsyncClient, db: AsyncSession
):
    headers = await _staff(client, db, "audit-analyst@example.com", ["audit.read"])
    await _seed_audit(db)

    response = await client.get("/api/admin/audit-logs", headers=headers)
    assert response.status_code == 200, response.text
    by_action = {item["action"]: item for item in response.json()}

    refund = by_action["refund.create"]
    assert refund["reason"] == REDACTED_FREE_TEXT
    assert refund["new_value"]["purchase_id"] == "8d0e1f2a-3b4c-4d5e-8f90-123456789abc"
    assert refund["new_value"]["amount_kopecks"] == 500000

    status_update = by_action["refund.status.update"]
    assert status_update["reason"] == REDACTED_FREE_TEXT
    assert status_update["new_value"]["note"] == REDACTED_FREE_TEXT
    assert status_update["new_value"]["status"] == "processed"
    assert status_update["old_value"]["note"] is None

    note = by_action["student.note.create"]
    assert note["reason"] == REDACTED_FREE_TEXT
    assert note["new_value"]["user_id"] == "11111111-2222-3333-4444-555555555555"

    grant = by_action["entitlement.grant"]
    assert grant["reason"] == "Подарок для m***@example.com"
    assert grant["new_value"]["user_email"] == "m***@example.com"
    assert grant["new_value"]["expires_at"] == "2026-12-25T10:00:00"
    assert "maria@example.com" not in response.text
    assert "anna.k@example.com" not in response.text
    assert "123-45-67" not in response.text


@pytest.mark.asyncio
async def test_audit_reader_with_pii_read_sees_full_records(
    client: AsyncClient, db: AsyncSession
):
    headers = await _staff(client, db, "audit-owner@example.com", ["audit.read", "pii.read"])
    await _seed_audit(db)

    response = await client.get("/api/admin/audit-logs", headers=headers)
    assert response.status_code == 200, response.text
    by_action = {item["action"]: item for item in response.json()}
    assert "anna.k@example.com" in by_action["refund.create"]["reason"]
    assert by_action["refund.status.update"]["new_value"]["note"] == "Позвонила 89991234567"
    assert by_action["entitlement.grant"]["new_value"]["user_email"] == "maria@example.com"


def test_mask_personal_data_leaves_identifiers_and_numbers_alone():
    assert mask_personal_data("+7 999 123-45-67") == "***4567"
    assert mask_personal_data("call 8(999)1234567 now") == "call ***4567 now"
    assert mask_personal_data("12345678-1234-1234-1234-123456789012") == (
        "12345678-1234-1234-1234-123456789012"
    )
    assert mask_personal_data("2026-11-25T10:00:00") == "2026-11-25T10:00:00"
    assert mask_personal_data("Order 500000") == "Order 500000"
    assert mask_personal_data({"a": ["x@y.ru", 5]}) == {"a": ["x***@y.ru", 5]}
