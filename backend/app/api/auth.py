"""
API эндпоинты для аутентификации.
"""
import logging
import secrets

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.core.security import create_password_reset_token, verify_password_reset_token
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    Token,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.services.email_service import EmailService


logger = logging.getLogger(__name__)

router = APIRouter()


class RefreshRequest(BaseModel):
    """Обновление access token."""

    refresh_token: str | None = Field(None, min_length=10)


def _is_production() -> bool:
    return settings.ENVIRONMENT.lower() == "production"


def _cookie_domain() -> str | None:
    return settings.COOKIE_DOMAIN or None


def _set_auth_cookies(response: Response, tokens: Token) -> None:
    csrf_token = secrets.token_urlsafe(32)
    domain = _cookie_domain()
    cookie_options = {
        "httponly": True,
        "secure": _is_production(),
        "samesite": "lax",
        "path": "/",
        "domain": domain,
    }
    response.set_cookie(
        "access_token",
        tokens.access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **cookie_options,
    )
    response.set_cookie(
        "refresh_token",
        tokens.refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        **cookie_options,
    )
    response.set_cookie(
        "csrf_token",
        csrf_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=False,
        secure=_is_production(),
        samesite="lax",
        path="/",
        domain=domain,
    )


def _clear_auth_cookies(response: Response) -> None:
    domain = _cookie_domain()
    for cookie_name in ("access_token", "refresh_token", "csrf_token"):
        response.delete_cookie(
            cookie_name,
            path="/",
            secure=_is_production(),
            samesite="lax",
            domain=domain,
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("15/minute")
async def register(
    request: Request,
    data: UserRegister,
    db: AsyncSession = Depends(get_db),
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
            detail=str(e),
        )


@router.post("/login", response_model=Token)
@limiter.limit("30/minute")
async def login(
    request: Request,
    response: Response,
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
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

    tokens = AuthService.create_tokens(user.id, user.token_version)
    _set_auth_cookies(response, tokens)
    return tokens


@router.post("/refresh", response_model=Token)
@limiter.limit("45/minute")
async def refresh_token_endpoint(
    request: Request,
    response: Response,
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Выдаёт новый access token по валидному refresh token."""
    refresh_token = data.refresh_token or request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is required",
        )

    try:
        payload = jwt.decode(
            refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not a refresh token",
            )
        user_id_str: str | None = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    result = await db.execute(select(User).where(User.id == UUID(user_id_str)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    # Reject refresh tokens issued before the last password change/reset.
    if payload.get("ver") != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    tokens = AuthService.create_tokens(user.id, user.token_version)
    _set_auth_cookies(response, tokens)
    return tokens


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
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
async def logout(response: Response):
    """
    Выход пользователя.

    Note:
        JWT stateless, поэтому просто возвращаем успех.
        Клиент должен удалить токен на своей стороне.
    """
    _clear_auth_cookies(response)
    return {"message": "Successfully logged out"}


@router.post("/change-password")
@limiter.limit("10/minute")
async def change_password(
    request: Request,
    response: Response,
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Меняет пароль залогиненного пользователя (нужен текущий пароль)."""
    ok = await AuthService.change_password(
        db, current_user, data.current_password, data.new_password
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    await db.commit()
    # The bumped token_version invalidated every prior session (incl. this one),
    # so re-issue fresh cookies to keep the current device logged in while other
    # devices are logged out.
    tokens = AuthService.create_tokens(current_user.id, current_user.token_version)
    _set_auth_cookies(response, tokens)
    return {"message": "Password changed"}


@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Отправляет ссылку на сброс пароля, если аккаунт существует.

    Ответ всегда одинаковый (не раскрывает наличие email — защита от enumeration).
    """
    email = data.email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        token = create_password_reset_token(user.id, user.token_version)
        reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/auth/reset-password?token={token}"
        try:
            await EmailService.send_password_reset(user.email, reset_url)
        except Exception:
            logger.exception("Failed to send reset email to %s", user.email)
    return {"message": "If the account exists, a reset link has been sent"}


@router.post("/reset-password")
@limiter.limit("10/minute")
async def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Устанавливает новый пароль по токену из письма."""
    invalid = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired reset token",
    )
    payload = verify_password_reset_token(data.token)
    if not payload or not payload.get("sub"):
        raise invalid
    try:
        user_uuid = UUID(payload["sub"])
    except ValueError:
        raise invalid

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user:
        raise invalid
    # Single-use: a reset bumps token_version, so replaying the same token
    # (its "ver" now stale) is rejected here.
    if payload.get("ver") != user.token_version:
        raise invalid

    await AuthService.set_password(db, user, data.new_password)
    await db.commit()
    return {"message": "Password has been reset"}
