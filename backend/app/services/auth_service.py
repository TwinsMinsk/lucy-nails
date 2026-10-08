"""
Сервис аутентификации.
"""

from datetime import datetime
from uuid import UUID
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.legal import CONSENT_VERSION
from app.core.config import settings
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token, create_account_activation_token
from app.models.user import User
from app.models.telegram_link import TelegramLinkToken
from app.schemas.auth import UserRegister, UserLogin, Token
from app.services.outbox_service import enqueue_outbox_message


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
        # Проверка существования email (case-insensitive: сравниваем по lower(),
        # чтобы легаси-записи со смешанным регистром тоже находились)
        result = await db.execute(
            select(User).where(func.lower(User.email) == data.email)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise ValueError("Email already registered")
        
        # Создание пользователя
        consented_at = datetime.utcnow()
        user = User(
            email=data.email,
            password_hash=await run_in_threadpool(get_password_hash, data.password),
            role="student",  # По умолчанию студент
            offer_accepted_at=consented_at if data.offer_accepted else None,
            personal_data_consent_at=consented_at if data.personal_data_consent else None,
            consent_version=CONSENT_VERSION,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(user)
        await db.flush()
        await db.refresh(user)
        AuthService.enqueue_verification(db, user)
        
        return user

    @staticmethod
    def enqueue_verification(db: AsyncSession, user: User) -> None:
        token = create_account_activation_token(user.id, user.token_version)
        enqueue_outbox_message(
            db,
            kind="email_verification",
            recipient=user.email,
            payload={"activation_url": f"{settings.FRONTEND_URL.rstrip('/')}/auth/activate?token={token}"},
            dedupe_key=f"verification:{user.id}:{uuid.uuid4().hex}",
        )

    @staticmethod
    async def confirm_mailbox(db: AsyncSession, user: User) -> None:
        if user.email_verified_at is None and user.role != "admin":
            user.telegram_id = None
            user.telegram_username = None
        await db.execute(delete(TelegramLinkToken).where(TelegramLinkToken.user_id == user.id))
        user.email_verified_at = datetime.utcnow()
    
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
            select(User).where(func.lower(User.email) == data.email)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None
        
        if not await run_in_threadpool(verify_password, data.password, user.password_hash):
            return None
        
        return user
    
    @staticmethod
    def create_tokens(
        user_id: UUID,
        token_version: int = 0,
        session_id: UUID | None = None,
    ) -> Token:
        """
        Создание JWT токенов для пользователя.

        Args:
            user_id: ID пользователя
            token_version: текущая версия сессий пользователя (кладётся в "ver")

        Returns:
            Токены (access + refresh)
        """
        payload = {"sub": str(user_id), "ver": token_version}
        if session_id is not None:
            payload["sid"] = str(session_id)
        access_token = create_access_token(payload)
        refresh_token = create_refresh_token(payload)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
    
    @staticmethod
    async def change_password(
        db: AsyncSession, user: User, current_password: str, new_password: str,
        *, authenticated_version: int | None = None, session_id: UUID | None = None,
    ) -> bool:
        """Меняет пароль после проверки текущего. False — текущий пароль неверен."""
        expected_version = user.token_version if authenticated_version is None else authenticated_version
        result = await db.execute(
            select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True)
        )
        user = result.scalar_one_or_none()
        if user is None or user.token_version != expected_version:
            return False
        if session_id is not None:
            from app.services.session_service import SessionService

            if await SessionService.get_active(db, session_id, user.id, for_update=True) is None:
                return False
        if not await run_in_threadpool(verify_password, current_password, user.password_hash):
            return False
        user.password_hash = await run_in_threadpool(get_password_hash, new_password)
        user.token_version = (user.token_version or 0) + 1
        user.updated_at = datetime.utcnow()
        return True

    @staticmethod
    async def set_password(db: AsyncSession, user: User, new_password: str) -> None:
        """Устанавливает новый пароль (после проверки reset-токена)."""
        user.password_hash = await run_in_threadpool(get_password_hash, new_password)
        user.token_version = (user.token_version or 0) + 1
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
