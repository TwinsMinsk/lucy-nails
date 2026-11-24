"""Expiring counter and access list use the effective access end (audit I6)."""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.course import Course
from app.models.entitlement import Entitlement
from app.models.user import User


async def _admin_headers(client: AsyncClient, db: AsyncSession) -> dict[str, str]:
    admin = User(
        email_verified_at=datetime.utcnow(),
        email="access-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    db.add(admin)
    await db.commit()
    response = await client.post(
        "/api/auth/login", json={"email": admin.email, "password": "adminpass1"}
    )
    client.cookies.clear()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _entitlement(user: User, course: Course, expires_at: datetime, status: str = "active") -> Entitlement:
    return Entitlement(
        user_id=user.id,
        course_id=course.id,
        source="purchase",
        tariff="self",
        status=status,
        starts_at=expires_at - timedelta(days=30),
        expires_at=expires_at,
    )


@pytest.mark.asyncio
async def test_expiring_counter_uses_latest_access_per_student_and_course(
    client: AsyncClient, db: AsyncSession
):
    headers = await _admin_headers(client, db)
    now = datetime.utcnow()
    course = Course(title="Expiring Course", price_self=5000, price_support=10000)
    renewed = User(email="renewed@example.com", password_hash="unused", role="student")
    ending = User(email="ending@example.com", password_hash="unused", role="student")
    db.add_all([course, renewed, ending])
    await db.flush()
    db.add_all(
        [
            # Early renewal: the old row ends tomorrow, the new one in a month.
            _entitlement(renewed, course, now + timedelta(days=1)),
            _entitlement(renewed, course, now + timedelta(days=31)),
            # A genuinely ending access, split over two rows that both end this week.
            _entitlement(ending, course, now + timedelta(days=2)),
            _entitlement(ending, course, now + timedelta(days=5)),
        ]
    )
    await db.commit()

    dashboard = await client.get("/api/admin/dashboard", headers=headers)

    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["expiring_entitlements_7d"] == 1


@pytest.mark.asyncio
async def test_access_list_shows_run_out_rows_as_expired(
    client: AsyncClient, db: AsyncSession
):
    headers = await _admin_headers(client, db)
    now = datetime.utcnow()
    course = Course(title="Access List Course", price_self=5000, price_support=10000)
    student = User(email="list-student@example.com", password_hash="unused", role="student")
    db.add_all([course, student])
    await db.flush()
    past = _entitlement(student, course, now - timedelta(hours=1))
    current = _entitlement(student, course, now + timedelta(days=10))
    revoked = _entitlement(student, course, now + timedelta(days=5), status="revoked")
    db.add_all([past, current, revoked])
    await db.commit()

    listed = await client.get("/api/admin/entitlements", headers=headers)
    assert listed.status_code == 200, listed.text
    statuses = {item["id"]: item["status"] for item in listed.json()["items"]}
    assert statuses == {
        str(past.id): "expired",
        str(current.id): "active",
        str(revoked.id): "revoked",
    }

    active = await client.get("/api/admin/entitlements?status=active", headers=headers)
    assert [item["id"] for item in active.json()["items"]] == [str(current.id)]
    expired = await client.get("/api/admin/entitlements?status=expired", headers=headers)
    assert [item["id"] for item in expired.json()["items"]] == [str(past.id)]
    assert expired.json()["total"] == 1
