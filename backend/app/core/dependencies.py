"""
FastAPI Dependencies для аутентификации и авторизации.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
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
    
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
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
    from app.models.purchase import Purchase
    
    result = await db.execute(
        select(Purchase).where(
            Purchase.user_id == current_user.id,
            Purchase.course_id == course_id,
            Purchase.payment_status == "success",
            Purchase.expires_at > datetime.utcnow()
        )
    )
    purchase = result.scalar_one_or_none()
    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Course access required"
        )
    return purchase
