"""
Сервис аутентификации.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, Token


class AuthService:
    """Сервис для работы с аутентификацией."""
    
    @staticmethod
    async def register_user(db: AsyncSession, data: UserRegister) -> User:
        """
        Регистрация нового пользователя.
        
        Args:
            db: Сессия БД
            data: Данные регистрации
        
        Returns:
            Созданный пользователь
        
        Raises:
            ValueError: Если email уже существует
        """
        # Проверка существования email
        result = await db.execute(
            select(User).where(User.email == data.email)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise ValueError("Email already registered")
        
        # Создание пользователя
        user = User(
            email=data.email,
            password_hash=get_password_hash(data.password),
            role="student",  # По умолчанию студент
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(user)
        await db.flush()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def authenticate_user(db: AsyncSession, data: UserLogin) -> User | None:
        """
        Проверка учётных данных пользователя.
        
        Args:
            db: Сессия БД
            data: Данные входа
        
        Returns:
            User если аутентификация успешна, None если нет
        """
        result = await db.execute(
            select(User).where(User.email == data.email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        if not verify_password(data.password, user.password_hash):
            return None
        
        return user
    
    @staticmethod
    def create_tokens(user_id: UUID) -> Token:
        """
        Создание JWT токенов для пользователя.
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Токены (access + refresh)
        """
        access_token = create_access_token({"sub": str(user_id)})
        refresh_token = create_refresh_token({"sub": str(user_id)})
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
    
    @staticmethod
    async def change_password(
        db: AsyncSession, user: User, current_password: str, new_password: str
    ) -> bool:
        """Меняет пароль после проверки текущего. False — текущий пароль неверен."""
        if not verify_password(current_password, user.password_hash):
            return False
        user.password_hash = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        return True

    @staticmethod
    async def set_password(db: AsyncSession, user: User, new_password: str) -> None:
        """Устанавливает новый пароль (после проверки reset-токена)."""
        user.password_hash = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
        """
        Получить пользователя по ID.
        
        Args:
            db: Сессия БД
            user_id: UUID пользователя
        
        Returns:
            User или None
        """
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
