"""/admin/purchases/page pages and separates real payments from manual grants (audit I8).

/admin/purchases keeps the plain list of master for tabs left open across a deploy.
"""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.course import Course
from app.models.purchase import Purchase
from app.models.user import User
from conftest import mfa_login


@pytest.mark.asyncio
async def test_purchases_are_paginated_and_default_to_real_payments(
    client: AsyncClient, db: AsyncSession
):
    admin = User(
        email_verified_at=datetime.utcnow(),
        email="purchases-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    buyer = User(email="purchases-buyer@example.com", password_hash="unused", role="student")
    course = Course(title="Purchases Course", price_self=5000, price_support=10000)
    db.add_all([admin, buyer, course])
    await db.flush()
    now = datetime.utcnow()
    paid = [
        Purchase(
            user_id=buyer.id,
            course_id=course.id,
            tariff="self",
            amount_kopecks=500000,
            payment_id=f"real-{index}",
            payment_status="success",
            paid_at=now - timedelta(days=300 - index),
            created_at=now - timedelta(days=300 - index),
            expires_at=now + timedelta(days=30),
        )
        for index in range(3)
    ]
    # 205 newer manual grants (204 + one legacy admin_grant_) used to push every
    # real payment out of the last 200 rows.
    manual = [
        Purchase(
            user_id=buyer.id,
            course_id=course.id,
            tariff="self",
            amount_kopecks=0,
            transaction_kind="manual_grant",
            payment_id=f"manual-{index}",
            payment_status="success",
            created_at=now - timedelta(minutes=index),
            expires_at=now + timedelta(days=30),
        )
        for index in range(204)
    ]
    legacy_grant = Purchase(
        user_id=buyer.id,
        course_id=course.id,
        tariff="self",
        amount_kopecks=0,
        payment_id="admin_grant_legacy",
        payment_status="success",
        created_at=now,
        expires_at=now + timedelta(days=30),
    )
    db.add_all([*paid, *manual, legacy_grant])
    await db.commit()
    login = await mfa_login(client, db, admin.email, "adminpass1")
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    default = await client.get("/api/admin/purchases/page", headers=headers)
    assert default.status_code == 200, default.text
    assert default.json()["total"] == 3
    assert [item["payment_id"] for item in default.json()["items"]] == ["real-2", "real-1", "real-0"]
    assert {item["kind"] for item in default.json()["items"]} == {"paid"}

    manual_page = await client.get(
        "/api/admin/purchases/page?kind=manual&limit=50&offset=200", headers=headers
    )
    assert manual_page.status_code == 200, manual_page.text
    assert manual_page.json()["total"] == 205
    assert manual_page.json()["offset"] == 200
    assert len(manual_page.json()["items"]) == 5
    assert {item["kind"] for item in manual_page.json()["items"]} == {"manual"}

    everything = await client.get("/api/admin/purchases/page?kind=all&limit=1", headers=headers)
    assert everything.json()["total"] == 208
    assert len(everything.json()["items"]) == 1

    assert (await client.get("/api/admin/purchases/page?kind=bogus", headers=headers)).status_code == 422

    # The legacy URL still answers the plain list of the last 200 rows of any kind.
    legacy = await client.get("/api/admin/purchases", headers=headers)
    assert legacy.status_code == 200, legacy.text
    assert isinstance(legacy.json(), list)
    assert len(legacy.json()) == 200
    assert {"id", "payment_id", "user_email", "access_status"} <= set(legacy.json()[0])