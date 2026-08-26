import asyncio
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import get_password_hash
from app.core.config import settings
from app.models.course import Course
from app.models.entitlement import Entitlement
from app.models.purchase import Purchase
from app.models.outbox import OutboxMessage
from app.models.refund import RefundRequest
from app.models.user import User
from app.models.analytics_event import AnalyticsEvent
from app.models.audit_log import AuditLog
from app.services.access_service import AccessService
from app.services.refund_service import RefundError, RefundService


@pytest.mark.asyncio
async def test_admin_refund_workflow_revokes_access_without_rewriting_purchase(
    client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(settings, "TELEGRAM_SUPPORT_GROUP_ID", -1001234567890)
    admin = User(
        email="refund-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    student = User(
        email="refund-student@example.com",
        password_hash=get_password_hash("studentpass1"),
        role="student",
        telegram_id=123456789,
    )
    course = Course(
        title="Refund Course",
        price_self=5000,
        price_support=10000,
        is_published=True,
    )
    db.add_all([admin, student, course])
    await db.flush()
    paid_at = datetime.utcnow()
    purchase = Purchase(
        user_id=student.id,
        course_id=course.id,
        tariff="support",
        amount_kopecks=500000,
        payment_id="refund-workflow-payment",
        payment_status="success",
        paid_at=paid_at,
        expires_at=paid_at + timedelta(days=30),
    )
    db.add(purchase)
    await db.flush()
    entitlement = Entitlement(
        user_id=student.id,
        course_id=course.id,
        source_purchase_id=purchase.id,
        source="purchase",
        tariff="support",
        status="active",
        starts_at=paid_at,
        expires_at=purchase.expires_at,
    )
    db.add(entitlement)
    await db.commit()

    login = await client.post(
        "/api/auth/login",
        json={"email": admin.email, "password": "adminpass1"},
    )
    token = login.json()["access_token"]
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await client.post(
        "/api/admin/refunds",
        json={
            "purchase_id": str(purchase.id),
            "amount_kopecks": 500000,
            "reason": "Клиент запросил возврат полной суммы",
        },
        headers=headers,
    )
    assert create_response.status_code == 201, create_response.text
    refund_id = create_response.json()["id"]
    refund = await db.get(RefundRequest, refund_id)
    assert refund is not None
    assert refund.status == "requested"
    assert refund.created_by_id == admin.id

    complete_response = await client.put(
        f"/api/admin/refunds/{refund_id}",
        json={
            "status": "processed",
            "provider_reference": "prodamus-refund-123",
            "reason": "Provider cabinet confirms full refund",
            "note": "Возврат подтверждён в кабинете Prodamus",
        },
        headers=headers,
    )
    assert complete_response.status_code == 200, complete_response.text
    assert complete_response.json()["status"] == "processed"

    await db.refresh(purchase)
    await db.refresh(entitlement)
    assert purchase.payment_status == "success"
    assert entitlement.status == "revoked"
    removal = await db.scalar(
        select(OutboxMessage).where(
            OutboxMessage.kind == "telegram_group_remove",
            OutboxMessage.recipient == "123456789",
        )
    )
    assert removal is not None
    assert not await AccessService.has_active_access(db, student.id, course.id)

    student_login = await client.post(
        "/api/auth/login",
        json={"email": student.email, "password": "studentpass1"},
    )
    client.cookies.clear()
    dashboard = await client.get(
        "/api/purchases/my",
        headers={"Authorization": f"Bearer {student_login.json()['access_token']}"},
    )
    assert dashboard.status_code == 200
    assert dashboard.json() == []
    refund_event = await db.scalar(
        select(AnalyticsEvent).where(
            AnalyticsEvent.event_name == "refund_processed",
            AnalyticsEvent.user_id == student.id,
        )
    )
    assert refund_event is not None
    assert refund_event.course_id == course.id
    audit_actions = set(
        (
            await db.execute(
                select(AuditLog.action).where(AuditLog.object_id == refund_id)
            )
        )
        .scalars()
        .all()
    )
    assert audit_actions == {"refund.create", "refund.status.update"}

    list_response = await client.get("/api/admin/refunds", headers=headers)
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [refund_id]


@pytest.mark.asyncio
async def test_refund_cannot_exceed_purchase_amount(client: AsyncClient, db: AsyncSession):
    admin = User(
        email="refund-limit-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    student = User(
        email="refund-limit-student@example.com",
        password_hash=get_password_hash("studentpass1"),
        role="student",
    )
    course = Course(title="Refund Limit", price_self=5000, price_support=10000, is_published=True)
    db.add_all([admin, student, course])
    await db.flush()
    purchase = Purchase(
        user_id=student.id,
        course_id=course.id,
        tariff="self",
        amount_kopecks=500000,
        payment_id="refund-limit-payment",
        payment_status="success",
        paid_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(purchase)
    await db.commit()

    login = await client.post(
        "/api/auth/login", json={"email": admin.email, "password": "adminpass1"}
    )
    token = login.json()["access_token"]
    client.cookies.clear()
    response = await client.post(
        "/api/admin/refunds",
        json={
            "purchase_id": str(purchase.id),
            "amount_kopecks": 500001,
            "reason": "Сумма выше оплаченной для негативного теста",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_partial_refund_keeps_access_until_full_amount_is_processed(
    client: AsyncClient,
    db: AsyncSession,
):
    admin = User(
        email="partial-refund-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    student = User(
        email="partial-refund-student@example.com",
        password_hash=get_password_hash("studentpass1"),
        role="student",
    )
    course = Course(title="Partial Refund", price_self=5000, price_support=10000, is_published=True)
    db.add_all([admin, student, course])
    await db.flush()
    now = datetime.utcnow()
    purchase = Purchase(
        user_id=student.id,
        course_id=course.id,
        tariff="self",
        amount_kopecks=500000,
        payment_id="partial-refund-payment",
        payment_status="success",
        paid_at=now,
        expires_at=now + timedelta(days=30),
    )
    db.add(purchase)
    await db.flush()
    entitlement = Entitlement(
        user_id=student.id,
        course_id=course.id,
        source_purchase_id=purchase.id,
        source="purchase",
        tariff="self",
        status="active",
        starts_at=now,
        expires_at=purchase.expires_at,
    )
    db.add(entitlement)
    await db.commit()

    login = await client.post(
        "/api/auth/login",
        json={"email": admin.email, "password": "adminpass1"},
    )
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    created = await client.post(
        "/api/admin/refunds",
        json={
            "purchase_id": str(purchase.id),
            "amount_kopecks": 100000,
            "reason": "Partial goodwill refund",
        },
        headers=headers,
    )
    processed = await client.put(
        f"/api/admin/refunds/{created.json()['id']}",
        json={
            "status": "processed",
            "provider_reference": "partial-1000",
            "reason": "Provider cabinet confirms partial refund",
        },
        headers=headers,
    )
    assert processed.status_code == 200, processed.text
    await db.refresh(entitlement)
    assert entitlement.status == "active"
    assert await AccessService.has_active_access(db, student.id, course.id)


@pytest.mark.asyncio
async def test_concurrent_refund_allocation_cannot_exceed_purchase(
    db: AsyncSession,
):
    admin = User(
        email="concurrent-refund-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    student = User(
        email="concurrent-refund-student@example.com",
        password_hash=get_password_hash("studentpass1"),
        role="student",
    )
    course = Course(title="Concurrent Refund", price_self=5000, price_support=10000, is_published=True)
    db.add_all([admin, student, course])
    await db.flush()
    purchase = Purchase(
        user_id=student.id,
        course_id=course.id,
        tariff="self",
        amount_kopecks=500000,
        payment_id="concurrent-refund-payment",
        payment_status="success",
        paid_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(purchase)
    await db.commit()

    sessions = async_sessionmaker(bind=db.bind, class_=AsyncSession, expire_on_commit=False)

    async def allocate(amount: int) -> str:
        async with sessions() as worker_db:
            try:
                await RefundService.create_refund(
                    worker_db,
                    purchase_id=purchase.id,
                    amount_kopecks=amount,
                    reason="Concurrent allocation test",
                    created_by_id=admin.id,
                )
                await worker_db.commit()
                return "created"
            except RefundError:
                await worker_db.rollback()
                return "rejected"

    results = await asyncio.gather(allocate(300000), allocate(300000))

    assert sorted(results) == ["created", "rejected"]


@pytest.mark.asyncio
async def test_concurrent_terminal_refund_updates_cannot_overwrite_processed_state(
    db: AsyncSession,
):
    admin = User(
        email="refund-transition-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    student = User(
        email="refund-transition-student@example.com",
        password_hash=get_password_hash("studentpass1"),
        role="student",
    )
    course = Course(
        title="Refund Transition",
        price_self=5000,
        price_support=10000,
        is_published=True,
    )
    db.add_all([admin, student, course])
    await db.flush()
    now = datetime.utcnow()
    purchase = Purchase(
        user_id=student.id,
        course_id=course.id,
        tariff="self",
        amount_kopecks=500000,
        payment_id="refund-transition-payment",
        payment_status="success",
        paid_at=now,
        expires_at=now + timedelta(days=30),
    )
    db.add(purchase)
    await db.flush()
    entitlement = Entitlement(
        user_id=student.id,
        course_id=course.id,
        source_purchase_id=purchase.id,
        source="purchase",
        tariff="self",
        status="active",
        starts_at=now,
        expires_at=purchase.expires_at,
    )
    refund = RefundRequest(
        purchase_id=purchase.id,
        amount_kopecks=500000,
        reason="Concurrent terminal transition",
        status="requested",
        created_by_id=admin.id,
    )
    db.add_all([entitlement, refund])
    await db.commit()

    sessions = async_sessionmaker(bind=db.bind, class_=AsyncSession, expire_on_commit=False)
    async with sessions() as first_db, sessions() as second_db:
        first_refund = await first_db.get(RefundRequest, refund.id)
        second_refund = await second_db.get(RefundRequest, refund.id)
        assert first_refund is not None and second_refund is not None

        await RefundService.update_refund(
            first_db,
            first_refund.id,
            status="processed",
            actor_id=admin.id,
            provider_reference="provider-processed",
            note=None,
        )

        async def reject_stale_copy() -> str:
            try:
                await RefundService.update_refund(
                    second_db,
                    second_refund.id,
                    status="rejected",
                    actor_id=admin.id,
                    provider_reference=None,
                    note="stale reject",
                )
                await second_db.commit()
                return "updated"
            except RefundError:
                await second_db.rollback()
                return "rejected"

        stale_update = asyncio.create_task(reject_stale_copy())
        await asyncio.sleep(0.05)
        assert not stale_update.done()
        await first_db.commit()
        assert await stale_update == "rejected"

    await db.refresh(refund)
    await db.refresh(entitlement)
    assert refund.status == "processed"
    assert entitlement.status == "revoked"


@pytest.mark.asyncio
async def test_group_removal_waits_for_last_active_support_entitlement(
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(settings, "TELEGRAM_SUPPORT_GROUP_ID", -1001234567890)
    student = User(
        email="multi-support@example.com",
        password_hash=get_password_hash("studentpass1"),
        role="student",
        telegram_id=99112233,
    )
    first_course = Course(
        title="Support One", price_self=5000, price_support=10000, is_published=True
    )
    second_course = Course(
        title="Support Two", price_self=5000, price_support=10000, is_published=True
    )
    db.add_all([student, first_course, second_course])
    await db.flush()
    now = datetime.utcnow()
    first = Entitlement(
        user_id=student.id,
        course_id=first_course.id,
        source="manual",
        tariff="support",
        status="active",
        starts_at=now,
        expires_at=now + timedelta(days=30),
    )
    second = Entitlement(
        user_id=student.id,
        course_id=second_course.id,
        source="manual",
        tariff="support",
        status="active",
        starts_at=now,
        expires_at=now + timedelta(days=30),
    )
    db.add_all([first, second])
    await db.commit()

    await AccessService.revoke_entitlement(db, first, reason="First support ended")
    await db.commit()
    removals = await db.scalar(
        select(func.count(OutboxMessage.id)).where(
            OutboxMessage.kind == "telegram_group_remove"
        )
    )
    assert removals == 0

    await AccessService.revoke_entitlement(db, second, reason="Last support ended")
    await db.commit()
    removals = await db.scalar(
        select(func.count(OutboxMessage.id)).where(
            OutboxMessage.kind == "telegram_group_remove"
        )
    )
    assert removals == 1
