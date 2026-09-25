from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password_reset_token
from app.models.audit_log import AuditLog
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


async def _staff_headers(
    client: AsyncClient,
    db: AsyncSession,
    *,
    email: str,
    role_name: str,
    permissions: list[str],
) -> dict[str, str]:
    staff = User(
        email=email,
        password_hash=get_password_hash("staffpass1"),
        role="student",
    )
    role = Role(name=role_name, description=role_name, is_system=True)
    role.permissions = [Permission(name=name, description=name) for name in permissions]
    db.add_all([staff, role])
    await db.flush()
    db.add(UserRoleAssignment(user_id=staff.id, role_id=role.id))
    await db.commit()
    response = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "staffpass1"},
    )
    assert response.status_code == 200, response.text
    client.cookies.clear()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_admin_creates_student_with_access_and_activation_email(
    client: AsyncClient, db: AsyncSession
):
    headers = await _admin_headers(client, db)
    admin_id = await db.scalar(select(User.id).where(User.email == "crm-admin@example.com"))
    course = Course(title="Manual Sale Course", price_self=5000, price_support=10000)
    db.add(course)
    await db.commit()

    response = await client.post(
        "/api/admin/students",
        json={
            "email": "  New.Student@Example.com ",
            "full_name": "Новая Ученица",
            "phone": "+7 999 000-11-22",
            "course_id": str(course.id),
            "access_days": 45,
            "reason": "Bank transfer payment",
        },
        headers={**headers, "X-Correlation-ID": "create-student"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user_created"] is True
    student = await db.scalar(select(User).where(User.id == UUID(body["user_id"])))
    assert student.email == "new.student@example.com"
    assert student.role == "student"
    assert student.full_name == "Новая Ученица"
    assert student.phone == "+7 999 000-11-22"
    entitlement = await db.scalar(
        select(Entitlement).where(Entitlement.id == UUID(body["entitlement_id"]))
    )
    assert entitlement.user_id == student.id
    assert entitlement.course_id == course.id
    assert entitlement.source == "manual"
    assert entitlement.status == "active"
    assert entitlement.granted_by_id == admin_id
    remaining = entitlement.expires_at - datetime.utcnow()
    assert timedelta(days=44) < remaining <= timedelta(days=45)
    message = await db.scalar(select(OutboxMessage))
    assert message.kind == "account_activation"
    assert message.recipient == "new.student@example.com"
    assert "/auth/activate?token=" in message.payload["activation_url"]
    assert message.payload["course_title"] == "Manual Sale Course"
    audit_actions = set(
        (
            await db.execute(
                select(AuditLog.action).where(
                    AuditLog.actor_user_id == admin_id,
                    AuditLog.correlation_id == "create-student",
                )
            )
        ).scalars().all()
    )
    assert audit_actions == {"student.create", "entitlement.grant"}


@pytest.mark.asyncio
async def test_admin_create_student_reuses_existing_user_case_insensitively(
    client: AsyncClient, db: AsyncSession
):
    headers = await _admin_headers(client, db)
    course = Course(title="Gift Course", price_self=5000, price_support=10000)
    existing = User(
        email="existing.student@example.com",
        password_hash=get_password_hash("studentpass1"),
        role="student",
    )
    db.add_all([course, existing])
    await db.commit()

    missing_course = await client.post(
        "/api/admin/students",
        json={
            "email": "existing.student@example.com",
            "course_id": str(uuid4()),
            "reason": "Gift from the author",
        },
        headers=headers,
    )
    assert missing_course.status_code == 404

    response = await client.post(
        "/api/admin/students",
        json={
            "email": "Existing.Student@EXAMPLE.com",
            "course_id": str(course.id),
            "reason": "Gift from the author",
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["user_created"] is False
    assert response.json()["user_id"] == str(existing.id)
    users = await db.scalar(
        select(func.count(User.id)).where(
            func.lower(User.email) == "existing.student@example.com"
        )
    )
    assert users == 1
    messages = (await db.execute(select(OutboxMessage))).scalars().all()
    assert [message.kind for message in messages] == ["access_granted"]
    assert messages[0].recipient == "existing.student@example.com"
    assert messages[0].payload["login_url"].endswith("/auth/login")


@pytest.mark.asyncio
async def test_student_creation_and_login_link_require_permissions(
    client: AsyncClient, db: AsyncSession
):
    course = Course(title="RBAC Student Course", price_self=5000, price_support=10000)
    db.add(course)
    await db.commit()
    payload = {
        "email": "rbac-student@example.com",
        "course_id": str(course.id),
        "reason": "Manual sale by support",
    }

    reader_headers = await _staff_headers(
        client, db, email="reader@example.com", role_name="reader", permissions=["users.read"]
    )
    denied = await client.post("/api/admin/students", json=payload, headers=reader_headers)
    assert denied.status_code == 403

    access_headers = await _staff_headers(
        client,
        db,
        email="access-manager@example.com",
        role_name="access_manager",
        permissions=["access.manage"],
    )
    created = await client.post("/api/admin/students", json=payload, headers=access_headers)
    assert created.status_code == 201, created.text
    login_link = await client.post(
        f"/api/admin/students/{created.json()['user_id']}/send-login-link",
        headers=access_headers,
    )
    assert login_link.status_code == 403


@pytest.mark.asyncio
async def test_send_login_link_enqueues_a_message_every_time(
    client: AsyncClient, db: AsyncSession
):
    headers = await _admin_headers(client, db)
    student = User(
        email="locked-out@example.com",
        password_hash=get_password_hash("studentpass1"),
        role="student",
    )
    db.add(student)
    await db.commit()

    unknown = await client.post(
        f"/api/admin/students/{uuid4()}/send-login-link", headers=headers
    )
    assert unknown.status_code == 404
    first = await client.post(
        f"/api/admin/students/{student.id}/send-login-link", headers=headers
    )
    second = await client.post(
        f"/api/admin/students/{student.id}/send-login-link", headers=headers
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    messages = (
        await db.execute(select(OutboxMessage).where(OutboxMessage.kind == "login_link"))
    ).scalars().all()
    assert len(messages) == 2
    assert len({message.dedupe_key for message in messages}) == 2
    for message in messages:
        assert message.recipient == "locked-out@example.com"
        url = message.payload["login_url"]
        assert "/auth/reset-password?token=" in url
        token_payload = verify_password_reset_token(url.split("token=", 1)[1])
        assert token_payload["sub"] == str(student.id)
    audits = await db.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.action == "student.login_link.send",
            AuditLog.object_id == str(student.id),
        )
    )
    assert audits == 2
