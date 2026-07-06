"""Tests for the password change / forgot / reset flow (audit 2026-07-06, P0-1)."""

import pytest
from httpx import AsyncClient

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
