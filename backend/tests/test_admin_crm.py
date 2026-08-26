from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.course import Course
from app.models.entitlement import Entitlement
from app.models.order import Order
from app.models.outbox import OutboxMessage
from app.models.payment_event import PaymentEvent
from app.models.purchase import Purchase
from app.models.refund import RefundRequest
from app.models.rbac import Permission, Role, UserRoleAssignment
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
        course_title=course.title,
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
async def test_reconciliation_counts_real_webhook_and_missing_access_issues_only(
    client: AsyncClient,
    db: AsyncSession,
):
    headers = await _admin_headers(client, db)
    course = Course(title="Reconciliation Course", price_self=5000, price_support=10000)
    student = User(
        email="reconciliation-student@example.com",
        password_hash=get_password_hash("studentpass1"),
        role="student",
    )
    db.add_all([course, student])
    await db.flush()
    now = datetime.utcnow()

    current_missing = Purchase(
        user_id=student.id,
        course_id=course.id,
        tariff="self",
        amount_kopecks=500000,
        payment_id="reconciliation-missing",
        payment_status="success",
        paid_at=now,
        expires_at=now + timedelta(days=30),
    )
    naturally_expired = Purchase(
        user_id=student.id,
        course_id=course.id,
        tariff="self",
        amount_kopecks=500000,
        payment_id="reconciliation-expired",
        payment_status="success",
        paid_at=now - timedelta(days=60),
        expires_at=now - timedelta(days=30),
    )
    intentionally_revoked = Purchase(
        user_id=student.id,
        course_id=course.id,
        tariff="support",
        amount_kopecks=1000000,
        payment_id="reconciliation-revoked",
        payment_status="success",
        paid_at=now,
        expires_at=now + timedelta(days=30),
    )
    fully_refunded = Purchase(
        user_id=student.id,
        course_id=course.id,
        tariff="self",
        amount_kopecks=500000,
        payment_id="reconciliation-refunded",
        payment_status="success",
        paid_at=now,
        expires_at=now + timedelta(days=30),
    )
    db.add_all(
        [current_missing, naturally_expired, intentionally_revoked, fully_refunded]
    )
    await db.flush()
    db.add_all(
        [
            Entitlement(
                user_id=student.id,
                course_id=course.id,
                source_purchase_id=intentionally_revoked.id,
                source="purchase",
                tariff="support",
                status="revoked",
                starts_at=now,
                expires_at=intentionally_revoked.expires_at,
                reason="Confirmed refund",
                revoked_at=now,
            ),
            PaymentEvent(
                event_hash="reconciliation-rejected-event",
                event_type="success",
                processing_status="rejected",
                error_code="amount_mismatch",
                sanitized_payload={},
                received_at=now,
                processed_at=now,
            ),
            RefundRequest(
                purchase_id=fully_refunded.id,
                amount_kopecks=fully_refunded.amount_kopecks,
                reason="Full provider refund",
                status="processed",
                created_by_id=student.id,
                processed_by_id=student.id,
                processed_at=now,
            ),
        ]
    )
    await db.commit()

    dashboard = await client.get("/api/admin/dashboard", headers=headers)
    reconciliation = await client.get("/api/admin/reconciliation", headers=headers)

    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["payment_errors"] == 1
    assert reconciliation.status_code == 200, reconciliation.text
    assert reconciliation.json()["processed_payment_errors"] == 1
    assert reconciliation.json()["successful_purchases_without_active_entitlement"] == 1


@pytest.mark.asyncio
async def test_analyst_order_access_masks_personal_data(
    client: AsyncClient,
    db: AsyncSession,
):
    analyst = User(
        email="masked-analyst@example.com",
        password_hash=get_password_hash("analystpass1"),
        role="student",
    )
    role = Role(name="analyst", description="Analyst", is_system=True)
    role.permissions = [
        Permission(name="commerce.read", description="Read commerce")
    ]
    buyer = User(
        email="private.buyer@example.com",
        password_hash=get_password_hash("buyerpass1"),
        role="student",
    )
    course = Course(title="Masked Order Course", price_self=9000, price_support=15000)
    db.add_all([analyst, buyer, role, course])
    await db.flush()
    db.add(UserRoleAssignment(user_id=analyst.id, role_id=role.id))
    db.add(
        Order(
            course_id=course.id,
            course_title=course.title,
            tariff="self",
            customer_email="private.buyer@example.com",
            customer_phone="+7 999 123-45-67",
            amount_kopecks=900000,
            currency="RUB",
            access_days=30,
            status="pending",
            status_token_hash="masked-order-status-hash",
        )
    )
    db.add(
        Purchase(
            user_id=buyer.id,
            course_id=course.id,
            tariff="self",
            amount_kopecks=900000,
            payment_id="masked-legacy-purchase",
            payment_status="success",
            customer_phone="+7 999 123-45-67",
            paid_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
    )
    await db.commit()
    login = await client.post(
        "/api/auth/login",
        json={"email": analyst.email, "password": "analystpass1"},
    )
    client.cookies.clear()

    response = await client.get(
        "/api/admin/orders",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert response.status_code == 200, response.text
    item = response.json()["items"][0]
    assert item["customer_email"] == "p***@example.com"
    assert item["customer_phone"] == "***4567"

    legacy = await client.get(
        "/api/admin/purchases",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert legacy.status_code == 200, legacy.text
    legacy_item = legacy.json()[0]
    assert legacy_item["user_email"] == "p***@example.com"
    assert legacy_item["customer_phone"] == "***4567"


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
