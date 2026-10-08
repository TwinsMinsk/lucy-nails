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
        email_verified_at=datetime.utcnow(),
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
        [
            "landing_view",
            "cta_click",
            "checkout_started",
            "payment_redirect",
            "purchase_confirmed",
        ]
    ):
        db.add(
            AnalyticsEvent(
                event_id=f"report-event-{index}",
                event_name=event_name,
                source="server" if event_name == "purchase_confirmed" else "web",
                anonymous_id="report-visitor",
                order_id=paid_order.id
                if "payment" in event_name or "purchase" in event_name
                else None,
                course_id=course.id,
                happened_at=now - timedelta(hours=5 - index),
                utm_source="instagram",
                properties={},
            )
        )
    db.add_all(
        [
            AnalyticsEvent(
                event_id="report-event-duplicate-cta",
                event_name="cta_click",
                source="web",
                anonymous_id="report-visitor",
                course_id=course.id,
                happened_at=now - timedelta(hours=3, minutes=30),
                properties={"tariff": "support", "location": "pricing"},
            ),
            AnalyticsEvent(
                event_id="report-event-orphan-purchase",
                event_name="purchase_confirmed",
                source="server",
                order_id=pending_order.id,
                course_id=course.id,
                happened_at=now,
                properties={"tariff": "self"},
            ),
        ]
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
    assert instagram["orders"] == 1
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


async def _report_fixture(db):
    now = datetime.utcnow()
    admin = User(
        email="report-regression-admin@example.com",
        password_hash="unused",
        role="admin",
    )
    student = User(
        email="report-regression-student@example.com",
        password_hash="unused",
        role="student",
        email_verified_at=now,
    )
    course = Course(
        title="Regression course", price_self=100, price_support=200, is_published=True
    )
    db.add_all([admin, student, course])
    await db.flush()
    token = AuthService.create_tokens(admin.id, admin.token_version).access_token
    return now, admin, student, course, {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_manual_legacy_grant_is_not_money_and_legacy_payment_is(client, db):
    now, admin, student, course, headers = await _report_fixture(db)
    for payment_id, amount in [
        ("admin_grant_legacy", 90000),
        ("real-historical-payment", 10000),
    ]:
        db.add(
            Purchase(
                user_id=student.id,
                course_id=course.id,
                tariff="self",
                amount_kopecks=amount,
                payment_id=payment_id,
                payment_status="success",
                paid_at=now,
                expires_at=now + timedelta(days=30),
            )
        )
    await db.commit()
    overview = await client.get("/api/admin/reports/overview", headers=headers)
    assert overview.status_code == 200, overview.text
    assert overview.json()["gross_revenue_kopecks"] == 10000
    assert overview.json()["paid_orders"] == 1
    tariffs = await client.get("/api/admin/reports/tariffs", headers=headers)
    assert tariffs.json() == [
        {"tariff": "self", "paid_orders": 1, "gross_revenue_kopecks": 10000}
    ]
    cohorts = await client.get("/api/admin/reports/cohorts", headers=headers)
    assert cohorts.json()[0]["purchasers"] == 1
    sources = await client.get("/api/admin/reports/sources", headers=headers)
    assert sum(row["gross_revenue_kopecks"] for row in sources.json()) == 10000
    timeseries = await client.get("/api/admin/reports/timeseries", headers=headers)
    assert sum(row["gross_revenue_kopecks"] for row in timeseries.json()) == 10000


@pytest.mark.asyncio
async def test_sources_money_uses_payment_date_with_separate_acquisition_cohort(
    client, db
):
    now, admin, student, course, headers = await _report_fixture(db)
    paid_at = datetime(2026, 10, 5, 12)
    order = Order(
        user_id=student.id,
        course_id=course.id,
        course_title=course.title,
        tariff="self",
        customer_email=student.email,
        amount_kopecks=10000,
        access_days=30,
        status="paid",
        status_token_hash="regression-cross-month",
        first_utm_source="yandex",
        first_utm_campaign="launch",
        first_utm_content="ad-1",
        created_at=datetime(2026, 9, 30, 23),
        paid_at=paid_at,
    )
    db.add(order)
    await db.flush()
    purchase = Purchase(
        user_id=student.id,
        course_id=course.id,
        order_id=order.id,
        tariff="self",
        amount_kopecks=10000,
        payment_id="cross-month-payment",
        payment_status="success",
        paid_at=paid_at,
        expires_at=now + timedelta(days=30),
    )
    db.add(purchase)
    await db.flush()
    db.add(
        RefundRequest(
            purchase_id=purchase.id,
            amount_kopecks=2000,
            reason="refund",
            status="processed",
            created_by_id=admin.id,
            processed_by_id=admin.id,
            processed_at=datetime(2026, 10, 7),
        )
    )
    await db.commit()
    query = "date_from=2026-10-01&date_to=2026-10-31"
    sources = await client.get(f"/api/admin/reports/sources?{query}", headers=headers)
    assert sources.status_code == 200, sources.text
    assert sources.json()[0]["gross_revenue_kopecks"] == 10000
    assert sources.json()[0]["campaign"] == "launch"
    assert sources.json()[0]["content"] == "ad-1"
    assert sources.json()[0]["date_basis"] == "paid_at_utc"
    cohort = await client.get(
        f"/api/admin/reports/sources?{query}&basis=acquisition", headers=headers
    )
    assert cohort.json() == []
    filtered = await client.get(
        f"/api/admin/reports/sources?{query}&campaign=other", headers=headers
    )
    assert filtered.json() == []
    overview = await client.get(f"/api/admin/reports/overview?{query}", headers=headers)
    assert overview.json()["net_revenue_kopecks"] == 8000
    series = await client.get(f"/api/admin/reports/timeseries?{query}", headers=headers)
    assert (
        next(row for row in series.json() if row["date"] == "2026-10-07")[
            "refunded_kopecks"
        ]
        == 2000
    )


@pytest.mark.asyncio
async def test_funnel_finds_later_valid_sequence_after_orphan_cta(client, db):
    now, admin, student, course, headers = await _report_fixture(db)
    for index, name in enumerate(
        [
            "cta_click",
            "landing_view",
            "cta_click",
            "checkout_started",
            "payment_redirect",
            "purchase_confirmed",
            "purchase_confirmed",
        ]
    ):
        db.add(
            AnalyticsEvent(
                event_id=f"ordered-{index}",
                event_name=name,
                source="server" if index >= 3 else "web",
                anonymous_id="ordered-visitor",
                course_id=course.id,
                happened_at=now - timedelta(minutes=10 - index),
                properties={},
            )
        )
    await db.commit()
    response = await client.get("/api/admin/reports/funnel", headers=headers)
    assert response.status_code == 200, response.text
    assert [row["count"] for row in response.json()["stages"]] == [1, 1, 1, 1, 1]


@pytest.mark.asyncio
async def test_learning_activity_reports_visit_without_progress_update(client, db):
    now, admin, student, course, headers = await _report_fixture(db)
    db.add(
        AnalyticsEvent(
            event_id="repeat-lesson-activity",
            event_name="lesson_activity",
            source="server",
            user_id=student.id,
            course_id=course.id,
            happened_at=now,
            properties={},
        )
    )
    await db.commit()
    response = await client.get("/api/admin/reports/progress", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["active_students"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hostile",
    [
        "=1+1",
        " +SUM(1)",
        "\t@SUM(1)",
        "\r-1",
        "\x01=HYPERLINK(1)",
        "\u2003=1",
        "\ufeff \t=1",
    ],
)
async def test_sources_csv_escapes_all_user_controlled_text(client, db, hostile):
    now, admin, student, course, headers = await _report_fixture(db)
    order = Order(
        user_id=student.id,
        course_id=course.id,
        course_title=course.title,
        tariff="self",
        customer_email=student.email,
        amount_kopecks=10000,
        access_days=30,
        status="paid",
        status_token_hash="hostile-source",
        first_utm_source=hostile,
        first_utm_campaign=hostile,
        first_utm_content=hostile,
    )
    db.add(order)
    await db.flush()
    db.add(
        Purchase(
            user_id=student.id,
            course_id=course.id,
            order_id=order.id,
            tariff="self",
            amount_kopecks=10000,
            payment_id="hostile-payment",
            payment_status="success",
            paid_at=now,
            expires_at=now + timedelta(days=30),
        )
    )
    await db.commit()
    response = await client.get(
        "/api/admin/reports/sources?format=csv", headers=headers
    )
    import csv
    import io

    row = next(csv.DictReader(io.StringIO(response.text.lstrip("\ufeff"))))
    assert row["source"].startswith("'")
    assert row["campaign"].startswith("'")
    assert row["content"].startswith("'")


@pytest.mark.asyncio
async def test_funnel_counts_each_order_and_does_not_get_stuck_on_abandoned_checkout(
    client, db
):
    now, admin, student, course, headers = await _report_fixture(db)
    orders = []
    for index in range(3):
        order = Order(
            user_id=student.id,
            course_id=course.id,
            course_title=course.title,
            tariff="self",
            customer_email=student.email,
            amount_kopecks=10000,
            access_days=30,
            status_token_hash=f"funnel-order-{index}",
        )
        db.add(order)
        orders.append(order)
    await db.flush()
    events = [
        ("landing_view", None),
        ("cta_click", None),
        ("checkout_started", orders[0].id),
        ("checkout_started", orders[1].id),
        ("payment_redirect", orders[1].id),
        ("purchase_confirmed", orders[1].id),
        ("checkout_started", orders[2].id),
        ("payment_redirect", orders[2].id),
        ("purchase_confirmed", orders[2].id),
        ("purchase_confirmed", orders[2].id),
    ]
    for index, (name, order_id) in enumerate(events):
        db.add(
            AnalyticsEvent(
                event_id=f"multi-order-{index}",
                event_name=name,
                source="server" if order_id else "web",
                anonymous_id="multi-visitor" if name != "purchase_confirmed" else None,
                user_id=student.id if order_id else None,
                order_id=order_id,
                course_id=course.id,
                happened_at=now - timedelta(minutes=20 - index),
                properties={},
            )
        )
    await db.commit()
    response = await client.get("/api/admin/reports/funnel", headers=headers)
    assert [row["count"] for row in response.json()["stages"]] == [3, 3, 3, 2, 2]


@pytest.mark.asyncio
async def test_explicit_manual_grant_and_its_refund_do_not_change_financial_reports(
    client, db
):
    now, admin, student, course, headers = await _report_fixture(db)
    purchase = Purchase(
        user_id=student.id,
        course_id=course.id,
        tariff="self",
        amount_kopecks=50000,
        payment_id="manual-without-known-prefix",
        payment_status="success",
        transaction_kind="manual_grant",
        paid_at=now,
        expires_at=now + timedelta(days=30),
    )
    db.add(purchase)
    await db.flush()
    db.add(
        RefundRequest(
            purchase_id=purchase.id,
            amount_kopecks=10000,
            reason="historical manual adjustment",
            status="processed",
            created_by_id=admin.id,
            processed_at=now,
        )
    )
    await db.commit()
    overview = await client.get("/api/admin/reports/overview", headers=headers)
    assert overview.json()["gross_revenue_kopecks"] == 0
    assert overview.json()["refunded_kopecks"] == 0
    assert overview.json()["paid_orders"] == 0
    cohort = await client.get("/api/admin/reports/cohorts", headers=headers)
    assert cohort.json()[0]["purchasers"] == 0
