"""Management reporting contracts and money source-of-truth rules."""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.analytics_event import AnalyticsEvent
from app.models.course import Course
from app.models.order import Order
from app.models.outbox import OutboxMessage
from app.models.purchase import Purchase
from app.models.refund import RefundRequest
from app.models.user import User
from app.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_reports_use_confirmed_money_and_expose_csv(
    client: AsyncClient, db: AsyncSession
):
    now = datetime.utcnow()
    admin = User(
        email="reports-admin@example.com",
        password_hash=get_password_hash("reports-admin-password"),
        role="admin",
    )
    student = User(
        email="reports-student@example.com",
        password_hash=get_password_hash("reports-student-password"),
        role="student",
        created_at=now - timedelta(days=2),
    )
    course = Course(
        title="Reporting course",
        price_self=10000,
        price_support=15000,
        is_published=True,
    )
    db.add_all([admin, student, course])
    await db.flush()

    paid_order = Order(
        user_id=student.id,
        course_id=course.id,
        course_title="Reporting course",
        tariff="support",
        customer_email=student.email,
        amount_kopecks=1_500_000,
        currency="RUB",
        access_days=30,
        status="paid",
        status_token_hash="paid-order-token-hash",
        first_utm_source="instagram",
        last_utm_source="telegram",
        paid_at=now - timedelta(days=1),
        created_at=now - timedelta(days=2),
    )
    pending_order = Order(
        course_id=course.id,
        course_title="Reporting course",
        tariff="self",
        customer_email="pending@example.com",
        amount_kopecks=1_000_000,
        currency="RUB",
        access_days=30,
        status="pending",
        status_token_hash="pending-order-token-hash",
        first_utm_source="instagram",
        last_utm_source="instagram",
        created_at=now - timedelta(days=1),
    )
    db.add_all([paid_order, pending_order])
    await db.flush()
    purchase = Purchase(
        user_id=student.id,
        course_id=course.id,
        order_id=paid_order.id,
        tariff="support",
        amount_kopecks=1_500_000,
        payment_id="reports-payment",
        payment_status="success",
        paid_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=29),
        created_at=now - timedelta(days=1),
    )
    db.add(purchase)
    await db.flush()
    db.add(
        RefundRequest(
            purchase_id=purchase.id,
            amount_kopecks=300_000,
            reason="Partial refund for report test",
            status="processed",
            created_by_id=admin.id,
            processed_by_id=admin.id,
            processed_at=now,
        )
    )
    for index, event_name in enumerate(
        ["landing_view", "cta_click", "checkout_started", "payment_redirect", "purchase_confirmed"]
    ):
        db.add(
            AnalyticsEvent(
                event_id=f"report-event-{index}",
                event_name=event_name,
                source="server" if event_name == "purchase_confirmed" else "web",
                anonymous_id="report-visitor",
                order_id=paid_order.id if "payment" in event_name or "purchase" in event_name else None,
                course_id=course.id,
                happened_at=now - timedelta(hours=5 - index),
                utm_source="instagram",
                properties={},
            )
        )
    db.add_all(
        [
            OutboxMessage(
                kind="access_opened",
                channel="email",
                recipient=student.email,
                payload={},
                status="sent",
                dedupe_key="reports-sent",
            ),
            OutboxMessage(
                kind="access_opened",
                channel="email",
                recipient=student.email,
                payload={},
                status="dead_letter",
                dedupe_key="reports-dead",
            ),
        ]
    )
    await db.commit()

    token = AuthService.create_tokens(admin.id, admin.token_version).access_token
    headers = {"Authorization": f"Bearer {token}"}
    date_from = (now - timedelta(days=7)).date().isoformat()
    date_to = (now + timedelta(days=1)).date().isoformat()

    overview = await client.get(
        f"/api/admin/reports/overview?date_from={date_from}&date_to={date_to}",
        headers=headers,
    )
    assert overview.status_code == 200, overview.text
    assert overview.json()["gross_revenue_kopecks"] == 1_500_000
    assert overview.json()["refunded_kopecks"] == 300_000
    assert overview.json()["net_revenue_kopecks"] == 1_200_000
    assert overview.json()["paid_orders"] == 1
    assert overview.json()["pending_orders"] == 1

    funnel = await client.get(
        f"/api/admin/reports/funnel?date_from={date_from}&date_to={date_to}",
        headers=headers,
    )
    assert funnel.status_code == 200, funnel.text
    assert [stage["count"] for stage in funnel.json()["stages"]] == [1, 1, 1, 1, 1]

    sources = await client.get(
        f"/api/admin/reports/sources?date_from={date_from}&date_to={date_to}",
        headers=headers,
    )
    assert sources.status_code == 200, sources.text
    instagram = next(item for item in sources.json() if item["source"] == "instagram")
    assert instagram["orders"] == 2
    assert instagram["paid_orders"] == 1
    assert instagram["gross_revenue_kopecks"] == 1_500_000

    delivery = await client.get(
        f"/api/admin/reports/delivery?date_from={date_from}&date_to={date_to}",
        headers=headers,
    )
    assert delivery.status_code == 200, delivery.text
    assert delivery.json()["sent"] == 1
    assert delivery.json()["dead_letter"] == 1

    csv_response = await client.get(
        f"/api/admin/reports/sources?date_from={date_from}&date_to={date_to}&format=csv",
        headers=headers,
    )
    assert csv_response.status_code == 200, csv_response.text
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "instagram" in csv_response.text
