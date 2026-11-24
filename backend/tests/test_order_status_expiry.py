"""The order status token stops working 72 hours after the order was created."""

import hashlib
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.order import Order

TOKEN = "order-status-token-for-tests"


async def _order(db: AsyncSession, age: timedelta) -> Order:
    course = Course(title="Status course", price_self=5900, price_support=11900)
    db.add(course)
    await db.flush()
    order = Order(
        course_id=course.id,
        course_title=course.title,
        tariff="self",
        customer_email="buyer@example.com",
        amount_kopecks=590000,
        currency="RUB",
        access_days=30,
        status="paid",
        status_token_hash=hashlib.sha256(TOKEN.encode("utf-8")).hexdigest(),
        created_at=datetime.utcnow() - age,
    )
    db.add(order)
    await db.commit()
    return order


@pytest.mark.asyncio
async def test_status_token_works_the_next_day(client: AsyncClient, db: AsyncSession):
    order = await _order(db, timedelta(hours=71))

    response = await client.get(
        f"/api/payments/orders/order|{order.id}/status", params={"token": TOKEN}
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "paid"


@pytest.mark.asyncio
async def test_expired_status_token_reads_as_unknown_order(client: AsyncClient, db: AsyncSession):
    order = await _order(db, timedelta(hours=73))

    response = await client.get(
        f"/api/payments/orders/order|{order.id}/status", params={"token": TOKEN}
    )
    unknown = await client.get(
        f"/api/payments/orders/order|{order.id}/status", params={"token": "wrong-token"}
    )

    assert response.status_code == 404
    assert response.json() == unknown.json() == {"detail": "Order not found"}
