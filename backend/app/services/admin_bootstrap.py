"""Utilities for one-off production admin bootstrap."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import User


async def ensure_admin_user(db: AsyncSession, email: str, password: str) -> User:
    """Create or promote an admin user with an explicit password."""
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise ValueError("Admin email is required")
    if len(password) < 12:
        raise ValueError("Admin password must be at least 12 characters")

    result = await db.execute(select(User).where(User.email == normalized_email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=normalized_email,
            password_hash=get_password_hash(password),
            role="admin",
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    user.role = "admin"
    user.password_hash = get_password_hash(password)
    await db.flush()
    await db.refresh(user)
    return user
