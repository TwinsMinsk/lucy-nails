"""/admin/grant-access queues the same email as /admin/students (review 1, item 6)."""

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_account_activation_token
from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.outbox import OutboxMessage
from app.models.user import User
from conftest import mfa_login


async def _grant(client: AsyncClient, db: AsyncSession, *, verified: bool):
    admin = User(
        email_verified_at=datetime.utcnow(),
        email="grant-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    student = User(
        email="grant-student@example.com",
        email_verified_at=datetime.utcnow() if verified else None,
        password_hash="unused",
        role="student",
    )
    course = Course(title="Grant Course", price_self=5000, price_support=10000, access_days=30)
    db.add_all([admin, student, course])
    await db.commit()
    login = await mfa_login(client, db, admin.email, "adminpass1")
    client.cookies.clear()
    response = await client.post(
        "/api/admin/grant-access",
        json={
            "user_id": str(student.id),
            "course_id": str(course.id),
            "tariff": "self",
            "reason": "Gift from the student card",
        },
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert response.status_code == 200, response.text
    messages = (await db.execute(select(OutboxMessage))).scalars().all()
    audit = (
        await db.execute(select(AuditLog).where(AuditLog.action == "entitlement.grant"))
    ).scalar_one()
    return response.json()["entitlement_id"], messages, audit


@pytest.mark.asyncio
async def test_grant_access_to_unverified_account_queues_activation(
    client: AsyncClient, db: AsyncSession
):
    entitlement_id, messages, audit = await _grant(client, db, verified=False)

    assert [message.kind for message in messages] == ["account_activation"]
    assert messages[0].recipient == "grant-student@example.com"
    assert messages[0].dedupe_key == f"admin-student:{entitlement_id}:activation"
    token = messages[0].payload["activation_url"].split("token=", 1)[1]
    assert verify_account_activation_token(token) is not None
    assert audit.new_value["notification"] == "account_activation"


@pytest.mark.asyncio
async def test_grant_access_to_verified_account_queues_access_email(
    client: AsyncClient, db: AsyncSession
):
    entitlement_id, messages, audit = await _grant(client, db, verified=True)

    assert [message.kind for message in messages] == ["access_granted"]
    assert messages[0].dedupe_key == f"admin-student:{entitlement_id}:access"
    assert messages[0].payload["login_url"].endswith("/auth/login")
    assert audit.new_value["notification"] == "access_granted"
