import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.course import Course

@pytest.mark.asyncio
async def test_create_and_list_purchases(client: AsyncClient, db: AsyncSession):
    # Setup
    course = Course(
        title="Buy Me",
        price_self=5000,
        price_support=10000,
        is_published=True
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    
    # Auth
    await client.post("/api/auth/register", json={"email": "buyer@t.com", "password": "password123", "password_confirm": "password123"})
    login = await client.post("/api/auth/login", json={"email": "buyer@t.com", "password": "password123"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create Purchase
    res_create = await client.post("/api/purchases/create", json={
        "course_id": str(course.id),
        "tariff": "self"
    }, headers=headers)
    
    assert res_create.status_code == 200
    data = res_create.json()
    assert data["payment_status"] == "pending"
    assert data["amount_kopecks"] == 500000
    
    # List Purchases
    res_list = await client.get("/api/purchases/my", headers=headers)
    assert res_list.status_code == 200
    data_list = res_list.json()
    assert len(data_list) == 1
    assert data_list[0]["course_id"] == str(course.id)
