"""
FastAPI Dependencies для аутентификации и авторизации.
"""

from typing import Annotated, Callable
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import PyJWTError as JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
):
    """
    Извлекает текущего пользователя из JWT токена.
    
    Args:
        token: JWT токен из заголовка Authorization
        db: Сессия базы данных
    
    Returns:
        User: Объект пользователя
    
    Raises:
        HTTPException: 401 если токен невалидный
    """
    from app.models.user import User
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_value = token or request.cookies.get("access_token")
    if not token_value:
        raise credentials_exception

    try:
        payload = jwt.decode(
            token_value,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        # Only access tokens authenticate. Reset/refresh tokens carry the same
        # signature+sub but must not grant API access.
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    # Token invalidation: a password change/reset bumps User.token_version, so
    # tokens minted before it (mismatched or missing "ver") are rejected.
    if payload.get("ver") != user.token_version:
        raise credentials_exception
    return user


async def require_admin(
    current_user = Depends(get_current_user),
):
    """
    Проверяет, что пользователь имеет роль admin.
    
    Raises:
        HTTPException: 403 если не админ
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def require_permission(permission_name: str) -> Callable:
    """Build a FastAPI dependency that enforces one normalized permission."""

    async def permission_dependency(
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        from app.models.rbac import Permission, Role, UserRoleAssignment

        permission = await db.scalar(
            select(Permission.id)
            .join(Permission.roles)
            .join(Role.assignments)
            .where(
                UserRoleAssignment.user_id == current_user.id,
                Permission.name == permission_name,
            )
            .limit(1)
        )
        if permission is not None:
            return current_user

        assignment_exists = await db.scalar(
            select(UserRoleAssignment.id)
            .where(UserRoleAssignment.user_id == current_user.id)
            .limit(1)
        )
        # Temporary rollout compatibility: legacy admins created before the RBAC
        # migration retain access only while they have no normalized assignment.
        if assignment_exists is None and current_user.role == "admin":
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission required: {permission_name}",
        )

    return permission_dependency


async def require_course_access(
    course_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Проверяет, что у пользователя есть активная покупка курса.
    
    Args:
        course_id: UUID курса
        current_user: Текущий пользователь
        db: Сессия базы данных
    
    Raises:
        HTTPException: 403 если нет доступа
    """
    from app.services.access_service import AccessService

    entitlement = await AccessService.get_active_entitlement(db, current_user.id, course_id)
    if entitlement is None and not await AccessService.has_active_access(
        db, current_user.id, course_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Course access required"
        )
    return entitlement
