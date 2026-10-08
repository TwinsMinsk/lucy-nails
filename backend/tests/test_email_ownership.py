import asyncio
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_account_activation_token,
    create_password_reset_token,
    get_password_hash,
)
from app.main import app
from app.models.auth_security import AuthSession
from app.models.course import Course
from app.models.entitlement import Entitlement
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.order import Order
from app.models.outbox import OutboxMessage
from app.models.purchase import Purchase
from app.models.user import User
from app.services.outbox_service import process_outbox_batch
from app.services.prodamus_service import _make_signature
from conftest import TestingSessionLocal
from test_kinescope_drm import configured_drm as configured_drm
from test_kinescope_drm import _basic_auth_header
from app.services.kinescope_jwt_service import KinescopeJwtService
from app.services.purchase_service import PurchaseService
from app.services.support_access_service import has_active_support_entitlement
from app.models.telegram_link import TelegramLinkToken
from app.bot.services.auth import BotAuthService
from types import SimpleNamespace
import hashlib


async def register(client, email="owner@example.com"):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "attacker-password",
            "offer_accepted": True,
            "personal_data_consent": True,
        },
    )
    assert response.status_code == 201
    return response.json()


async def login(client, password="attacker-password", email="owner@example.com"):
    response = await client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    client.cookies.clear()
    return response.json()


@pytest.mark.asyncio
async def test_registration_and_resend_queue_generic_mailbox_claim(client, db):
    registered = await register(client)
    assert registered["email_verified_at"] is None
    message = await db.scalar(
        select(OutboxMessage).where(OutboxMessage.kind == "email_verification")
    )
    assert message is not None
    assert "password" not in message.payload
    hit = await client.post(
        "/api/auth/resend-verification", json={"email": "owner@example.com"}
    )
    miss = await client.post(
        "/api/auth/resend-verification", json={"email": "missing@example.com"}
    )
    assert hit.status_code == miss.status_code == 200
    assert hit.json() == miss.json()


@pytest.mark.asyncio
@pytest.mark.parametrize("buyer", ["attacker", "legacy", "new", "verified"])
async def test_guest_payment_requires_mailbox_ownership(
    client, db, buyer, configured_drm
):
    if buyer != "new":
        if buyer == "legacy":
            db.add(
                User(
                    email="owner@example.com",
                    password_hash=get_password_hash("attacker-password"),
                    role="student",
                )
            )
            await db.commit()
        else:
            await register(client)
        user = await db.scalar(select(User).where(User.email == "owner@example.com"))
        if buyer == "verified":
            user.email_verified_at = datetime.utcnow()
            await db.commit()
        old_tokens = await login(client)
    course = Course(
        title="Ownership", price_self=5000, price_support=10000, is_published=True
    )
    db.add(course)
    await db.flush()
    module = Module(
        course_id=course.id, title="Module", order_index=1, is_published=True
    )
    db.add(module)
    await db.flush()
    lesson = Lesson(
        module_id=module.id,
        title="Paid",
        order_index=1,
        content="PAID CONTENT",
        kinescope_video_id="video",
    )
    db.add(lesson)
    await db.commit()
    checkout = await client.post(
        "/api/payments/guest-link",
        json={
            "course_id": str(course.id),
            "tariff": "self",
            "customer_email": "owner@example.com",
            "offer_accepted": True,
            "personal_data_consent": True,
        },
    )
    assert checkout.status_code == 200, checkout.text
    order_id = checkout.json()["order_id"]
    notification = {
        "order_id": "ownership-payment",
        "order_num": order_id,
        "customer_email": "owner@example.com",
        "sum": "5000.00",
        "currency": "rub",
        "payment_status": "success",
    }
    paid = await client.post(
        "/api/payments/webhook",
        json=notification,
        headers={"Sign": _make_signature(notification, settings.PRODAMUS_SECRET_KEY)},
    )
    assert paid.status_code == 200, paid.text
    db.expire_all()
    await db.refresh(lesson)
    user = await db.scalar(select(User).where(User.email == "owner@example.com"))
    messages = list(
        (
            await db.scalars(
                select(OutboxMessage).where(
                    OutboxMessage.dedupe_key.like("payment:%"),
                    OutboxMessage.channel == "email",
                )
            )
        ).all()
    )
    assert len(messages) == 1
    assert messages[0].kind == (
        "access_granted" if buyer == "verified" else "account_activation"
    )

    async def offline(_):
        raise RuntimeError("Delivery unavailable")

    await process_outbox_batch(db, deliver=offline)
    assert await db.scalar(select(Purchase.id)) is not None
    assert await db.scalar(select(Entitlement.id)) is not None
    assert (await db.scalar(select(Order))).status == "paid"
    assert messages[0].status == "retry"
    if buyer != "new":
        headers = {"Authorization": f"Bearer {old_tokens['access_token']}"}
        details = await client.get(f"/api/lessons/{lesson.id}", headers=headers)
        assert details.json()["content"] == (
            "PAID CONTENT" if buyer == "verified" else None
        )
        if buyer != "verified":
            assert (
                await client.get(f"/api/lessons/{lesson.id}/play", headers=headers)
            ).status_code == 403
            drm = KinescopeJwtService().create_drm_token(
                user_id=str(user.id), lesson_id=str(lesson.id)
            )
            denied = await client.post(
                "/api/integrations/kinescope/drm/authorize",
                json={"id": "video", "token": drm},
                headers={
                    "Authorization": _basic_auth_header(
                        "kinescope-drm", "test-pass-123"
                    )
                },
            )
            assert denied.status_code == 403
    if buyer == "verified":
        return
    activation = parse_qs(urlparse(messages[0].payload["activation_url"]).query)[
        "token"
    ][0]
    claimed = await client.post(
        "/api/auth/activate",
        json={"token": activation, "new_password": "victim-password"},
    )
    assert claimed.status_code == 200, claimed.text
    await db.refresh(user)
    assert user.email_verified_at is not None
    assert user.token_version == 1
    if buyer != "new":
        assert (await client.get("/api/auth/me", headers=headers)).status_code == 401
        assert (
            await client.post(
                "/api/auth/refresh", json={"refresh_token": old_tokens["refresh_token"]}
            )
        ).status_code == 401
    victim = await login(client, "victim-password")
    details = await client.get(
        f"/api/lessons/{lesson.id}",
        headers={"Authorization": f"Bearer {victim['access_token']}"},
    )
    assert details.json()["content"] == "PAID CONTENT"


@pytest.mark.asyncio
async def test_logout_revokes_refresh_when_access_expired(client, db):
    await register(client)
    tokens = await login(client)
    claims = jwt.decode(
        tokens["access_token"],
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    expired = create_access_token(claims, expires_delta=timedelta(seconds=-1))
    response = await client.post(
        "/api/auth/logout",
        cookies={"access_token": expired, "refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 200
    assert (
        await client.post(
            "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
    ).status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "route,token_factory",
    [
        ("activate", create_account_activation_token),
        ("reset-password", create_password_reset_token),
    ],
)
async def test_mailbox_tokens_are_atomic_and_revoke_sessions(
    client, db, route, token_factory
):
    registered = await register(client)
    await login(client)
    token = token_factory(registered["id"])

    async def isolated_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = isolated_db

    async def redeem(password):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as isolated:
            return await isolated.post(
                f"/api/auth/{route}", json={"token": token, "new_password": password}
            )

    responses = await asyncio.gather(
        redeem("first-password"), redeem("second-password")
    )
    assert sorted(response.status_code for response in responses) == [200, 400]
    user = await db.scalar(select(User))
    assert user.email_verified_at is not None
    assert user.token_version == 1
    assert all(
        session.revoked_at is not None
        for session in (await db.scalars(select(AuthSession))).all()
    )


@pytest.mark.asyncio
async def test_password_change_does_not_claim_mailbox(client, db):
    await register(client)
    tokens = await login(client)
    changed = await client.post(
        "/api/auth/change-password",
        json={"current_password": "attacker-password", "new_password": "new-password"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert changed.status_code == 200
    user = await db.scalar(select(User))
    assert user.email_verified_at is None


@pytest.mark.asyncio
@pytest.mark.parametrize("subject", ["not-a-uuid", [], 17])
async def test_bad_jwt_subject_is_controlled(client, subject):
    token = jwt.encode(
        {
            "sub": subject,
            "ver": 0,
            "type": "access",
            "exp": datetime.utcnow() + timedelta(minutes=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "route", ["activate", "reset-password", "refresh", "mfa/setup"]
)
async def test_oversized_token_inputs_rejected(client, route):
    key = {"refresh": "refresh_token", "mfa/setup": "setup_token"}.get(route, "token")
    response = await client.post(
        f"/api/auth/{route}", json={key: "x" * 10000, "new_password": "new-password"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_deep_jwt_is_controlled(client):
    import base64
    import hashlib
    import hmac

    def encode(value):
        return base64.urlsafe_b64encode(value).rstrip(b"=")

    header = encode(b'{"alg":"HS256","typ":"JWT"}')
    payload = encode(b'{"nested":' + b"[" * 1200 + b"0" + b"]" * 1200 + b"}")
    signing = header + b"." + payload
    signature = encode(
        hmac.new(settings.JWT_SECRET_KEY.encode(), signing, hashlib.sha256).digest()
    )
    token = (signing + b"." + signature).decode()
    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_drm_malformed_subject_is_controlled(client, configured_drm):
    token = KinescopeJwtService().create_drm_token(user_id="invalid-uuid")
    response = await client.post(
        "/api/integrations/kinescope/drm/authorize",
        json={"id": "video", "token": token},
        headers={"Authorization": _basic_auth_header("kinescope-drm", "test-pass-123")},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_drm_oversized_input_rejected(client, configured_drm):
    response = await client.post(
        "/api/integrations/kinescope/drm/authorize",
        json={"id": "video", "token": "x" * 10000},
        headers={"Authorization": _basic_auth_header("kinescope-drm", "test-pass-123")},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_drm_malformed_lesson_is_controlled(client, db, configured_drm):
    registered = await register(client)
    token = KinescopeJwtService().create_drm_token(
        user_id=registered["id"], lesson_id="invalid-uuid"
    )
    response = await client.post(
        "/api/integrations/kinescope/drm/authorize",
        json={"id": "video", "token": token},
        headers={"Authorization": _basic_auth_header("kinescope-drm", "test-pass-123")},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unverified_support_access_and_telegram_claim_are_denied(
    client, db, monkeypatch
):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "test_bot")
    monkeypatch.setattr(
        settings, "TELEGRAM_SUPPORT_GROUP_INVITE", "https://t.me/private-invite"
    )
    await register(client)
    tokens = await login(client)
    user = await db.scalar(select(User))
    user.telegram_id = 123456
    user.telegram_username = "old-untrusted-link"
    course = Course(
        title="Support", price_self=5000, price_support=10000, is_published=True
    )
    db.add(course)
    await db.flush()
    db.add(
        Entitlement(
            user_id=user.id,
            course_id=course.id,
            source="manual",
            tariff="support",
            status="active",
            starts_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
    )
    db.add(
        TelegramLinkToken(
            user_id=user.id,
            token_hash=hashlib.sha256(b"old-link").hexdigest(),
            expires_at=datetime.utcnow() + timedelta(minutes=15),
        )
    )
    await db.commit()
    courses = await PurchaseService.get_my_courses_with_progress(db, user.id)
    assert len(courses) == 1
    assert courses[0]["support_chat_url"] is None
    assert not await has_active_support_entitlement(db, user.id)
    response = await client.post(
        "/api/telegram/link",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 403
    outcome = await BotAuthService.link_account(
        "old-link", SimpleNamespace(id=123456, username="attacker")
    )
    assert "подтвердите email" in outcome
    activation = create_account_activation_token(user.id, user.token_version)
    confirmed = await client.post(
        "/api/auth/activate",
        json={"token": activation, "new_password": "victim-password"},
    )
    assert confirmed.status_code == 200
    await db.refresh(user)
    assert user.telegram_id is None
    assert user.telegram_username is None
    assert await db.scalar(select(TelegramLinkToken.id)) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("owner_action", ["activate", "reset-password", "logout"])
async def test_stale_password_change_cannot_override_owner_or_logout(
    client, db, monkeypatch, owner_action
):
    from app.core.security import verify_password
    from app.services.auth_service import AuthService

    registered = await register(client)
    tokens = await login(client)
    authenticated = asyncio.Event()
    resume = asyncio.Event()
    original_change = AuthService.change_password

    async def pause_after_authentication(*args, **kwargs):
        authenticated.set()
        await asyncio.wait_for(resume.wait(), timeout=10)
        return await original_change(*args, **kwargs)

    monkeypatch.setattr(AuthService, "change_password", pause_after_authentication)

    async def isolated_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = isolated_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as attacker:
        pending = asyncio.create_task(
            attacker.post(
                "/api/auth/change-password",
                json={
                    "current_password": "attacker-password",
                    "new_password": "attacker-replacement",
                },
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )
        )
        await asyncio.wait_for(authenticated.wait(), timeout=10)
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as owner:
                if owner_action == "logout":
                    response = await owner.post(
                        "/api/auth/logout",
                        headers={"Authorization": f"Bearer {tokens['access_token']}"},
                    )
                else:
                    factory = (
                        create_account_activation_token
                        if owner_action == "activate"
                        else create_password_reset_token
                    )
                    response = await owner.post(
                        f"/api/auth/{owner_action}",
                        json={
                            "token": factory(registered["id"]),
                            "new_password": "owner-password",
                        },
                    )
                assert response.status_code == 200, response.text
        finally:
            resume.set()
        changed = await pending
    assert changed.status_code in {400, 401}, changed.text
    assert "access_token" not in changed.cookies
    user = await db.scalar(select(User).execution_options(populate_existing=True))
    expected_password = (
        "attacker-password" if owner_action == "logout" else "owner-password"
    )
    assert verify_password(expected_password, user.password_hash)
    assert user.token_version == (0 if owner_action == "logout" else 1)
    sessions = (
        await db.scalars(select(AuthSession).execution_options(populate_existing=True))
    ).all()
    assert len(sessions) == 1
    assert all(session.revoked_at is not None for session in sessions)
