"""Derived order status in /admin/orders, dashboard and reconciliation (audit B5)."""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.course import Course
from app.models.order import Order
from app.models.payment_event import PaymentEvent
from app.models.purchase import Purchase
from app.models.refund import RefundRequest
from app.models.user import User
from app.services.prodamus_service import _make_signature


async def _admin_headers(client: AsyncClient, db: AsyncSession) -> dict[str, str]:
    admin = User(
        email_verified_at=datetime.utcnow(),
        email="status-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    db.add(admin)
    await db.commit()
    response = await client.post(
        "/api/auth/login", json={"email": admin.email, "password": "adminpass1"}
    )
    assert response.status_code == 200, response.text
    client.cookies.clear()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _order(course: Course, email: str, *, created_at: datetime, status: str = "pending") -> Order:
    return Order(
        course_id=course.id,
        course_title=course.title,
        tariff="self",
        customer_email=email,
        amount_kopecks=500000,
        currency="RUB",
        access_days=30,
        status=status,
        status_token_hash="0" * 64,
        created_at=created_at,
        updated_at=created_at,
    )


async def _seed(db: AsyncSession) -> dict[str, Order]:
    now = datetime.utcnow()
    course = Course(title="Status Course", price_self=5000, price_support=10000, is_published=True)
    buyer = User(
        email_verified_at=now,
        email="status-buyer@example.com",
        password_hash=get_password_hash("buyerpass1"),
        role="student",
    )
    db.add_all([course, buyer])
    await db.flush()
    orders = {
        "pending": _order(course, "pending@example.com", created_at=now - timedelta(minutes=5)),
        "stale": _order(course, "stale@example.com", created_at=now - timedelta(hours=3)),
        "expired": _order(course, "expired@example.com", created_at=now - timedelta(hours=25)),
        "failed": _order(course, "failed@example.com", created_at=now - timedelta(hours=4)),
        "paid": _order(course, "paid@example.com", created_at=now - timedelta(days=2), status="paid"),
        "partial": _order(course, "partial@example.com", created_at=now - timedelta(days=2), status="paid"),
        "refunded": _order(course, "refunded@example.com", created_at=now - timedelta(days=2), status="paid"),
    }
    db.add_all(orders.values())
    await db.flush()
    purchases = {}
    for key in ("paid", "partial", "refunded"):
        purchases[key] = Purchase(
            user_id=buyer.id,
            course_id=course.id,
            order_id=orders[key].id,
            tariff="self",
            amount_kopecks=500000,
            payment_id=f"status-{key}",
            payment_status="success",
            paid_at=now - timedelta(days=2),
            expires_at=now + timedelta(days=28),
        )
    db.add_all(purchases.values())
    await db.flush()
    db.add_all(
        [
            RefundRequest(
                purchase_id=purchases["partial"].id,
                amount_kopecks=100000,
                reason="Partial refund",
                status="processed",
                created_by_id=buyer.id,
                processed_at=now,
            ),
            # A refund that is only requested does not change the display status.
            RefundRequest(
                purchase_id=purchases["paid"].id,
                amount_kopecks=50000,
                reason="Not yet processed",
                status="requested",
                created_by_id=buyer.id,
            ),
            RefundRequest(
                purchase_id=purchases["refunded"].id,
                amount_kopecks=500000,
                reason="Full refund",
                status="processed",
                created_by_id=buyer.id,
                processed_at=now,
            ),
            # A declined attempt is journaled without order_id, only by reference.
            PaymentEvent(
                event_hash="status-declined",
                external_event_id="9100",
                order_reference=f"order|{orders['failed'].id}",
                event_type="fail",
                processing_status="ignored",
                error_code="payment_not_successful",
                sanitized_payload={},
                received_at=now,
                processed_at=now,
            ),
        ]
    )
    await db.commit()
    return orders


@pytest.mark.asyncio
async def test_orders_list_returns_derived_status_and_refund_totals(
    client: AsyncClient, db: AsyncSession
):
    headers = await _admin_headers(client, db)
    orders = await _seed(db)

    response = await client.get("/api/admin/orders?limit=50", headers=headers)
    assert response.status_code == 200, response.text
    by_id = {item["id"]: item for item in response.json()["items"]}
    expected = {
        "pending": ("pending", 0),
        "stale": ("pending", 0),
        "expired": ("expired", 0),
        "failed": ("failed", 0),
        "paid": ("paid", 0),
        "partial": ("partially_refunded", 100000),
        "refunded": ("refunded", 500000),
    }
    for key, (display, refunded) in expected.items():
        item = by_id[str(orders[key].id)]
        assert item["status"] == display, key
        assert item["refunded_kopecks"] == refunded, key
    # The stored status is unchanged and still exposed separately.
    assert by_id[str(orders["expired"].id)]["order_status"] == "pending"
    assert by_id[str(orders["refunded"].id)]["order_status"] == "paid"
    # Refundable = purchase amount minus every non-rejected request.
    assert by_id[str(orders["paid"].id)]["refundable_kopecks"] == 450000
    assert by_id[str(orders["partial"].id)]["refundable_kopecks"] == 400000
    assert by_id[str(orders["refunded"].id)]["refundable_kopecks"] == 0
    assert by_id[str(orders["pending"].id)]["refundable_kopecks"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "keys"),
    [
        ("pending", {"pending", "stale"}),
        ("paid", {"paid"}),
        ("partially_refunded", {"partial"}),
        ("refunded", {"refunded"}),
        ("failed", {"failed"}),
        ("expired", {"expired"}),
    ],
)
async def test_order_status_filter_uses_derived_status(
    client: AsyncClient, db: AsyncSession, status: str, keys: set[str]
):
    headers = await _admin_headers(client, db)
    orders = await _seed(db)

    response = await client.get(f"/api/admin/orders?status={status}", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["total"] == len(keys)
    assert {item["id"] for item in response.json()["items"]} == {
        str(orders[key].id) for key in keys
    }


@pytest.mark.asyncio
async def test_dashboard_and_reconciliation_count_only_open_pending_orders(
    client: AsyncClient, db: AsyncSession
):
    headers = await _admin_headers(client, db)
    await _seed(db)

    dashboard = await client.get("/api/admin/dashboard", headers=headers)
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["pending_orders"] == 2

    reconciliation = await client.get("/api/admin/reconciliation", headers=headers)
    assert reconciliation.status_code == 200, reconciliation.text
    # Only the 3-hour-old open order: expired and failed orders are settled.
    assert reconciliation.json()["stale_pending_orders"] == 1


@pytest.mark.asyncio
async def test_expired_order_still_accepts_a_late_payment(
    client: AsyncClient, db: AsyncSession
):
    headers = await _admin_headers(client, db)
    course = Course(title="Late Course", price_self=5000, price_support=10000, is_published=True)
    db.add(course)
    await db.flush()
    order = _order(course, "late@example.com", created_at=datetime.utcnow() - timedelta(hours=30))
    db.add(order)
    await db.commit()

    before = await client.get("/api/admin/orders?status=expired", headers=headers)
    assert [item["id"] for item in before.json()["items"]] == [str(order.id)]

    payload = {
        "order_id": "9200",
        "order_num": f"order|{order.id}",
        "customer_email": "late@example.com",
        "sum": "5000",
        "currency": "rub",
        "payment_status": "success",
    }
    signature = _make_signature(payload, "test-prodamus-hmac-secret-key-for-ci")
    webhook = await client.post("/api/payments/webhook", json=payload, headers={"Sign": signature})
    assert webhook.status_code == 200, webhook.text
    assert (
        await db.scalar(select(Purchase.id).where(Purchase.payment_id == "9200"))
    ) is not None

    after = await client.get("/api/admin/orders", headers=headers)
    item = next(row for row in after.json()["items"] if row["id"] == str(order.id))
    assert item["status"] == "paid"
