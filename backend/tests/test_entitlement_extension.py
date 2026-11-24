"""Admin access extension: base and idempotency (task item 21, audit I13)."""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.entitlement import Entitlement
from app.models.user import User
from conftest import TestingSessionLocal


async def _setup(client: AsyncClient, db: AsyncSession):
    admin = User(
        email_verified_at=datetime.utcnow(),
        email="extend-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    student = User(
        email_verified_at=datetime.utcnow(),
        email="extend-student@example.com",
        password_hash="unused",
        role="student",
    )
    course = Course(title="Extend Course", price_self=5000, price_support=10000)
    db.add_all([admin, student, course])
    await db.flush()
    now = datetime.utcnow()
    old = Entitlement(
        user_id=student.id,
        course_id=course.id,
        source="purchase",
        tariff="self",
        status="active",
        starts_at=now - timedelta(days=28),
        expires_at=now + timedelta(days=2),
    )
    renewed = Entitlement(
        user_id=student.id,
        course_id=course.id,
        source="purchase",
        tariff="self",
        status="active",
        starts_at=now,
        expires_at=now + timedelta(days=32),
    )
    db.add_all([old, renewed])
    await db.commit()
    login = await client.post(
        "/api/auth/login", json={"email": admin.email, "password": "adminpass1"}
    )
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    return headers, old, renewed


@pytest.mark.asyncio
async def test_extending_an_older_row_moves_the_students_access_end(
    client: AsyncClient, db: AsyncSession
):
    headers, old, renewed = await _setup(client, db)
    renewed_end = renewed.expires_at

    response = await client.post(
        f"/api/admin/entitlements/{old.id}/extend",
        json={"days": 10, "reason": "Goodwill extension"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    async with TestingSessionLocal() as fresh:
        extended = await fresh.get(Entitlement, old.id)
        assert extended.expires_at == renewed_end + timedelta(days=10)
        audit = (
            await fresh.execute(select(AuditLog).where(AuditLog.action == "entitlement.extend"))
        ).scalar_one()
    assert response.json()["expires_at"] == extended.expires_at.isoformat()
    assert audit.new_value["expires_at"] == extended.expires_at.isoformat()


@pytest.mark.asyncio
async def test_extending_the_latest_row_adds_days_to_its_own_end(
    client: AsyncClient, db: AsyncSession
):
    headers, _, renewed = await _setup(client, db)
    renewed_end = renewed.expires_at

    response = await client.post(
        f"/api/admin/entitlements/{renewed.id}/extend",
        json={"days": 5, "reason": "Goodwill extension"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    async with TestingSessionLocal() as fresh:
        assert (await fresh.get(Entitlement, renewed.id)).expires_at == renewed_end + timedelta(days=5)
