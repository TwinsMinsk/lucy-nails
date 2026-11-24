"""Utilities for one-off production admin bootstrap."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.rbac import Role, UserRoleAssignment
from app.models.user import User
from app.services.session_service import SessionService


async def _assign_owner_if_rbac_is_seeded(db: AsyncSession, user: User) -> None:
    owner_role = await db.scalar(select(Role).where(Role.name == "owner"))
    if owner_role is None:
        return
    existing = await db.scalar(
        select(UserRoleAssignment.id).where(
            UserRoleAssignment.user_id == user.id,
            UserRoleAssignment.role_id == owner_role.id,
        )
    )
    if existing is None:
        db.add(UserRoleAssignment(user_id=user.id, role_id=owner_role.id))


async def ensure_admin_user(db: AsyncSession, email: str, password: str) -> User:
    """Create or promote an admin user with an explicit password."""
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise ValueError("Admin email is required")
    if len(password) < 12:
        raise ValueError("Admin password must be at least 12 characters")

    result = await db.execute(select(User).where(func.lower(User.email) == normalized_email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=normalized_email,
            password_hash=get_password_hash(password),
            role="admin",
        )
        db.add(user)
        await db.flush()
        await _assign_owner_if_rbac_is_seeded(db, user)
        await db.refresh(user)
        return user

    # Lock the row so a concurrent login/refresh cannot mint a token for the old
    # version between the password swap and the version bump.
    user = await db.scalar(
        select(User)
        .where(User.id == user.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    user.role = "admin"
    user.password_hash = get_password_hash(password)
    # Permissions are read per request, so every earlier token and session of
    # this account (possibly held by someone else) must stop working before the
    # account gains owner rights or a new administrator password.
    user.token_version = (user.token_version or 0) + 1
    await SessionService.revoke_all(db, user.id)
    await _assign_owner_if_rbac_is_seeded(db, user)
    await db.flush()
    await db.refresh(user)
    return user
