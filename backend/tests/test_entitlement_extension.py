"""Admin access extension: only the latest access, idempotency (audit I13, review 1)."""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.entitlement import Entitlement
from app.models.purchase import Purchase
from app.models.refund import RefundRequest
from app.models.user import User
from app.services.email_service import format_msk_datetime
from conftest import TestingSessionLocal


async def _setup(client: AsyncClient, db: AsyncSession):
    admin = User(
        email_verified_at=datetime.utcnow(),
        email="extend-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    student = User(
        email_verified_at=datetime.utcnow(),
        email="extend-student@example.com",
        password_hash="unused",
        role="student",
    )
    course = Course(title="Extend Course", price_self=5000, price_support=10000)
    db.add_all([admin, student, course])
    await db.flush()
    now = datetime.utcnow()
    old = Entitlement(
        user_id=student.id,
        course_id=course.id,
        source="purchase",
        tariff="self",
        status="active",
        starts_at=now - timedelta(days=28),
        expires_at=now + timedelta(days=2),
    )
    renewed = Entitlement(
        user_id=student.id,
        course_id=course.id,
        source="purchase",
        tariff="self",
        status="active",
        starts_at=now,
        expires_at=now + timedelta(days=32),
    )
    db.add_all([old, renewed])
    await db.commit()
    login = await client.post(
        "/api/auth/login", json={"email": admin.email, "password": "adminpass1"}
    )
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    return headers, old, renewed


@pytest.mark.asyncio
async def test_extending_an_older_row_is_refused_and_names_the_later_access(
    client: AsyncClient, db: AsyncSession
):
    headers, old, renewed = await _setup(client, db)
    old_end = old.expires_at

    response = await client.post(
        f"/api/admin/entitlements/{old.id}/extend",
        json={"days": 10, "reason": "Goodwill extension"},
        headers=headers,
    )

    assert response.status_code == 409, response.text
    assert "более поздний доступ" in response.json()["detail"]
    assert format_msk_datetime(renewed.expires_at) in response.json()["detail"]
    async with TestingSessionLocal() as fresh:
        assert (await fresh.get(Entitlement, old.id)).expires_at == old_end
        assert (
            await fresh.scalar(select(AuditLog.id).where(AuditLog.action == "entitlement.extend"))
        ) is None

    listed = await client.get("/api/admin/entitlements?status=active", headers=headers)
    latest = {item["id"]: item["is_latest_access"] for item in listed.json()["items"]}
    assert latest == {str(old.id): False, str(renewed.id): True}


@pytest.mark.asyncio
async def test_extending_the_latest_row_adds_days_to_its_own_end(
    client: AsyncClient, db: AsyncSession
):
    headers, _, renewed = await _setup(client, db)
    renewed_end = renewed.expires_at

    response = await client.post(
        f"/api/admin/entitlements/{renewed.id}/extend",
        json={"days": 5, "reason": "Goodwill extension"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    async with TestingSessionLocal() as fresh:
        assert (await fresh.get(Entitlement, renewed.id)).expires_at == renewed_end + timedelta(days=5)


@pytest.mark.asyncio
async def test_repeated_extension_with_the_same_key_adds_days_once(
    client: AsyncClient, db: AsyncSession
):
    headers, _, renewed = await _setup(client, db)
    renewed_end = renewed.expires_at
    payload = {"days": 7, "reason": "Goodwill extension", "idempotency_key": "dialog-key-0001"}

    first = await client.post(f"/api/admin/entitlements/{renewed.id}/extend", json=payload, headers=headers)
    second = await client.post(f"/api/admin/entitlements/{renewed.id}/extend", json=payload, headers=headers)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["expires_at"] == second.json()["expires_at"]
    async with TestingSessionLocal() as fresh:
        assert (await fresh.get(Entitlement, renewed.id)).expires_at == renewed_end + timedelta(days=7)
        audits = (
            await fresh.execute(select(AuditLog).where(AuditLog.action == "entitlement.extend"))
        ).scalars().all()
    assert len(audits) == 1
    assert audits[0].new_value["idempotency_key"] == "dialog-key-0001"

    # A new dialog (new key) is a new, deliberate extension.
    third = await client.post(
        f"/api/admin/entitlements/{renewed.id}/extend",
        json={**payload, "idempotency_key": "dialog-key-0002"},
        headers=headers,
    )
    assert third.status_code == 200, third.text
    async with TestingSessionLocal() as fresh:
        assert (await fresh.get(Entitlement, renewed.id)).expires_at == renewed_end + timedelta(days=14)


@pytest.mark.asyncio
async def test_concurrent_double_submit_adds_days_once(client: AsyncClient, db: AsyncSession):
    import asyncio

    from app.core.database import get_db
    from app.main import app

    headers, _, renewed = await _setup(client, db)
    renewed_end = renewed.expires_at

    async def isolated_db():
        async with TestingSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = isolated_db
    payload = {"days": 3, "reason": "Goodwill extension", "idempotency_key": "double-click-01"}
    responses = await asyncio.gather(
        *(
            client.post(f"/api/admin/entitlements/{renewed.id}/extend", json=payload, headers=headers)
            for _ in range(2)
        )
    )

    assert [response.status_code for response in responses] == [200, 200]
    async with TestingSessionLocal() as fresh:
        assert (await fresh.get(Entitlement, renewed.id)).expires_at == renewed_end + timedelta(days=3)


async def _two_purchases(client: AsyncClient, db: AsyncSession):
    """A: older purchase with 5 days left; B: later purchase ending in 35 days."""
    admin = User(
        email_verified_at=datetime.utcnow(),
        email="two-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    student = User(
        email_verified_at=datetime.utcnow(),
        email="two-student@example.com",
        password_hash="unused",
        role="student",
    )
    course = Course(title="Two Purchases", price_self=5000, price_support=10000)
    db.add_all([admin, student, course])
    await db.flush()
    now = datetime.utcnow()
    rows = {}
    for key, days_left, tariff in (("a", 5, "support"), ("b", 35, "self")):
        purchase = Purchase(
            user_id=student.id,
            course_id=course.id,
            tariff=tariff,
            amount_kopecks=500000,
            payment_id=f"two-{key}",
            payment_status="success",
            paid_at=now,
            expires_at=now + timedelta(days=days_left),
        )
        db.add(purchase)
        await db.flush()
        entitlement = Entitlement(
            user_id=student.id,
            course_id=course.id,
            source_purchase_id=purchase.id,
            source="purchase",
            tariff=tariff,
            status="active",
            starts_at=now,
            expires_at=now + timedelta(days=days_left),
        )
        db.add(entitlement)
        await db.flush()
        rows[key] = (purchase, entitlement)
    refund = RefundRequest(
        purchase_id=rows["b"][0].id,
        amount_kopecks=500000,
        reason="Full refund of the later purchase",
        status="submitted",
        provider_reference="P-TWO-B",
        created_by_id=admin.id,
    )
    db.add(refund)
    await db.commit()
    login = await client.post(
        "/api/auth/login", json={"email": admin.email, "password": "adminpass1"}
    )
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    return headers, rows, refund.id


async def _student_access_end(entitlement_ids) -> datetime | None:
    async with TestingSessionLocal() as fresh:
        ends = [
            row.expires_at
            for row in [await fresh.get(Entitlement, item) for item in entitlement_ids]
            if row.status == "active" and row.expires_at > datetime.utcnow()
        ]
    return max(ends, default=None)


@pytest.mark.asyncio
async def test_extending_the_older_purchase_is_refused_and_a_refund_of_the_later_keeps_no_days(
    client: AsyncClient, db: AsyncSession
):
    headers, rows, refund_id = await _two_purchases(client, db)
    a_end = rows["a"][1].expires_at

    refused = await client.post(
        f"/api/admin/entitlements/{rows['a'][1].id}/extend",
        json={"days": 1, "reason": "Goodwill extension"},
        headers=headers,
    )
    assert refused.status_code == 409, refused.text

    refund = await client.put(
        f"/api/admin/refunds/{refund_id}",
        json={"status": "processed", "reason": "Confirmed in Prodamus"},
        headers=headers,
    )
    assert refund.status_code == 200, refund.text
    # Only A's own period remains: nothing of the refunded purchase B.
    assert await _student_access_end([rows["a"][1].id, rows["b"][1].id]) == a_end


@pytest.mark.asyncio
async def test_extending_the_latest_purchase_then_refunding_it_keeps_no_refunded_days(
    client: AsyncClient, db: AsyncSession
):
    headers, rows, refund_id = await _two_purchases(client, db)
    a_end = rows["a"][1].expires_at
    b_end = rows["b"][1].expires_at

    extended = await client.post(
        f"/api/admin/entitlements/{rows['b'][1].id}/extend",
        json={"days": 1, "reason": "Goodwill extension"},
        headers=headers,
    )
    assert extended.status_code == 200, extended.text
    async with TestingSessionLocal() as fresh:
        assert (await fresh.get(Entitlement, rows["b"][1].id)).expires_at == b_end + timedelta(days=1)
        assert (await fresh.get(Entitlement, rows["a"][1].id)).expires_at == a_end

    refund = await client.put(
        f"/api/admin/refunds/{refund_id}",
        json={"status": "processed", "reason": "Confirmed in Prodamus"},
        headers=headers,
    )
    assert refund.status_code == 200, refund.text
    async with TestingSessionLocal() as fresh:
        assert (await fresh.get(Entitlement, rows["b"][1].id)).status == "revoked"
    assert await _student_access_end([rows["a"][1].id, rows["b"][1].id]) == a_end


@pytest.mark.asyncio
async def test_repeated_key_returns_the_first_result_and_rejects_other_parameters(
    client: AsyncClient, db: AsyncSession
):
    headers, _, renewed = await _setup(client, db)
    url = f"/api/admin/entitlements/{renewed.id}/extend"
    payload = {"days": 7, "reason": "Goodwill extension", "idempotency_key": "dialog-key-1001"}

    first = await client.post(url, json=payload, headers=headers)
    assert first.status_code == 200, first.text
    # Something else changes the row afterwards.
    later = await client.post(
        url, json={**payload, "days": 3, "idempotency_key": "dialog-key-1002"}, headers=headers
    )
    assert later.status_code == 200, later.text

    repeat = await client.post(url, json=payload, headers=headers)
    assert repeat.status_code == 200, repeat.text
    # The stored result of the first operation, not the current state.
    assert repeat.json() == first.json()

    other_days = await client.post(url, json={**payload, "days": 30}, headers=headers)
    assert other_days.status_code == 409, other_days.text
    assert "другими параметрами" in other_days.json()["detail"]
    other_reason = await client.post(url, json={**payload, "reason": "Another reason here"}, headers=headers)
    assert other_reason.status_code == 409, other_reason.text
    async with TestingSessionLocal() as fresh:
        assert (await fresh.get(Entitlement, renewed.id)).expires_at.isoformat() == later.json()["expires_at"]