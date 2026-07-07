"""Tests for the password change / forgot / reset flow (audit 2026-07-06, P0-1)."""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from jose import jwt

from app.core.config import settings
from app.core.security import create_password_reset_token


async def _register(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post("/api/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_reset_password_flow(client: AsyncClient):
    user_id = await _register(client, "reset@example.com", "oldpass1")
    token = create_password_reset_token(user_id)

    r = await client.post(
        "/api/auth/reset-password", json={"token": token, "new_password": "brandnew2"}
    )
    assert r.status_code == 200, r.text

    old = await client.post(
        "/api/auth/login", json={"email": "reset@example.com", "password": "oldpass1"}
    )
    assert old.status_code == 401

    new = await client.post(
        "/api/auth/login", json={"email": "reset@example.com", "password": "brandnew2"}
    )
    assert new.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_invalid_token(client: AsyncClient):
    r = await client.post(
        "/api/auth/reset-password",
        json={"token": "not-a-real-token", "new_password": "whatever1"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_forgot_password_generic_response(client: AsyncClient):
    await _register(client, "exists@example.com", "password1")

    hit = await client.post("/api/auth/forgot-password", json={"email": "exists@example.com"})
    miss = await client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})

    # Same status and body for existing and non-existing account (no enumeration).
    assert hit.status_code == 200
    assert miss.status_code == 200
    assert hit.json() == miss.json()


@pytest.mark.asyncio
async def test_change_password_flow(client: AsyncClient):
    await _register(client, "chg@example.com", "oldpass1")
    login = await client.post(
        "/api/auth/login", json={"email": "chg@example.com", "password": "oldpass1"}
    )
    assert login.status_code == 200
    csrf = client.cookies.get("csrf_token")
    assert csrf

    r = await client.post(
        "/api/auth/change-password",
        json={"current_password": "oldpass1", "new_password": "newpass2"},
        headers={"x-csrf-token": csrf},
    )
    assert r.status_code == 200, r.text

    # New password works, old does not.
    await client.post("/api/auth/logout")
    old = await client.post(
        "/api/auth/login", json={"email": "chg@example.com", "password": "oldpass1"}
    )
    assert old.status_code == 401
    new = await client.post(
        "/api/auth/login", json={"email": "chg@example.com", "password": "newpass2"}
    )
    assert new.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current(client: AsyncClient):
    await _register(client, "chg2@example.com", "oldpass1")
    login = await client.post(
        "/api/auth/login", json={"email": "chg2@example.com", "password": "oldpass1"}
    )
    assert login.status_code == 200
    csrf = client.cookies.get("csrf_token")

    r = await client.post(
        "/api/auth/change-password",
        json={"current_password": "WRONG", "new_password": "newpass2"},
        headers={"x-csrf-token": csrf},
    )
    assert r.status_code == 400


# --- Token hardening (audit round 2: A1 token-type, A2 session invalidation) ---


@pytest.mark.asyncio
async def test_reset_token_not_usable_as_access_token(client: AsyncClient):
    """A reset JWT must NOT authenticate as an access token (type confusion)."""
    user_id = await _register(client, "resettoken@example.com", "password1")
    reset = create_password_reset_token(user_id)

    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {reset}"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_reset_token_single_use(client: AsyncClient):
    """A reset token is single-use: replay after a successful reset is rejected."""
    user_id = await _register(client, "singleuse@example.com", "oldpass1")
    token = create_password_reset_token(user_id)

    r1 = await client.post(
        "/api/auth/reset-password", json={"token": token, "new_password": "newpass2"}
    )
    assert r1.status_code == 200, r1.text

    r2 = await client.post(
        "/api/auth/reset-password", json={"token": token, "new_password": "newpass3"}
    )
    assert r2.status_code == 400


@pytest.mark.asyncio
async def test_expired_reset_token_rejected(client: AsyncClient):
    user_id = await _register(client, "expiredtok@example.com", "password1")
    expired = jwt.encode(
        {
            "sub": str(user_id),
            "ver": 0,
            "type": "reset",
            "exp": datetime.utcnow() - timedelta(minutes=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    r = await client.post(
        "/api/auth/reset-password", json={"token": expired, "new_password": "newpass2"}
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_password_change_invalidates_old_access_token(client: AsyncClient):
    """Changing the password bumps token_version → old access token is rejected."""
    await _register(client, "invalidate@example.com", "oldpass1")
    login = await client.post(
        "/api/auth/login", json={"email": "invalidate@example.com", "password": "oldpass1"}
    )
    assert login.status_code == 200
    old_access = login.json()["access_token"]
    csrf = client.cookies.get("csrf_token")

    ok_before = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {old_access}"}
    )
    assert ok_before.status_code == 200

    chg = await client.post(
        "/api/auth/change-password",
        json={"current_password": "oldpass1", "new_password": "newpass2"},
        headers={"x-csrf-token": csrf},
    )
    assert chg.status_code == 200, chg.text

    denied_after = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {old_access}"}
    )
    assert denied_after.status_code == 401


@pytest.mark.asyncio
async def test_csrf_required_on_change_password(client: AsyncClient):
    await _register(client, "csrfchg@example.com", "oldpass1")
    login = await client.post(
        "/api/auth/login", json={"email": "csrfchg@example.com", "password": "oldpass1"}
    )
    assert login.status_code == 200

    # cookie-authenticated unsafe request without the CSRF header → 403
    r = await client.post(
        "/api/auth/change-password",
        json={"current_password": "oldpass1", "new_password": "newpass2"},
    )
    assert r.status_code == 403
