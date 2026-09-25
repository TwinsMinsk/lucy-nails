from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.course import Course
from app.models.purchase import Purchase
from app.models.user import User


async def _admin_headers(client: AsyncClient, db: AsyncSession) -> dict[str, str]:
    admin = User(
        email="course-admin@example.com",
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
async def test_course_with_purchase_cannot_be_deleted(
    client: AsyncClient, db: AsyncSession
):
    headers = await _admin_headers(client, db)
    course = Course(title="Paid Course", price_self=5000, price_support=10000)
    buyer = User(
        email="paid-buyer@example.com",
        password_hash=get_password_hash("buyerpass1"),
        role="student",
    )
    db.add_all([course, buyer])
    await db.flush()
    purchase = Purchase(
        user_id=buyer.id,
        course_id=course.id,
        tariff="self",
        amount_kopecks=500000,
        payment_id="delete-guard-purchase",
        payment_status="success",
        paid_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(purchase)
    await db.commit()
    course_id, purchase_id = course.id, purchase.id

    response = await client.delete(f"/api/admin/courses/{course_id}", headers=headers)

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == (
        "Курс с оплатами или доступами нельзя удалить — снимите его с публикации"
    )
    db.expire_all()
    assert await db.scalar(select(Course.id).where(Course.id == course_id)) == course_id
    assert (
        await db.scalar(select(Purchase.id).where(Purchase.id == purchase_id))
        == purchase_id
    )


@pytest.mark.asyncio
async def test_course_without_payments_is_deleted(client: AsyncClient, db: AsyncSession):
    headers = await _admin_headers(client, db)
    course = Course(title="Draft Course", price_self=5000, price_support=10000)
    db.add(course)
    await db.commit()
    course_id = course.id

    response = await client.delete(f"/api/admin/courses/{course_id}", headers=headers)

    assert response.status_code == 200, response.text
    db.expire_all()
    assert await db.scalar(select(Course.id).where(Course.id == course_id)) is None
