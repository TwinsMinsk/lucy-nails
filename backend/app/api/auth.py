"""
API эндпоинты для аутентификации.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.auth import UserRegister, UserLogin, Token, UserResponse
from app.services.auth_service import AuthService
from app.models.user import User


router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Регистрация нового пользователя.
    
    Args:
        data: Данные регистрации (email, password)
        db: Сессия БД
    
    Returns:
        Данные созданного пользователя
    
    Raises:
        HTTPException 400: Email уже зарегистрирован
    """
    try:
        user = await AuthService.register_user(db, data)
        await db.commit()
        return UserResponse.from_orm(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
async def login(
    data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Вход пользователя.
    
    Args:
        data: Данные входа (email, password)
        db: Сессия БД
    
    Returns:
        JWT токены (access + refresh)
    
    Raises:
        HTTPException 401: Неверные учётные данные
    """
    user = await AuthService.authenticate_user(db, data)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    tokens = AuthService.create_tokens(user.id)
    return tokens


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Получить информацию о текущем пользователе.
    
    Args:
        current_user: Текущий пользователь из JWT
    
    Returns:
        Данные пользователя
    """
    return UserResponse.from_orm(current_user)


@router.post("/logout")
async def logout():
    """
    Выход пользователя.
    
    Note:
        JWT stateless, поэтому просто возвращаем успех.
        Клиент должен удалить токен на своей стороне.
    """
    return {"message": "Successfully logged out"}
