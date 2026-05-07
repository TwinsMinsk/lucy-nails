import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.payments import _build_prodamus_order_id, parse_checkout_order_id
from app.core.security import get_password_hash, verify_password
from app.models.course import Course
from app.models.purchase import Purchase
from app.models.user import User
from app.services.prodamus_service import _make_signature


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

    monkeypatch.setattr("app.api.payments.EmailService.send_credentials", fake_send_credentials)

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

    monkeypatch.setattr("app.api.payments.EmailService.send_credentials", fake_send_credentials)

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
async def test_webhook_creates_user_and_sends_credentials(
    client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    sent: list[tuple[str, str]] = []

    async def capture_send(email: str, password: str) -> None:
        sent.append((email, password))

    monkeypatch.setattr("app.api.payments.EmailService.send_credentials", capture_send)

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
    assert len(sent) == 1
    assert sent[0][0] == "brand-new@example.com"
    assert len(sent[0][1]) >= 8
    assert verify_password(sent[0][1], user.password_hash)

    purchase_result = await db.execute(select(Purchase).where(Purchase.payment_id == f"order_id:{order_id}"))
    purchase = purchase_result.scalar_one()
    assert purchase.user_id == user.id
    assert purchase.payment_status == "success"


@pytest.mark.asyncio
async def test_webhook_existing_user_does_not_resend_credentials(
    client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    async def must_not_send(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("send_credentials must not be called for existing user")

    monkeypatch.setattr("app.api.payments.EmailService.send_credentials", must_not_send)

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

    purchase_result = await db.execute(select(Purchase).where(Purchase.payment_id == f"order_id:{order_id}"))
    assert purchase_result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_webhook_email_failure_does_not_break_idempotency(
    client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    async def boom_send(*args: object, **kwargs: object) -> None:
        raise RuntimeError("smtp down")

    monkeypatch.setattr("app.api.payments.EmailService.send_credentials", boom_send)

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
    url = response.json()["url"]
    assert "signature=" in url
    assert ("guest%40example.com" in url) or ("guest@example.com" in url)


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
