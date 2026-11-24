import json
import logging
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.api.payments as payments_module
import app.services.payment_event_service as payment_event_module
from app.core.config import settings
from app.core.database import async_session_maker as app_session_maker
from app.core.security import get_password_hash
from app.models.analytics_event import AnalyticsEvent
from app.models.certificate import Certificate
from app.models.course import Course
from app.models.entitlement import Entitlement
from app.models.order import Order
from app.models.outbox import OutboxMessage
from app.models.payment_event import PaymentEvent
from app.models.purchase import Purchase
from app.models.user import User
from app.services.access_service import AccessService
from app.services.certificate_service import CertificateService
from app.services.prodamus_service import ProdamusService, _make_signature
from app.services.refund_service import RefundError, RefundService
from app.services.auth_service import AuthService
from conftest import TestingSessionLocal, engine as test_engine
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
@pytest.mark.parametrize(
    ("stored_utm", "expected_utm"),
    [("12345678901", "12345678901"), ("+79991234567", None)],
)
async def test_attribution_stored_on_order_does_not_block_payment_webhook(
    client, db, stored_utm, expected_utm
):
    """Orders created before PII validation may still hold a phone in a UTM label."""
    course = Course(
        title="Attributed", price_self=5000, price_support=10000, is_published=True
    )
    db.add(course)
    await db.flush()
    order = Order(
        course_id=course.id,
        course_title=course.title,
        tariff="self",
        customer_email="attributed-buyer@example.com",
        amount_kopecks=500000,
        currency="RUB",
        access_days=course.access_days,
        status="pending",
        status_token_hash="0" * 64,
        first_utm_content=stored_utm,
    )
    db.add(order)
    await db.commit()
    payload = {
        "order_id": "attributed-payment",
        "order_num": f"order|{order.id}",
        "customer_email": "attributed-buyer@example.com",
        "sum": "5000",
        "currency": "rub",
        "payment_status": "success",
    }
    headers = {"Sign": _make_signature(payload, settings.PRODAMUS_SECRET_KEY)}

    response = await client.post("/api/payments/webhook", json=payload, headers=headers)

    assert response.status_code == 200, response.text
    assert await db.scalar(
        select(func.count(Purchase.id)).where(
            Purchase.payment_id == "attributed-payment"
        )
    ) == 1
    event = await db.scalar(
        select(AnalyticsEvent).where(
            AnalyticsEvent.event_id == "purchase_confirmed:attributed-payment"
        )
    )
    assert event.utm_content == expected_utm


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


# --- Prodamus webhook: locking, missing orders, renewals, ids, statuses, sums ---


@pytest.fixture
def production_sessions(monkeypatch):
    """Point the payment code at sessions configured like the application's.

    conftest gives the payment code a factory with autoflush off, which hides
    lock-order bugs: production flushes pending rows before every query. Each
    session still opens its own PostgreSQL connection (NullPool).
    """
    options = {key: value for key, value in app_session_maker.kw.items() if key != "bind"}
    factory = async_sessionmaker(bind=test_engine, class_=app_session_maker.class_, **options)
    assert factory.kw["autoflush"] is True
    monkeypatch.setattr(payments_module, "async_session_maker", factory)
    monkeypatch.setattr(payment_event_module, "async_session_maker", factory)
    return factory


@pytest.fixture
def owner_chat(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(settings, "TELEGRAM_OWNER_CHAT_ID", 123456)


async def _course_for_sale(db) -> Course:
    course = Course(
        title="Webhook Safety", price_self=5900, price_support=11900, is_published=True
    )
    db.add(course)
    await db.commit()
    return course


async def _pending_order(db, course, email, *, phone=None) -> Order:
    order = Order(
        course_id=course.id,
        course_title=course.title,
        tariff="self",
        customer_email=email,
        customer_phone=phone,
        amount_kopecks=590000,
        currency="RUB",
        access_days=30,
        status="pending",
        status_token_hash="0" * 64,
    )
    db.add(order)
    await db.commit()
    return order


def _notification(order, provider_payment_id, **fields) -> dict:
    return {
        "order_id": provider_payment_id,
        "order_num": f"order|{order.id}",
        "customer_email": order.customer_email,
        "sum": "5900.00",
        "currency": "rub",
        "payment_status": "success",
        **fields,
    }


def _sign(payload: dict) -> str:
    return _make_signature(payload, settings.PRODAMUS_SECRET_KEY)


async def _deliver(client, payload: dict):
    return await client.post(
        "/api/payments/webhook", json=payload, headers={"Sign": _sign(payload)}
    )


async def _count(db, column, *conditions) -> int:
    return await db.scalar(select(func.count(column)).where(*conditions))


def _meet_or_pass(parties: int, timeout: float):
    """Hold each caller until `parties` have arrived, or until `timeout`.

    Unfixed code lets concurrent requests reach the same point together, so
    they all pass at once. When a lock keeps the others out, the first caller
    gives up waiting and continues.
    """
    arrived = 0
    everyone = asyncio.Event()

    async def meet() -> None:
        nonlocal arrived
        arrived += 1
        if arrived >= parties:
            everyone.set()
        try:
            await asyncio.wait_for(everyone.wait(), timeout)
        except asyncio.TimeoutError:
            pass

    return meet


@pytest.mark.asyncio
async def test_concurrent_deliveries_of_one_order_queue_instead_of_deadlocking(
    client, db, monkeypatch, production_sessions
):
    course = await _course_for_sale(db)
    order = await _pending_order(db, course, "queue@example.com")
    barrier = asyncio.Barrier(2)
    execute = AsyncSession.execute
    arrivals = 0

    async def execute_then_wait_for_both(session, statement, *args, **kwargs):
        nonlocal arrivals
        result = await execute(session, statement, *args, **kwargs)
        if "WHERE purchases.payment_id =" in str(statement) and arrivals < 2:
            arrivals += 1
            await asyncio.wait_for(barrier.wait(), timeout=5)
        return result

    monkeypatch.setattr(AsyncSession, "execute", execute_then_wait_for_both)

    responses = await asyncio.gather(
        _deliver(client, _notification(order, "queued-payment", attempt="1")),
        _deliver(client, _notification(order, "queued-payment", attempt="2")),
        return_exceptions=True,
    )

    assert all(not isinstance(response, BaseException) for response in responses), (
        responses
    )
    assert [response.status_code for response in responses] == [200, 200]
    assert await _count(db, Purchase.id) == 1
    assert await _count(db, Entitlement.id) == 1
    assert sorted(await db.scalars(select(PaymentEvent.processing_status))) == [
        "duplicate",
        "processed",
    ]


class _PostgresFailure(Exception):
    def __init__(self, sqlstate: str):
        super().__init__(f"SQLSTATE {sqlstate}")
        self.sqlstate = sqlstate


@pytest.mark.asyncio
@pytest.mark.parametrize("sqlstate", ["40P01", "40001"])
async def test_webhook_retries_deadlock_and_serialization_failure(
    client, db, monkeypatch, sqlstate
):
    course = await _course_for_sale(db)
    order = await _pending_order(db, course, "lock-retry@example.com")
    record_once = payments_module._record_purchase_once
    calls = 0

    async def aborted_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise DBAPIError("SELECT 1", {}, _PostgresFailure(sqlstate))
        return await record_once(*args, **kwargs)

    monkeypatch.setattr(payments_module, "_record_purchase_once", aborted_once)

    response = await _deliver(client, _notification(order, "lock-retry-payment"))

    assert response.status_code == 200, response.text
    assert calls == 2
    assert await _count(db, Purchase.id) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(("sqlstate", "expected_calls"), [("40P01", 2), ("22001", 1)])
async def test_webhook_database_failure_retry_is_bounded(
    client, db, monkeypatch, sqlstate, expected_calls
):
    course = await _course_for_sale(db)
    order = await _pending_order(db, course, "lock-bounded@example.com")
    calls = 0

    async def always_aborted(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise DBAPIError("SELECT 1", {}, _PostgresFailure(sqlstate))

    monkeypatch.setattr(payments_module, "_record_purchase_once", always_aborted)

    with pytest.raises(DBAPIError):
        await _deliver(client, _notification(order, "lock-bounded-payment"))
    assert calls == expected_calls
    assert await _count(db, Purchase.id) == 0


@pytest.mark.asyncio
async def test_signed_webhook_for_missing_order_is_rejected_and_alerted_once(
    client, db, owner_chat, production_sessions
):
    reference = f"order|{uuid.uuid4()}"
    payload = {
        "order_id": "missing-order-payment",
        "order_num": reference,
        "customer_email": "ghost@example.com",
        "sum": "5900.00",
        "currency": "rub",
        "payment_status": "success",
        "attempt": "1",
    }

    first = await _deliver(client, payload)
    replay = await _deliver(client, payload)

    assert first.status_code == replay.status_code == 422
    assert first.json() == replay.json() == {"detail": "Order not found"}
    event = (await db.scalars(select(PaymentEvent))).one()
    assert event.processing_status == "rejected"
    assert event.error_code == "order_not_found"
    assert event.order_id is None
    assert event.order_reference == reference
    assert event.external_event_id == "missing-order-payment"

    next_attempt = await _deliver(client, {**payload, "attempt": "2"})

    assert next_attempt.status_code == 422
    alerts = (
        await db.scalars(
            select(OutboxMessage).where(OutboxMessage.kind == "owner_payment_rejected")
        )
    ).all()
    assert len(alerts) == 1
    assert reference in alerts[0].payload["text"]
    assert await _count(db, Purchase.id) == 0
    assert await _count(db, User.id) == 0


@pytest.mark.asyncio
async def test_concurrent_orders_of_one_buyer_add_both_paid_periods(
    client, db, monkeypatch, production_sessions
):
    course = await _course_for_sale(db)
    buyer = User(
        email="renewal@example.com",
        password_hash="unused",
        email_verified_at=datetime.utcnow(),
        role="student",
    )
    db.add(buyer)
    await db.commit()
    first_order = await _pending_order(db, course, buyer.email)
    second_order = await _pending_order(db, course, buyer.email)
    meet = _meet_or_pass(2, timeout=2)
    read_access = AccessService.get_active_entitlement

    async def read_then_meet(session, user_id, course_id, *, now=None):
        current = await read_access(session, user_id, course_id, now=now)
        await meet()
        return current

    monkeypatch.setattr(AccessService, "get_active_entitlement", staticmethod(read_then_meet))

    responses = await asyncio.gather(
        _deliver(client, _notification(first_order, "renewal-one")),
        _deliver(client, _notification(second_order, "renewal-two")),
        return_exceptions=True,
    )

    assert all(not isinstance(response, BaseException) for response in responses), (
        responses
    )
    assert [response.status_code for response in responses] == [200, 200]
    earlier, later = (
        await db.scalars(
            select(Entitlement)
            .where(Entitlement.user_id == buyer.id)
            .order_by(Entitlement.expires_at)
        )
    ).all()
    assert later.expires_at - earlier.expires_at == timedelta(days=30)


@pytest.mark.asyncio
async def test_concurrent_manual_grants_add_both_periods(
    db, monkeypatch, production_sessions
):
    course = await _course_for_sale(db)
    student = User(
        email="granted@example.com",
        password_hash="unused",
        email_verified_at=datetime.utcnow(),
        role="student",
    )
    operator = User(email="granter@example.com", password_hash="unused", role="admin")
    db.add_all([student, operator])
    await db.commit()
    meet = _meet_or_pass(2, timeout=2)
    read_access = AccessService.get_active_entitlement

    async def read_then_meet(session, user_id, course_id, *, now=None):
        current = await read_access(session, user_id, course_id, now=now)
        await meet()
        return current

    monkeypatch.setattr(AccessService, "get_active_entitlement", staticmethod(read_then_meet))

    async def grant(reason: str) -> None:
        async with production_sessions() as session:
            await AccessService.grant_manual_access(
                session,
                user_id=student.id,
                course_id=course.id,
                tariff="self",
                access_days=30,
                granted_by_id=operator.id,
                reason=reason,
            )
            await session.commit()

    await asyncio.gather(grant("First grant"), grant("Second grant"))

    earlier, later = (
        await db.scalars(
            select(Entitlement)
            .where(Entitlement.user_id == student.id)
            .order_by(Entitlement.expires_at)
        )
    ).all()
    assert later.expires_at - earlier.expires_at == timedelta(days=30)


@pytest.mark.asyncio
async def test_long_provider_payment_id_is_recorded_once(client, db):
    course = await _course_for_sale(db)
    order = await _pending_order(db, course, "long-id@example.com")
    payment_id = "p" * 200
    payload = _notification(order, payment_id, attempt="1")

    async def stored() -> list[int]:
        return [
            await _count(db, Purchase.id),
            await _count(db, Entitlement.id),
            await _count(db, AnalyticsEvent.id),
            await _count(db, OutboxMessage.id),
        ]

    first = await _deliver(client, payload)

    assert first.status_code == 200, first.text
    purchase = await db.scalar(select(Purchase).where(Purchase.payment_id == payment_id))
    assert purchase is not None and purchase.order_id == order.id
    confirmed = (
        await db.scalars(
            select(AnalyticsEvent).where(AnalyticsEvent.event_name == "purchase_confirmed")
        )
    ).all()
    assert len(confirmed) == 1
    assert confirmed[0].order_id == order.id
    assert len(confirmed[0].event_id) <= 128
    after_first = await stored()
    events_after_first = await _count(db, PaymentEvent.id)

    replay = await _deliver(client, payload)
    next_attempt = await _deliver(client, {**payload, "attempt": "2"})

    assert replay.status_code == next_attempt.status_code == 200
    assert await stored() == after_first
    # The identical replay adds nothing; the next attempt adds only its duplicate event.
    assert await _count(db, PaymentEvent.id) == events_after_first + 1
    assert await _count(
        db, PaymentEvent.id, PaymentEvent.processing_status == "duplicate"
    ) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "markers",
    [
        {"payment_status": "success", "status": "failed"},
        {"payment_status": "success", "result": "error"},
        {"payment_status": "order_denied", "status": "success"},
        {"status": "success", "result": "fail"},
    ],
)
async def test_contradictory_status_markers_never_grant_access(
    client, db, owner_chat, markers
):
    course = await _course_for_sale(db)
    order = await _pending_order(db, course, "contradiction@example.com")
    payload = _notification(order, "contradictory-payment")
    del payload["payment_status"]
    payload.update(markers)

    response = await _deliver(client, payload)

    assert response.status_code == 422, response.text
    assert await _count(db, Purchase.id) == 0
    assert await _count(db, Entitlement.id) == 0
    event = (await db.scalars(select(PaymentEvent))).one()
    assert event.processing_status == "rejected"
    assert event.error_code == "contradictory_payment_status"
    assert await _count(
        db, OutboxMessage.id, OutboxMessage.kind == "owner_payment_rejected"
    ) == 1
    await db.refresh(order)
    assert order.status == "pending"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "markers",
    [
        {"payment_status": "success"},
        {"payment_status": "success", "status": "paid"},
        {"payment_status": "SUCCESS", "result": "ok"},
        {"payment_status": "success", "status": "   "},
        {"status": "paid"},
        {"result": "completed"},
    ],
)
async def test_agreeing_or_single_status_markers_are_still_accepted(client, db, markers):
    course = await _course_for_sale(db)
    order = await _pending_order(db, course, "agreeing@example.com")
    payload = _notification(order, "agreeing-payment")
    del payload["payment_status"]
    payload.update(markers)

    response = await _deliver(client, payload)

    assert response.status_code == 200, response.text
    assert await _count(db, Purchase.id) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("paid_sum", "paid_kopecks", "event_kopecks"),
    [
        ("5900.00", 590000, 590000),
        ("5900,00", 590000, 590000),
        ("5899.99", 589999, 589999),
        ("5900.02", 590002, 590002),
        ("5900.03", None, 590003),
        ("5899.97", None, 589997),
        ("nan", None, None),
        ("-1", None, None),
        ("1e400", None, None),
        ("Infinity", None, None),
    ],
)
async def test_paid_sum_is_parsed_exactly_within_two_kopecks(
    client, db, paid_sum, paid_kopecks, event_kopecks
):
    course = await _course_for_sale(db)
    order = await _pending_order(db, course, "sum@example.com")

    response = await _deliver(client, _notification(order, "sum-payment", sum=paid_sum))

    purchase = await db.scalar(select(Purchase))
    event = (await db.scalars(select(PaymentEvent))).one()
    assert event.amount_kopecks == event_kopecks
    if paid_kopecks is None:
        assert response.status_code == 422, response.text
        assert response.json() == {"detail": "Amount mismatch"}
        assert purchase is None
        assert event.processing_status == "rejected"
    else:
        assert response.status_code == 200, response.text
        assert purchase.amount_kopecks == paid_kopecks
        assert event.processing_status == "processed"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("5900.00", 590000),
        ("5900,00", 590000),
        (" 5899.99 ", 589999),
        (5900, 590000),
        (5899.99, 589999),
        ("0.29", 29),
        ("1.005", 101),
        ("21474836.47", 2147483647),
        ("21474836.48", None),
        ("nan", None),
        ("sNaN", None),
        ("-1", None),
        ("-0.01", None),
        ("1e400", None),
        ("inf", None),
        ("", None),
        (None, None),
        ("5 900", None),
    ],
)
def test_parse_amount_kopecks(raw, expected):
    from app.services.payment_event_service import parse_amount_kopecks

    assert parse_amount_kopecks(raw) == expected


@pytest.mark.asyncio
async def test_guest_payment_links_order_and_keeps_checkout_phone(client, db):
    course = await _course_for_sale(db)
    order = await _pending_order(db, course, "guest-phone@example.com", phone="+79990001122")

    response = await _deliver(client, _notification(order, "guest-phone-payment"))

    assert response.status_code == 200, response.text
    buyer = await db.scalar(select(User).where(User.email == "guest-phone@example.com"))
    await db.refresh(order)
    assert order.user_id == buyer.id
    purchase = await db.scalar(select(Purchase).where(Purchase.order_id == order.id))
    assert purchase.customer_phone == "+79990001122"
    # The account was born from this payment, so it takes the checkout phone.
    assert buyer.phone == "+79990001122"


@pytest.mark.asyncio
async def test_guest_payment_does_not_write_phone_into_existing_account(client, db):
    course = await _course_for_sale(db)
    account = User(
        email="account-owner@example.com",
        password_hash="unused",
        email_verified_at=datetime.utcnow(),
        role="student",
    )
    db.add(account)
    await db.commit()
    order = await _pending_order(db, course, account.email, phone="+79990001122")

    response = await _deliver(
        client,
        _notification(order, "gift-payment", customer_phone="+79995556677"),
    )

    assert response.status_code == 200, response.text
    await db.refresh(account)
    await db.refresh(order)
    assert account.phone is None
    assert order.user_id == account.id
    purchase = await db.scalar(select(Purchase).where(Purchase.order_id == order.id))
    assert purchase.customer_phone == "+79995556677"


WEBHOOK_BODY_LIMIT = 64 * 1024


def _signed_body_of_size(order, size: int) -> tuple[bytes, dict]:
    payload = _notification(order, "sized-payment", padding="")
    base = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload["padding"] = "x" * (size - len(base))
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    assert len(body) == size
    return body, {"Sign": _sign(payload), "Content-Type": "application/json"}


@pytest.mark.asyncio
async def test_webhook_body_at_size_limit_is_processed(client, db):
    course = await _course_for_sale(db)
    order = await _pending_order(db, course, "sized@example.com")
    body, headers = _signed_body_of_size(order, WEBHOOK_BODY_LIMIT)

    response = await client.post("/api/payments/webhook", content=body, headers=headers)

    assert response.status_code == 200, response.text
    assert await _count(db, Purchase.id) == 1


@pytest.mark.asyncio
async def test_webhook_body_over_size_limit_is_rejected_before_parsing(
    client, db, monkeypatch
):
    course = await _course_for_sale(db)
    order = await _pending_order(db, course, "oversized@example.com")
    body, headers = _signed_body_of_size(order, WEBHOOK_BODY_LIMIT + 1)

    def must_not_verify(*args, **kwargs):
        raise AssertionError("an oversized body must be rejected before verification")

    monkeypatch.setattr(ProdamusService, "verify_signature", staticmethod(must_not_verify))

    async def in_chunks():
        # No Content-Length: the limit must count the bytes actually received.
        yield body[: WEBHOOK_BODY_LIMIT // 2]
        yield body[WEBHOOK_BODY_LIMIT // 2 :]

    declared = await client.post("/api/payments/webhook", content=body, headers=headers)
    streamed = await client.post(
        "/api/payments/webhook", content=in_chunks(), headers=headers
    )
    unsigned = await client.post(
        "/api/payments/webhook",
        content=body,
        headers={"Content-Type": "application/json"},
    )

    assert declared.status_code == streamed.status_code == 413
    assert unsigned.status_code == 400
    assert unsigned.json() == {"detail": "Missing signature"}
    assert await _count(db, PaymentEvent.id) == 0
    assert await _count(db, Purchase.id) == 0


@pytest.mark.asyncio
async def test_invalid_webhook_signature_log_names_the_request_not_the_signature(
    client, db, caplog
):
    course = await _course_for_sale(db)
    order = await _pending_order(db, course, "forged@example.com")
    forged = "0123456789abcdef" * 4
    expected = _sign(_notification(order, "forged-payment"))

    with caplog.at_level(logging.WARNING, logger="app.services.prodamus_service"):
        response = await client.post(
            "/api/payments/webhook",
            json=_notification(order, "forged-payment"),
            headers={"Sign": forged, "X-Correlation-ID": "webhook-corr-7"},
        )

    assert response.status_code == 400
    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "signature mismatch" in message and "webhook-corr-7" in message
        for message in messages
    ), messages
    assert not any(
        signature[:6] in message for signature in (forged, expected) for message in messages
    )
