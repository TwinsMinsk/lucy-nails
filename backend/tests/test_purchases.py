import uuid
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.payments import _build_prodamus_order_id, parse_checkout_order_id
from app.core.config import Settings
from app.core.security import get_password_hash
from app.models.course import Course
from app.models.entitlement import Entitlement
from app.models.payment_event import PaymentEvent
from app.models.purchase import Purchase
from app.models.user import User
from app.services.prodamus_service import _make_signature


async def _published_course(db: AsyncSession, title: str) -> Course:
    course = Course(title=title, price_self=5000, price_support=10000, is_published=True)
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


def _signed_payload(payload: dict) -> tuple[dict, dict]:
    return payload, {"Sign": _make_signature(payload, "test-prodamus-hmac-secret-key-for-ci")}


async def _create_user(db: AsyncSession, email: str) -> User:
    user = User(
        email=email,
        password_hash=get_password_hash("password123"),
        role="student",
    )
    db.add(user)
    await db.flush()
    return user


@pytest.mark.asyncio
async def test_parse_checkout_order_id():
    cid = uuid.uuid4()
    raw = f"course|{cid}|support|deadbeef"
    parsed = parse_checkout_order_id(raw)
    assert parsed is not None
    assert parsed[0] == cid
    assert parsed[1] == "support"
    assert parse_checkout_order_id("invalid") is None


@pytest.mark.asyncio
async def test_create_and_list_purchases(client: AsyncClient, db: AsyncSession):
    course = Course(
        title="Buy Me",
        price_self=5000,
        price_support=10000,
        is_published=True,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)

    await client.post(
        "/api/auth/register",
        json={"email": "buyer@t.com", "password": "password123", "password_confirm": "password123"},
    )
    login = await client.post("/api/auth/login", json={"email": "buyer@t.com", "password": "password123"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # Bearer-only auth: drop login cookies so the CSRF middleware does not require
    # an X-CSRF-Token header on the unsafe POST below.
    client.cookies.clear()

    res_create = await client.post(
        "/api/purchases/create",
        json={"course_id": str(course.id), "tariff": "self"},
        headers=headers,
    )

    assert res_create.status_code == 200
    data = res_create.json()
    assert "payment_url" in data
    assert str(course.id) in data["payment_url"] or "pay" in data["payment_url"]
    assert data["tariff"] == "self"
    assert data["course_id"] == str(course.id)

    res_list = await client.get("/api/purchases/my", headers=headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) == 0


@pytest.mark.asyncio
async def test_prodamus_webhook_uses_order_id_as_stable_fallback_payment_id(
    client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_send_credentials(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.email_service.EmailService.send_credentials", fake_send_credentials)

    course = Course(
        title="Webhook Course",
        price_self=5000,
        price_support=10000,
        is_published=True,
    )
    db.add(course)
    await _create_user(db, "webhook-buyer@example.com")
    await db.commit()
    await db.refresh(course)

    order_id = _build_prodamus_order_id(course.id, "self")
    payload, headers = _signed_payload(
        {
            "order_id": order_id,
            "customer_email": "webhook-buyer@example.com",
            "customer_phone": "+79990000000",
            "sum": "5000",
            "currency": "rub",
            "payment_status": "success",
        }
    )

    first = await client.post("/api/payments/webhook", json=payload, headers=headers)
    second = await client.post("/api/payments/webhook", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200

    result = await db.execute(select(Purchase))
    purchase = result.scalar_one()
    assert purchase.payment_id == f"order_id:{order_id}"
    assert purchase.payment_status == "success"
    assert purchase.amount_kopecks == 500000
    assert purchase.customer_phone == "+79990000000"

    count_result = await db.execute(select(func.count(Purchase.id)))
    assert count_result.scalar_one() == 1


@pytest.mark.asyncio
async def test_prodamus_webhook_keeps_repeat_payments_idempotent(
    client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_send_credentials(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.email_service.EmailService.send_credentials", fake_send_credentials)

    course = Course(
        title="Repeat Payment Course",
        price_self=5000,
        price_support=10000,
        is_published=True,
    )
    db.add(course)
    await _create_user(db, "repeat-buyer@example.com")
    await db.commit()
    await db.refresh(course)

    payload_one, headers_one = _signed_payload(
        {
            "order_id": _build_prodamus_order_id(course.id, "self"),
            "order_num": "payment-one",
            "customer_email": "repeat-buyer@example.com",
            "sum": "5000",
            "currency": "rub",
            "payment_status": "success",
        }
    )
    payload_two, headers_two = _signed_payload(
        {
            "order_id": _build_prodamus_order_id(course.id, "support"),
            "order_num": "payment-two",
            "customer_email": "repeat-buyer@example.com",
            "sum": "10000",
            "currency": "rub",
            "payment_status": "success",
        }
    )

    first = await client.post("/api/payments/webhook", json=payload_one, headers=headers_one)
    second = await client.post("/api/payments/webhook", json=payload_two, headers=headers_two)
    first_retry = await client.post("/api/payments/webhook", json=payload_one, headers=headers_one)
    second_retry = await client.post("/api/payments/webhook", json=payload_two, headers=headers_two)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first_retry.status_code == 200
    assert second_retry.status_code == 200

    count_result = await db.execute(select(func.count(Purchase.id)))
    assert count_result.scalar_one() == 2

    purchases_result = await db.execute(select(Purchase).order_by(Purchase.payment_id))
    purchases = purchases_result.scalars().all()
    assert [purchase.payment_id for purchase in purchases] == ["payment-one", "payment-two"]
    assert [purchase.tariff for purchase in purchases] == ["self", "support"]
    event_count = await db.scalar(select(func.count(PaymentEvent.id)))
    assert event_count == 2


@pytest.mark.asyncio
async def test_prodamus_webhook_rejects_non_success_status(client: AsyncClient, db: AsyncSession):
    course = Course(
        title="Webhook Failed Course",
        price_self=5000,
        price_support=10000,
        is_published=True,
    )
    db.add(course)
    await _create_user(db, "failed-webhook@example.com")
    await db.commit()
    await db.refresh(course)

    payload, headers = _signed_payload(
        {
            "order_id": _build_prodamus_order_id(course.id, "self"),
            "customer_email": "failed-webhook@example.com",
            "sum": "5000",
            "currency": "rub",
            "payment_status": "failed",
        }
    )

    response = await client.post("/api/payments/webhook", json=payload, headers=headers)

    assert response.status_code == 422
    event = (await db.execute(select(PaymentEvent))).scalar_one()
    assert event.processing_status == "ignored"
    assert event.error_code == "payment_not_successful"
    assert "customer_email" not in event.sanitized_payload
    assert "failed-webhook@example.com" not in str(event.sanitized_payload)


@pytest.mark.asyncio
async def test_prodamus_webhook_rejects_non_rub_currency(client: AsyncClient, db: AsyncSession):
    course = Course(
        title="Webhook Currency Course",
        price_self=5000,
        price_support=10000,
        is_published=True,
    )
    db.add(course)
    await _create_user(db, "currency-webhook@example.com")
    await db.commit()
    await db.refresh(course)

    payload, headers = _signed_payload(
        {
            "order_id": _build_prodamus_order_id(course.id, "self"),
            "customer_email": "currency-webhook@example.com",
            "sum": "5000",
            "currency": "usd",
            "payment_status": "success",
        }
    )

    response = await client.post("/api/payments/webhook", json=payload, headers=headers)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_webhook_creates_user_and_queues_single_use_activation(
    client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    sent: list[tuple[str, str]] = []

    async def capture_send(email: str, password: str) -> None:
        sent.append((email, password))

    monkeypatch.setattr("app.services.email_service.EmailService.send_credentials", capture_send)

    course = Course(
        title="Webhook Creates User Course",
        price_self=5000,
        price_support=10000,
        is_published=True,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)

    order_id = _build_prodamus_order_id(course.id, "self")
    payload, wh_headers = _signed_payload(
        {
            "order_id": order_id,
            "customer_email": "brand-new@example.com",
            "customer_phone": "+79991112233",
            "sum": "5000",
            "currency": "rub",
            "payment_status": "success",
        }
    )

    response = await client.post("/api/payments/webhook", json=payload, headers=wh_headers)
    assert response.status_code == 200

    user_result = await db.execute(select(User).where(User.email == "brand-new@example.com"))
    user = user_result.scalar_one()
    assert user.phone == "+79991112233"
    assert sent == []

    outbox_result = await db.execute(
        text(
            "SELECT kind, recipient, payload FROM outbox_messages "
            "WHERE recipient = :recipient"
        ),
        {"recipient": "brand-new@example.com"},
    )
    outbox = outbox_result.mappings().one()
    assert outbox["kind"] == "account_activation"
    activation_url = outbox["payload"]["activation_url"]
    activation_token = parse_qs(urlparse(activation_url).query)["token"][0]

    activated = await client.post(
        "/api/auth/activate",
        json={"token": activation_token, "new_password": "new-secure-password"},
    )
    assert activated.status_code == 200
    replay = await client.post(
        "/api/auth/activate",
        json={"token": activation_token, "new_password": "another-password"},
    )
    assert replay.status_code == 400
    login = await client.post(
        "/api/auth/login",
        json={"email": "brand-new@example.com", "password": "new-secure-password"},
    )
    assert login.status_code == 200

    purchase_result = await db.execute(select(Purchase).where(Purchase.payment_id == f"order_id:{order_id}"))
    purchase = purchase_result.scalar_one()
    assert purchase.user_id == user.id
    assert purchase.payment_status == "success"


@pytest.mark.asyncio
async def test_webhook_existing_user_queues_access_notification(
    client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    sent: list[tuple[object, ...]] = []

    async def capture_send(*args: object, **_kwargs: object) -> None:
        sent.append(args)

    monkeypatch.setattr("app.services.email_service.EmailService.send_credentials", capture_send)

    course = Course(
        title="Webhook Existing User Course",
        price_self=5000,
        price_support=10000,
        is_published=True,
    )
    db.add(course)
    await _create_user(db, "existing-webhook@example.com")
    await db.commit()
    await db.refresh(course)

    order_id = _build_prodamus_order_id(course.id, "self")
    payload, wh_headers = _signed_payload(
        {
            "order_id": order_id,
            "customer_email": "existing-webhook@example.com",
            "sum": "5000",
            "currency": "rub",
            "payment_status": "success",
        }
    )

    response = await client.post("/api/payments/webhook", json=payload, headers=wh_headers)
    assert response.status_code == 200
    assert sent == []

    outbox_table = await db.scalar(text("SELECT to_regclass('public.outbox_messages')"))
    assert outbox_table == "outbox_messages"
    outbox_result = await db.execute(
        text(
            "SELECT kind, recipient FROM outbox_messages "
            "WHERE recipient = :recipient"
        ),
        {"recipient": "existing-webhook@example.com"},
    )
    outbox = outbox_result.mappings().one()
    assert outbox["kind"] == "access_granted"

    purchase_result = await db.execute(
        select(Purchase).where(Purchase.payment_id == f"order_id:{order_id}")
    )
    assert purchase_result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_successful_webhook_creates_purchase_entitlement(
    client: AsyncClient,
    db: AsyncSession,
):
    course = await _published_course(db, "Entitled Course")
    await _create_user(db, "entitled-buyer@example.com")
    await db.commit()

    order_id = _build_prodamus_order_id(course.id, "support")
    payload, headers = _signed_payload(
        {
            "order_id": order_id,
            "customer_email": "entitled-buyer@example.com",
            "sum": "10000",
            "currency": "rub",
            "payment_status": "success",
        }
    )

    response = await client.post("/api/payments/webhook", json=payload, headers=headers)
    assert response.status_code == 200, response.text

    purchase = (
        await db.execute(select(Purchase).where(Purchase.payment_id == f"order_id:{order_id}"))
    ).scalar_one()
    entitlement = (
        await db.execute(
            select(Entitlement).where(Entitlement.source_purchase_id == purchase.id)
        )
    ).scalar_one()
    assert entitlement.user_id == purchase.user_id
    assert entitlement.course_id == purchase.course_id
    assert entitlement.source == "purchase"
    assert entitlement.status == "active"
    assert entitlement.tariff == "support"
    assert entitlement.expires_at == purchase.expires_at


@pytest.mark.asyncio
async def test_admin_grant_creates_entitlement_without_fake_purchase(
    client: AsyncClient,
    db: AsyncSession,
):
    admin = User(
        email="access-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    student = await _create_user(db, "manual-access@example.com")
    course = await _published_course(db, "Manual Access Course")
    course.access_days = 30
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    await db.refresh(student)

    login = await client.post(
        "/api/auth/login",
        json={"email": admin.email, "password": "adminpass1"},
    )
    token = login.json()["access_token"]
    client.cookies.clear()

    response = await client.post(
        "/api/admin/grant-access",
        json={
            "user_id": str(student.id),
            "course_id": str(course.id),
            "tariff": "self",
            "reason": "Доступ для участника тестовой группы",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["entitlement_id"]
    assert "purchase_id" not in body

    purchases_count = (
        await db.execute(select(func.count(Purchase.id)).where(Purchase.user_id == student.id))
    ).scalar_one()
    assert purchases_count == 0

    entitlement = await db.get(Entitlement, uuid.UUID(body["entitlement_id"]))
    assert entitlement is not None
    assert entitlement.source == "manual"
    assert entitlement.granted_by_id == admin.id
    assert entitlement.reason == "Доступ для участника тестовой группы"
    assert timedelta(days=29, hours=23) < entitlement.expires_at - entitlement.starts_at <= timedelta(days=30)

    student_login = await client.post(
        "/api/auth/login",
        json={"email": student.email, "password": "password123"},
    )
    student_token = student_login.json()["access_token"]
    client.cookies.clear()
    courses_response = await client.get(
        "/api/purchases/my",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert courses_response.status_code == 200, courses_response.text
    assert [item["id"] for item in courses_response.json()] == [str(course.id)]

    revoke_response = await client.post(
        "/api/admin/revoke-entitlement",
        json={
            "entitlement_id": body["entitlement_id"],
            "reason": "Тестовый доступ завершён",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert revoke_response.status_code == 200, revoke_response.text
    await db.refresh(entitlement)
    assert entitlement.status == "revoked"
    assert entitlement.reason == "Тестовый доступ завершён"

    revoked_courses_response = await client.get(
        "/api/purchases/my",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert revoked_courses_response.status_code == 200
    assert revoked_courses_response.json() == []

@pytest.mark.asyncio
async def test_webhook_retry_does_not_duplicate_outbox_message(
    client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    async def capture_send(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr("app.services.email_service.EmailService.send_credentials", capture_send)

    course = Course(
        title="Webhook Email Fail Course",
        price_self=5000,
        price_support=10000,
        is_published=True,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)

    order_id = _build_prodamus_order_id(course.id, "self")
    payload, wh_headers = _signed_payload(
        {
            "order_id": order_id,
            "customer_email": "email-fail@example.com",
            "sum": "5000",
            "currency": "rub",
            "payment_status": "success",
        }
    )

    first = await client.post("/api/payments/webhook", json=payload, headers=wh_headers)
    second = await client.post("/api/payments/webhook", json=payload, headers=wh_headers)

    assert first.status_code == 200
    assert second.status_code == 200

    count_result = await db.execute(select(func.count(Purchase.id)))
    assert count_result.scalar_one() == 1
    outbox_table = await db.scalar(text("SELECT to_regclass('public.outbox_messages')"))
    assert outbox_table == "outbox_messages"
    outbox_count = await db.execute(
        text(
            "SELECT count(*) FROM outbox_messages "
            "WHERE recipient = :recipient"
        ),
        {"recipient": "email-fail@example.com"},
    )
    assert outbox_count.scalar_one() == 1


@pytest.mark.asyncio
async def test_guest_payment_link_returns_url(client: AsyncClient, db: AsyncSession):
    course = Course(
        title="Guest Link Course",
        price_self=5000,
        price_support=10000,
        is_published=True,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)

    response = await client.post(
        "/api/payments/guest-link",
        json={
            "course_id": str(course.id),
            "tariff": "self",
            "customer_email": "guest@example.com",
            "customer_phone": "+79990001122",
        },
    )

    assert response.status_code == 200
    response_data = response.json()
    url = response_data["url"]
    assert "signature=" in url
    assert ("guest%40example.com" in url) or ("guest@example.com" in url)
    success_url = parse_qs(urlparse(url).query)["urlSuccess"][0]
    success_query = parse_qs(urlparse(success_url).query)
    assert success_query["order_id"] == [response_data["order_id"]]
    assert success_query["token"] == [response_data["status_token"]]


@pytest.mark.asyncio
async def test_guest_checkout_is_blocked_by_kill_switch(
    client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    course = await _published_course(db, "Disabled Checkout Course")
    monkeypatch.setenv("CHECKOUT_ENABLED", "false")
    monkeypatch.setattr("app.api.payments.settings", Settings())

    response = await client.post(
        "/api/payments/guest-link",
        json={
            "course_id": str(course.id),
            "tariff": "self",
            "customer_email": "disabled-checkout@example.com",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Checkout is temporarily unavailable"


@pytest.mark.asyncio
async def test_checkout_order_keeps_original_price_when_course_price_changes(
    client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_send_credentials(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr("app.services.email_service.EmailService.send_credentials", fake_send_credentials)
    course = await _published_course(db, "Immutable Checkout Price")
    course.access_days = 45
    await db.commit()

    checkout = await client.post(
        "/api/payments/guest-link",
        json={
            "course_id": str(course.id),
            "tariff": "self",
            "customer_email": "snapshot-buyer@example.com",
        },
    )
    assert checkout.status_code == 200
    checkout_data = checkout.json()
    order_id = checkout_data["order_id"]
    status_token = checkout_data["status_token"]

    pending = await client.get(
        f"/api/payments/orders/{order_id}/status",
        params={"token": status_token},
    )
    assert pending.status_code == 200
    assert pending.json()["status"] == "pending"

    course.price_self = 7000
    course.access_days = 5
    await db.commit()

    payload, headers = _signed_payload(
        {
            "order_id": order_id,
            "customer_email": "snapshot-buyer@example.com",
            "sum": "5000",
            "currency": "rub",
            "payment_status": "success",
        }
    )
    webhook = await client.post("/api/payments/webhook", json=payload, headers=headers)

    assert webhook.status_code == 200
    paid = await client.get(
        f"/api/payments/orders/{order_id}/status",
        params={"token": status_token},
    )
    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"

    purchase_result = await db.execute(
        select(Purchase).where(Purchase.user.has(email="snapshot-buyer@example.com"))
    )
    purchase = purchase_result.scalar_one()
    assert purchase.amount_kopecks == 500000
    assert timedelta(days=44, hours=23) < purchase.expires_at - purchase.paid_at <= timedelta(days=45)


@pytest.mark.asyncio
async def test_payment_link_requires_authenticated_user(client: AsyncClient, db: AsyncSession):
    course = Course(
        title="Protected Checkout Course",
        price_self=5000,
        price_support=10000,
        is_published=True,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)

    response = await client.post(
        "/api/payments/link",
        json={"course_id": str(course.id), "tariff": "self"},
    )

    assert response.status_code == 401


# --- Webhook hardening (audit round 2: B1 status, B2 race, signature/amount) ---


@pytest.mark.asyncio
async def test_webhook_missing_signature_rejected(client: AsyncClient, db: AsyncSession):
    course = await _published_course(db, "No Sign Course")
    payload = {
        "order_id": _build_prodamus_order_id(course.id, "self"),
        "customer_email": "nosign@example.com",
        "sum": "5000",
        "currency": "rub",
        "payment_status": "success",
    }
    r = await client.post("/api/payments/webhook", json=payload)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_webhook_invalid_signature_rejected(client: AsyncClient, db: AsyncSession):
    course = await _published_course(db, "Bad Sign Course")
    payload = {
        "order_id": _build_prodamus_order_id(course.id, "self"),
        "customer_email": "badsign@example.com",
        "sum": "5000",
        "currency": "rub",
        "payment_status": "success",
    }
    r = await client.post("/api/payments/webhook", json=payload, headers={"Sign": "deadbeef"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_webhook_amount_mismatch_rejected(client: AsyncClient, db: AsyncSession):
    course = await _published_course(db, "Amount Mismatch Course")
    payload, headers = _signed_payload(
        {
            "order_id": _build_prodamus_order_id(course.id, "self"),
            "customer_email": "mismatch@example.com",
            "sum": "9999",  # course.price_self is 5000
            "currency": "rub",
            "payment_status": "success",
        }
    )
    r = await client.post("/api/payments/webhook", json=payload, headers=headers)
    assert r.status_code == 422

    count = await db.execute(select(func.count(Purchase.id)))
    assert count.scalar_one() == 0
    event = (await db.execute(select(PaymentEvent))).scalar_one()
    assert event.processing_status == "rejected"
    assert event.error_code == "amount_mismatch"


@pytest.mark.asyncio
async def test_webhook_empty_status_rejected(client: AsyncClient, db: AsyncSession):
    """A signed webhook with no status marker must NOT be treated as success."""
    course = await _published_course(db, "Empty Status Course")
    payload, headers = _signed_payload(
        {
            "order_id": _build_prodamus_order_id(course.id, "self"),
            "customer_email": "empty@example.com",
            "sum": "5000",
            "currency": "rub",
        }
    )
    r = await client.post("/api/payments/webhook", json=payload, headers=headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_webhook_two_payments_same_new_email_keeps_both(
    client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    """Two distinct payments for the same brand-new email create two purchases."""
    async def fake_send_credentials(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.email_service.EmailService.send_credentials", fake_send_credentials)

    course = await _published_course(db, "Two Payments Course")

    p1, h1 = _signed_payload(
        {
            "order_id": _build_prodamus_order_id(course.id, "self"),
            "order_num": "race-one",
            "customer_email": "racebuyer@example.com",
            "sum": "5000",
            "currency": "rub",
            "payment_status": "success",
        }
    )
    p2, h2 = _signed_payload(
        {
            "order_id": _build_prodamus_order_id(course.id, "support"),
            "order_num": "race-two",
            "customer_email": "racebuyer@example.com",
            "sum": "10000",
            "currency": "rub",
            "payment_status": "success",
        }
    )

    r1 = await client.post("/api/payments/webhook", json=p1, headers=h1)
    r2 = await client.post("/api/payments/webhook", json=p2, headers=h2)
    assert r1.status_code == 200
    assert r2.status_code == 200

    purchases = await db.execute(select(func.count(Purchase.id)))
    assert purchases.scalar_one() == 2
    users = await db.execute(select(func.count(User.id)).where(User.email == "racebuyer@example.com"))
    assert users.scalar_one() == 1


@pytest.mark.asyncio
async def test_webhook_retries_on_integrity_error(
    client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    """A transient IntegrityError (new-user email race) is retried, not swallowed."""
    async def fake_send_credentials(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.email_service.EmailService.send_credentials", fake_send_credentials)

    course = await _published_course(db, "Retry Course")

    import app.api.payments as payments_module

    real_get_or_create = payments_module._get_or_create_user
    calls = {"n": 0}

    async def flaky(session, email, phone):
        calls["n"] += 1
        if calls["n"] == 1:
            raise IntegrityError("INSERT users", {}, Exception("duplicate email"))
        return await real_get_or_create(session, email, phone)

    monkeypatch.setattr("app.api.payments._get_or_create_user", flaky)

    order_id = _build_prodamus_order_id(course.id, "self")
    payload, headers = _signed_payload(
        {
            "order_id": order_id,
            "customer_email": "retry@example.com",
            "sum": "5000",
            "currency": "rub",
            "payment_status": "success",
        }
    )

    r = await client.post("/api/payments/webhook", json=payload, headers=headers)
    assert r.status_code == 200
    assert calls["n"] == 2

    purchase = await db.execute(select(Purchase).where(Purchase.payment_id == f"order_id:{order_id}"))
    assert purchase.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_admin_revoke_access(client: AsyncClient, db: AsyncSession):
    admin = User(
        email="admin-revoke@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    student = await _create_user(db, "revoke-student@example.com")
    course = await _published_course(db, "Revoke Course")
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    await db.refresh(student)

    now = datetime.utcnow()
    purchase = Purchase(
        user_id=student.id,
        course_id=course.id,
        tariff="self",
        amount_kopecks=500000,
        payment_id="admin-revoke-test",
        payment_status="success",
        paid_at=now,
        expires_at=now + timedelta(days=30),
    )
    db.add(purchase)
    await db.commit()
    await db.refresh(purchase)

    login = await client.post(
        "/api/auth/login", json={"email": "admin-revoke@example.com", "password": "adminpass1"}
    )
    token = login.json()["access_token"]
    client.cookies.clear()

    r = await client.post(
        "/api/admin/revoke-access",
        json={"purchase_id": str(purchase.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text

    await db.refresh(purchase)
    assert purchase.payment_status == "failed"
    assert purchase.expires_at <= datetime.utcnow()
