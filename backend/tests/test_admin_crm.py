from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.course import Course
from app.models.entitlement import Entitlement
from app.models.order import Order
from app.models.outbox import OutboxMessage
from app.models.user import User


async def _admin_headers(client: AsyncClient, db: AsyncSession) -> dict[str, str]:
    admin = User(
        email="crm-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    db.add(admin)
    await db.commit()
    response = await client.post(
        "/api/auth/login",
        json={"email": admin.email, "password": "adminpass1"},
    )
    assert response.status_code == 200, response.text
    client.cookies.clear()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_dashboard_and_paginated_student_search(
    client: AsyncClient, db: AsyncSession
):
    headers = await _admin_headers(client, db)
    course = Course(title="CRM Course", price_self=5000, price_support=10000)
    anna = User(
        email="anna.student@example.com",
        full_name="Anna Student",
        password_hash=get_password_hash("studentpass1"),
        role="student",
    )
    boris = User(
        email="boris@example.com",
        password_hash=get_password_hash("studentpass1"),
        role="student",
    )
    db.add_all([course, anna, boris])
    await db.flush()
    db.add(
        Entitlement(
            user_id=anna.id,
            course_id=course.id,
            source="manual",
            tariff="self",
            status="active",
            starts_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
            reason="CRM test",
        )
    )
    await db.commit()

    dashboard = await client.get("/api/admin/dashboard", headers=headers)
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["active_entitlements"] == 1
    assert dashboard.json()["total_students"] == 2
    system_status = await client.get("/api/admin/system/status", headers=headers)
    assert system_status.status_code == 200, system_status.text
    assert isinstance(system_status.json()["checkout_enabled"], bool)
    assert "prodamus" in system_status.json()["integrations"]

    entitlements = await client.get(
        "/api/admin/entitlements?status=active&search=anna",
        headers=headers,
    )
    assert entitlements.status_code == 200, entitlements.text
    assert entitlements.json()["total"] == 1
    assert entitlements.json()["items"][0]["user_email"] == anna.email

    students = await client.get(
        "/api/admin/students?search=anna&limit=1&offset=0",
        headers=headers,
    )
    assert students.status_code == 200, students.text
    assert students.json()["total"] == 1
    assert students.json()["items"][0]["email"] == anna.email
    assert students.json()["items"][0]["active_entitlements"] == 1

    detail = await client.get(f"/api/admin/students/{anna.id}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["entitlements"][0]["course_title"] == "CRM Course"

    note = await client.post(
        f"/api/admin/students/{anna.id}/notes",
        json={"body": "Student asked to extend access after vacation"},
        headers=headers,
    )
    assert note.status_code == 201, note.text
    tagged = await client.put(
        f"/api/admin/students/{anna.id}/tags",
        json={"tags": ["vip", "needs-follow-up"], "reason": "CRM segmentation"},
        headers=headers,
    )
    assert tagged.status_code == 200, tagged.text

    updated_detail = await client.get(f"/api/admin/students/{anna.id}", headers=headers)
    assert updated_detail.json()["notes"][0]["body"].startswith("Student asked")
    assert updated_detail.json()["tags"] == ["needs-follow-up", "vip"]


@pytest.mark.asyncio
async def test_orders_are_snapshot_based_and_paginated(
    client: AsyncClient, db: AsyncSession
):
    headers = await _admin_headers(client, db)
    course = Course(title="Order Course", price_self=9000, price_support=15000)
    db.add(course)
    await db.flush()
    order = Order(
        course_id=course.id,
        tariff="self",
        customer_email="buyer@example.com",
        amount_kopecks=777700,
        currency="RUB",
        access_days=30,
        status="pending",
        status_token_hash="order-status-hash",
    )
    db.add(order)
    await db.commit()

    response = await client.get(
        "/api/admin/orders?status=pending&search=buyer",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["amount_kopecks"] == 777700
    assert response.json()["items"][0]["course_title"] == "Order Course"


@pytest.mark.asyncio
async def test_dead_letter_can_be_retried_with_reason(
    client: AsyncClient, db: AsyncSession
):
    headers = await _admin_headers(client, db)
    message = OutboxMessage(
        kind="access_granted",
        channel="email",
        recipient="student@example.com",
        payload={"subject": "Access"},
        status="dead_letter",
        attempts=5,
        max_attempts=5,
        next_attempt_at=datetime.utcnow(),
        last_error="Provider unavailable",
        dedupe_key="crm-retry-test",
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    retried = await client.post(
        f"/api/admin/notifications/{message.id}/retry",
        json={"reason": "Provider recovered; manual retry"},
        headers={**headers, "X-Correlation-ID": "crm-retry"},
    )
    assert retried.status_code == 200, retried.text
    assert retried.json()["status"] == "pending"
    assert retried.json()["attempts"] == 0

    listed = await client.get(
        "/api/admin/notifications?status=pending",
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
