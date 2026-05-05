import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.user import User
from app.services.admin_bootstrap import ensure_admin_user


@pytest.mark.asyncio
async def test_ensure_admin_user_creates_admin(db: AsyncSession):
    user = await ensure_admin_user(db, "Owner@Example.com", "StrongPass123!")
    await db.commit()

    result = await db.execute(select(User).where(User.email == "owner@example.com"))
    stored = result.scalar_one()
    assert user.id == stored.id
    assert stored.role == "admin"
    assert verify_password("StrongPass123!", stored.password_hash)


@pytest.mark.asyncio
async def test_ensure_admin_user_promotes_existing_user(db: AsyncSession):
    existing = User(
        email="student@example.com",
        password_hash="old-hash",
        role="student",
    )
    db.add(existing)
    await db.commit()

    user = await ensure_admin_user(db, "student@example.com", "NewStrongPass123!")
    await db.commit()

    assert user.id == existing.id
    assert user.role == "admin"
    assert verify_password("NewStrongPass123!", user.password_hash)
