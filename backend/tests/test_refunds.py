from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.course import Course
from app.models.entitlement import Entitlement
from app.models.purchase import Purchase
from app.models.refund import RefundRequest
from app.models.user import User
from app.models.analytics_event import AnalyticsEvent


@pytest.mark.asyncio
async def test_admin_refund_workflow_revokes_access_without_rewriting_purchase(
    client: AsyncClient,
    db: AsyncSession,
):
    admin = User(
        email="refund-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    student = User(
        email="refund-student@example.com",
        password_hash=get_password_hash("studentpass1"),
        role="student",
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
        tariff="self",
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
        tariff="self",
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
    refund_event = await db.scalar(
        select(AnalyticsEvent).where(
            AnalyticsEvent.event_name == "refund_processed",
            AnalyticsEvent.user_id == student.id,
        )
    )
    assert refund_event is not None
    assert refund_event.course_id == course.id

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
