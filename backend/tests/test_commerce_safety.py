from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.certificate import Certificate
from app.models.course import Course
from app.models.entitlement import Entitlement
from app.models.outbox import OutboxMessage
from app.models.payment_event import PaymentEvent
from app.models.purchase import Purchase
from app.models.user import User
from app.services.access_service import AccessService
from app.services.certificate_service import CertificateService
from app.services.prodamus_service import _make_signature
from app.services.refund_service import RefundError, RefundService
from app.services.auth_service import AuthService
from conftest import TestingSessionLocal
import asyncio


async def purchase_fixture(db, state="active"):
    user = User(
        email="commerce@example.com",
        password_hash=get_password_hash("password123"),
        email_verified_at=datetime.utcnow(),
        role="student",
    )
    actor = User(email="operator@example.com", password_hash="unused", role="admin")
    course = Course(
        title="Commerce", price_self=5000, price_support=10000, is_published=True
    )
    db.add_all([user, actor, course])
    await db.flush()
    purchase = Purchase(
        user_id=user.id,
        course_id=course.id,
        tariff="self",
        payment_id="paid",
        amount_kopecks=500000,
        payment_status="success",
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(purchase)
    await db.flush()
    access = AccessService.create_purchase_entitlement(purchase)
    access.status = state
    cert = Certificate(
        user_id=user.id,
        course_id=course.id,
        certificate_number="LN-2026-ABCDEF",
        student_name="Test Owner",
        status="active",
        pdf_url="/paid.pdf",
        png_url="/paid.png",
    )
    db.add_all([access, cert])
    await db.commit()
    refund = await RefundService.create_refund(
        db,
        purchase_id=purchase.id,
        amount_kopecks=500000,
        reason="Full refund",
        created_by_id=actor.id,
    )
    await db.commit()
    return user, actor, purchase, access, cert, refund


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["active", "suspended", "expired"])
async def test_full_refund_revokes_all_access_states_and_certificate(client, db, state):
    user, actor, purchase, access, cert, refund = await purchase_fixture(db, state)
    await RefundService.update_refund(
        db,
        refund.id,
        status="processed",
        actor_id=actor.id,
        provider_reference="provider-123",
        note=None,
    )
    await db.commit()
    assert access.status == "revoked"
    assert cert.status == "revoked"
    assert cert.revoked_by_id == actor.id
    assert purchase.payment_status == "success"
    assert not await CertificateService._has_course_access(db, user, purchase.course_id)
    status, _, result = await CertificateService.get_status(
        db, user, purchase.course_id
    )
    assert status == "revoked"
    assert result.id == cert.id
    headers = {
        "Authorization": f"Bearer {AuthService.create_tokens(user.id).access_token}"
    }
    response = await client.get(
        f"/api/courses/{purchase.course_id}/certificate", headers=headers
    )
    assert response.json()["status"] == "revoked"
    assert response.json()["certificate"]["pdf_url"] is None
    assert (
        await client.post(
            f"/api/courses/{purchase.course_id}/certificate",
            json={"full_name": "Test Owner"},
            headers=headers,
        )
    ).status_code == 410
    assert (
        await client.get(f"/api/certificates/verify/{cert.certificate_number}")
    ).status_code == 410
    assert (
        await client.get(f"/api/certificates/{cert.certificate_number}/file?format=pdf")
    ).status_code == 410


@pytest.mark.asyncio
async def test_refund_and_restore_race_cannot_revive_access(db):
    _, actor, _, access, cert, refund = await purchase_fixture(db, "suspended")
    actor_id, access_id, certificate_id, refund_id = (
        actor.id,
        access.id,
        cert.id,
        refund.id,
    )

    async def refund_payment():
        async with TestingSessionLocal() as session:
            await RefundService.update_refund(
                session,
                refund_id,
                status="processed",
                actor_id=actor_id,
                provider_reference="race-refund",
                note=None,
            )
            await session.commit()

    async def restore():
        async with TestingSessionLocal() as session:
            current = await session.get(Entitlement, access_id)
            try:
                await AccessService.restore_entitlement(
                    session, current, reason="Concurrent restore"
                )
                await session.commit()
            except ValueError:
                await session.rollback()

    await asyncio.gather(refund_payment(), restore())
    await db.refresh(access)
    await db.refresh(cert)
    assert access.status == "revoked"
    assert cert.id == certificate_id and cert.status == "revoked"


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["extend", "restore"])
async def test_financial_refund_guard_blocks_stale_access_state(db, action):
    _, actor, _, access, _, refund = await purchase_fixture(db)
    refund.status = "processed"
    refund.provider_reference = "historical-refund"
    access.status = "expired" if action == "extend" else "suspended"
    await db.commit()
    with pytest.raises(ValueError, match="refunded"):
        if action == "extend":
            await AccessService.extend_entitlement(
                db, access, days=30, reason="Cannot revive refunded access"
            )
        else:
            await AccessService.restore_entitlement(
                db, access, reason="Cannot revive refunded access"
            )


@pytest.mark.asyncio
async def test_processed_refund_replay_preserves_evidence(db):
    user, actor, _, _, _, refund = await purchase_fixture(db)
    await RefundService.update_refund(
        db,
        refund.id,
        status="processed",
        actor_id=actor.id,
        provider_reference="first-reference",
        note="first-note",
    )
    await db.commit()
    original = refund.processed_at
    await RefundService.update_refund(
        db,
        refund.id,
        status="processed",
        actor_id=user.id,
        provider_reference="overwritten-reference",
        note="overwritten-note",
    )
    assert refund.processed_at == original
    assert refund.processed_by_id == actor.id
    assert refund.provider_reference == "first-reference"
    assert refund.note == "first-note"


@pytest.mark.asyncio
async def test_blank_refund_reference_rejected(db):
    _, actor, _, _, _, refund = await purchase_fixture(db)
    with pytest.raises(RefundError):
        await RefundService.update_refund(
            db,
            refund.id,
            status="processed",
            actor_id=actor.id,
            provider_reference="   ",
            note=None,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind,payment_id", [("manual_grant", "historical"), ("paid", "admin_grant_legacy")]
)
async def test_manual_grant_is_not_refundable_money(db, kind, payment_id):
    _, actor, purchase, _, _, refund = await purchase_fixture(db)
    await db.delete(refund)
    purchase.transaction_kind = kind
    purchase.payment_id = payment_id
    await db.commit()
    with pytest.raises(RefundError, match="paid financial"):
        await RefundService.create_refund(
            db,
            purchase_id=purchase.id,
            amount_kopecks=1,
            reason="Not actual money",
            created_by_id=actor.id,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["active", "expired"])
async def test_manual_entitlement_earns_certificate_after_ordinary_expiry(db, state):
    user, _, purchase, access, _, refund = await purchase_fixture(db)
    access.source_purchase_id = None
    access.source = "manual"
    access.status = state
    access.expires_at = (
        datetime.utcnow() - timedelta(days=1)
        if state == "expired"
        else datetime.utcnow() + timedelta(days=1)
    )
    await db.delete(refund)
    await db.flush()
    await db.delete(purchase)
    await db.commit()
    assert await CertificateService._has_course_access(db, user, access.course_id)


@pytest.mark.asyncio
async def test_rejected_event_replay_remains_rejected(client, db):
    course = Course(
        title="Rejected", price_self=5000, price_support=10000, is_published=True
    )
    db.add(course)
    await db.commit()
    payload = {
        "order_id": "bad-amount",
        "order_num": f"course|{course.id}|self|order",
        "customer_email": "buyer@example.com",
        "sum": "1.00",
        "currency": "rub",
        "payment_status": "success",
    }
    headers = {"Sign": _make_signature(payload, settings.PRODAMUS_SECRET_KEY)}
    first = await client.post("/api/payments/webhook", json=payload, headers=headers)
    second = await client.post("/api/payments/webhook", json=payload, headers=headers)
    assert first.status_code == second.status_code == 422
    assert first.json() == second.json()


@pytest.mark.asyncio
async def test_second_payment_is_durable_incident_without_second_access(
    client, db, monkeypatch
):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(settings, "TELEGRAM_OWNER_CHAT_ID", 123456)
    course = Course(
        title="Double Payment", price_self=5000, price_support=10000, is_published=True
    )
    db.add(course)
    await db.commit()
    link = await client.post(
        "/api/payments/guest-link",
        json={
            "course_id": str(course.id),
            "tariff": "self",
            "customer_email": "buyer@example.com",
            "offer_accepted": True,
            "personal_data_consent": True,
        },
    )
    order_id = link.json()["order_id"]
    for provider_id, attempt in [("one", 1), ("two", 1), ("two", 1), ("two", 2)]:
        payload = {
            "order_id": provider_id,
            "order_num": order_id,
            "customer_email": "buyer@example.com",
            "sum": "5000.00",
            "currency": "rub",
            "payment_status": "success",
            "attempt": attempt,
        }
        response = await client.post(
            "/api/payments/webhook",
            json=payload,
            headers={"Sign": _make_signature(payload, settings.PRODAMUS_SECRET_KEY)},
        )
        assert response.status_code == 200, response.text
    assert await db.scalar(select(func.count(Purchase.id))) == 1
    assert await db.scalar(select(func.count(Entitlement.id))) == 1
    incidents = (
        await db.scalars(
            select(PaymentEvent).where(
                PaymentEvent.processing_status == "financial_incident"
            )
        )
    ).all()
    assert len(incidents) == 1
    assert incidents[0].external_event_id == "two"
    assert incidents[0].amount_kopecks == 500000
    assert (
        await db.scalar(
            select(func.count(OutboxMessage.id)).where(
                OutboxMessage.kind == "owner_payment_incident"
            )
        )
        == 1
    )


@pytest.mark.asyncio
async def test_concurrent_same_payment_callbacks_do_not_create_incident(
    client, db, monkeypatch
):
    from sqlalchemy.ext.asyncio import AsyncSession

    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(settings, "TELEGRAM_OWNER_CHAT_ID", 123456)
    course = Course(
        title="Concurrent Payment",
        price_self=5000,
        price_support=10000,
        is_published=True,
    )
    db.add(course)
    await db.commit()
    link = await client.post(
        "/api/payments/guest-link",
        json={
            "course_id": str(course.id),
            "tariff": "self",
            "customer_email": "buyer@example.com",
            "offer_accepted": True,
            "personal_data_consent": True,
        },
    )
    assert link.status_code == 200
    barrier = asyncio.Barrier(2)
    execute = AsyncSession.execute

    async def execute_after_both_initial_checks(session, statement, *args, **kwargs):
        result = await execute(session, statement, *args, **kwargs)
        if "WHERE purchases.payment_id =" in str(statement):
            await asyncio.wait_for(barrier.wait(), timeout=5)
        return result

    monkeypatch.setattr(AsyncSession, "execute", execute_after_both_initial_checks)

    async def notify(attempt):
        payload = {
            "order_id": "same-provider-payment",
            "order_num": link.json()["order_id"],
            "customer_email": "buyer@example.com",
            "sum": "5000.00",
            "currency": "rub",
            "payment_status": "success",
            "attempt": attempt,
        }
        return await client.post(
            "/api/payments/webhook",
            json=payload,
            headers={"Sign": _make_signature(payload, settings.PRODAMUS_SECRET_KEY)},
        )

    responses = await asyncio.gather(notify(1), notify(2), return_exceptions=True)
    assert all(not isinstance(response, BaseException) for response in responses), (
        responses
    )
    assert [response.status_code for response in responses] == [200, 200]
    assert await db.scalar(select(func.count(Purchase.id))) == 1
    assert await db.scalar(select(func.count(Entitlement.id))) == 1
    assert (
        await db.scalar(
            select(func.count(PaymentEvent.id)).where(
                PaymentEvent.processing_status == "financial_incident"
            )
        )
        == 0
    )
    assert (
        await db.scalar(
            select(func.count(OutboxMessage.id)).where(
                OutboxMessage.kind == "owner_payment_incident"
            )
        )
        == 0
    )
    assert sorted(await db.scalars(select(PaymentEvent.processing_status))) == [
        "duplicate",
        "processed",
    ]
