import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson

@pytest.mark.asyncio
async def test_get_courses_empty(client: AsyncClient):
    response = await client.get("/api/courses")
    assert response.status_code == 200
    assert response.json() == {"courses": [], "total": 0}

@pytest.mark.asyncio
async def test_get_courses_list(client: AsyncClient, db: AsyncSession):
    # Create a course
    course = Course(
        title="Test Course",
        description="Desc",
        price_self=1000,
        price_support=2000,
        is_published=True
    )
    db.add(course)
    await db.commit()
    
    response = await client.get("/api/courses")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["courses"][0]["title"] == "Test Course"

@pytest.mark.asyncio
async def test_get_course_detail(client: AsyncClient, db: AsyncSession):
    course = Course(
        title="Detail Course",
        price_self=500,
        price_support=1000,
        is_published=True
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    
    response = await client.get(f"/api/courses/{course.id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Detail Course"

@pytest.mark.asyncio
async def test_get_modules_and_lessons(client: AsyncClient, db: AsyncSession):
    # Setup hierarchy
    course = Course(title="Course M", price_self=100, price_support=200, is_published=True)
    db.add(course)
    await db.commit()
    await db.refresh(course)
    
    module = Module(course_id=course.id, title="Module 1", order_index=1, is_published=True)
    db.add(module)
    await db.commit()
    await db.refresh(module)
    
    lesson = Lesson(module_id=module.id, title="Lesson 1", duration_seconds=60, order_index=1, is_preview=True)
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    
    # Check Modules
    res_modules = await client.get(f"/api/courses/{course.id}/modules")
    assert res_modules.status_code == 200
    assert len(res_modules.json()) == 1
    
    # Check Lessons
    res_lessons = await client.get(f"/api/modules/{module.id}/lessons")
    assert res_lessons.status_code == 200
    assert len(res_lessons.json()) == 1
    assert res_lessons.json()[0]["title"] == "Lesson 1"

@pytest.mark.asyncio
async def test_lesson_detail(client: AsyncClient, db: AsyncSession):
    # Retrieve lesson details (preview)
    course = Course(title="Preview C", price_self=1, price_support=2, is_published=True)
    db.add(course)
    await db.flush()
    module = Module(course_id=course.id, title="M1", order_index=1, is_published=True)
    db.add(module)
    await db.flush()
    lesson = Lesson(
        module_id=module.id, 
        title="Preview Lesson", 
        duration_seconds=100, 
        order_index=1, 
        is_preview=True,
        kinescope_video_id="video123"
    )
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    
    # Need auth? The endpoint handles anonymous/auth. If user logged in, check access.
    # But for public preview, it should just work?
    # Let's check dependencies. get_current_user throws 401 if not authorized?
    # Actually, lesson detail endpoint uses `current_user: User = Depends(get_current_user)`.
    # `get_current_user` raises HTTPException(401) if not valid.
    # So we MUST be logged in.
    
    # Register & Login
    await client.post("/api/auth/register", json={"email": "u1@t.com", "password": "password123", "password_confirm": "password123"})
    login = await client.post("/api/auth/login", json={"email": "u1@t.com", "password": "password123"})
    token = login.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.get(f"/api/lessons/{lesson.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Preview Lesson"
    # Preview lesson should have video_url populated (mocked in API)
    assert data["video_url"] is not None
