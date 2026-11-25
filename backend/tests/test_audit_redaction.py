"""Audit log reader view without pii.read (audit B6, review 1)."""

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.audit_log import AuditLog
from app.models.rbac import Permission, Role, UserRoleAssignment
from app.models.user import User
from app.services.audit_service import REDACTED_FREE_TEXT


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


SERVER_CORRELATION = "3f2b1c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d"


async def _seed_audit(db: AsyncSession) -> None:
    db.add_all(
        [
            AuditLog(
                action="refund.create",
                object_type="refund_request",
                object_id="8d0e1f2a-3b4c-4d5e-8f90-123456789abc",
                reason="Клиентка anna.k@example.com просит вернуть, тел. +7 (999) 123-45-67",
                new_value={"purchase_id": "8d0e1f2a-3b4c-4d5e-8f90-123456789abc", "amount_kopecks": 500000, "status": "requested"},
                correlation_id=SERVER_CORRELATION,
            ),
            AuditLog(
                action="refund.status.update",
                object_type="refund_request",
                object_id="8d0e1f2a-3b4c-4d5e-8f90-123456789abc",
                reason="Возврат подтверждён в кабинете",
                old_value={"status": "submitted", "note": None},
                new_value={"status": "processed", "provider_reference": "P-1", "note": "Позвонила 89991234567"},
                correlation_id="89991234567",
            ),
            AuditLog(
                action="entitlement.suspend",
                object_type="entitlement",
                object_id="11111111-2222-3333-4444-555555555555",
                reason="Иванова Мария Петровна, больничный до конца месяца",
                old_value={"status": "active", "expires_at": "2026-12-25T10:00:00"},
                new_value={"status": "suspended", "expires_at": "2026-12-25T10:00:00"},
                correlation_id="crm-suspend",
            ),
            AuditLog(
                action="entitlement.grant",
                object_type="entitlement",
                object_id="11111111-2222-3333-4444-555555555556",
                reason="Подарок для мария@пример.рф",
                new_value={"user_email": "мария@пример.рф", "access_days": 30, "tariff": "self", "expires_at": "2026-12-25T10:00:00.123456"},
                correlation_id=SERVER_CORRELATION,
            ),
            AuditLog(
                action="student.tags.update",
                object_type="user",
                object_id="11111111-2222-3333-4444-555555555557",
                reason="Сегментация",
                old_value={"tags": ["vip"]},
                new_value={"tags": ["болеет", "vip"]},
                correlation_id=SERVER_CORRELATION,
            ),
        ]
    )
    await db.commit()


@pytest.mark.asyncio
async def test_audit_reader_without_pii_read_sees_only_structured_fields(
    client: AsyncClient, db: AsyncSession
):
    headers = await _staff(client, db, "audit-analyst@example.com", ["audit.read"])
    await _seed_audit(db)

    response = await client.get("/api/admin/audit-logs", headers=headers)
    assert response.status_code == 200, response.text
    by_action = {item["action"]: item for item in response.json()}

    # Free-text suspension reason with a full name and a medical detail.
    suspend = by_action["entitlement.suspend"]
    assert suspend["reason"] == REDACTED_FREE_TEXT
    assert suspend["new_value"] == {"status": "suspended", "expires_at": "2026-12-25T10:00:00"}
    assert suspend["object_id"] == "11111111-2222-3333-4444-555555555555"

    # A Cyrillic-domain email in the reason and in a value.
    grant = by_action["entitlement.grant"]
    assert grant["reason"] == REDACTED_FREE_TEXT
    assert grant["new_value"]["user_email"] == REDACTED_FREE_TEXT
    assert grant["new_value"]["access_days"] == 30
    assert grant["new_value"]["tariff"] == "self"
    assert grant["new_value"]["expires_at"] == "2026-12-25T10:00:00.123456"

    refund = by_action["refund.create"]
    assert refund["reason"] == REDACTED_FREE_TEXT
    assert refund["new_value"]["amount_kopecks"] == 500000
    assert refund["new_value"]["purchase_id"] == "8d0e1f2a-3b4c-4d5e-8f90-123456789abc"

    status_update = by_action["refund.status.update"]
    assert status_update["new_value"]["note"] == REDACTED_FREE_TEXT
    assert status_update["new_value"]["provider_reference"] == REDACTED_FREE_TEXT
    assert status_update["new_value"]["status"] == "processed"
    # A digits-only client correlation id is not shown; a server one is.
    assert status_update["correlation_id"] == REDACTED_FREE_TEXT
    assert suspend["correlation_id"] == REDACTED_FREE_TEXT
    assert refund["correlation_id"] == SERVER_CORRELATION

    tags = by_action["student.tags.update"]
    assert tags["new_value"]["tags"] == REDACTED_FREE_TEXT

    for secret in ("мария@пример.рф", "Иванова", "больничный", "89991234567", "anna.k@example.com", "болеет", "123-45-67"):
        assert secret not in response.text


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
    assert by_action["entitlement.suspend"]["reason"].startswith("Иванова")
    assert by_action["entitlement.grant"]["new_value"]["user_email"] == "мария@пример.рф"
    assert by_action["refund.status.update"]["correlation_id"] == "89991234567"

@pytest.mark.asyncio
async def test_content_and_pricing_audit_keeps_scalars_and_hides_titles(
    client: AsyncClient, db: AsyncSession
):
    headers = await _staff(client, db, "audit-content@example.com", ["audit.read"])
    item_id = "21111111-2222-3333-4444-555555555555"
    db.add_all(
        [
            AuditLog(
                action="course.update",
                object_type="course",
                object_id="31111111-2222-3333-4444-555555555555",
                old_value={"price_self": 5900, "title": "Курс Марии Ивановой", "is_published": False},
                new_value={
                    "changed_fields": ["is_published", "price_self", "title"],
                    "price_self": 6900,
                    "access_days": 45,
                    "title": "Курс Марии Ивановой 2.0",
                    "is_published": True,
                },
                correlation_id=SERVER_CORRELATION,
            ),
            AuditLog(
                action="lesson.create",
                object_type="lesson",
                object_id="41111111-2222-3333-4444-555555555555",
                new_value={"module_id": "51111111-2222-3333-4444-555555555555", "title": "Урок для Анны", "is_preview": True, "order_index": 3, "duration_seconds": 600},
                correlation_id=SERVER_CORRELATION,
            ),
            AuditLog(
                action="gallery_item.reorder",
                object_type="gallery_item",
                object_id=None,
                old_value={"order_index": {item_id: 1}},
                new_value={"order_index": {item_id: 2}},
                correlation_id=SERVER_CORRELATION,
            ),
        ]
    )
    await db.commit()

    response = await client.get("/api/admin/audit-logs", headers=headers)
    assert response.status_code == 200, response.text
    by_action = {item["action"]: item for item in response.json()}
    course = by_action["course.update"]
    assert course["new_value"] == {
        "changed_fields": ["is_published", "price_self", "title"],
        "price_self": 6900,
        "access_days": 45,
        "title": REDACTED_FREE_TEXT,
        "is_published": True,
    }
    assert course["old_value"]["price_self"] == 5900
    assert course["old_value"]["title"] == REDACTED_FREE_TEXT
    lesson = by_action["lesson.create"]["new_value"]
    assert lesson["title"] == REDACTED_FREE_TEXT
    assert (lesson["is_preview"], lesson["order_index"], lesson["duration_seconds"]) == (True, 3, 600)
    assert by_action["gallery_item.reorder"]["new_value"] == {"order_index": {item_id: 2}}
    for secret in ("Ивановой", "Анны"):
        assert secret not in response.text