import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    response = await client.post("/api/auth/register", json={
        "email": "test_register_unique@example.com",
        "password": "password123",
        "password_confirm": "password123"
    })
    if response.status_code != 201:
        print(f"Registration failed: {response.text}")
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test_register_unique@example.com"
    assert "id" in data

@pytest.mark.asyncio
async def test_login_user(client: AsyncClient):
    # Register first
    await client.post("/api/auth/register", json={
        "email": "login@example.com",
        "password": "password123",
        "password_confirm": "password123"
    })
    
    # Login
    response = await client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert response.cookies.get("access_token")
    assert response.cookies.get("refresh_token")


@pytest.mark.asyncio
async def test_get_me_accepts_cookie_token(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "cookie-me@example.com",
        "password": "password123",
        "password_confirm": "password123"
    })

    login_res = await client.post("/api/auth/login", json={
        "email": "cookie-me@example.com",
        "password": "password123"
    })

    response = await client.get(
        "/api/auth/me",
        cookies={"access_token": login_res.json()["access_token"]},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "cookie-me@example.com"


@pytest.mark.asyncio
async def test_refresh_accepts_cookie_token(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "cookie-refresh@example.com",
        "password": "password123",
        "password_confirm": "password123"
    })

    login_res = await client.post("/api/auth/login", json={
        "email": "cookie-refresh@example.com",
        "password": "password123"
    })

    response = await client.post(
        "/api/auth/refresh",
        json={},
        cookies={"refresh_token": login_res.json()["refresh_token"]},
    )

    assert response.status_code == 200
    assert response.cookies.get("access_token")
    assert response.cookies.get("csrf_token")


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    # Register
    await client.post("/api/auth/register", json={
        "email": "me@example.com",
        "password": "password123",
        "password_confirm": "password123"
    })
    
    # Login
    login_res = await client.post("/api/auth/login", json={
        "email": "me@example.com",
        "password": "password123"
    })
    token = login_res.json()["access_token"]
    
    # Get Me
    response = await client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
