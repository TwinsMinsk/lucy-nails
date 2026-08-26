"""
API эндпоинты для аутентификации.
"""
import logging
import secrets
from datetime import datetime

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
import jwt
from jwt.exceptions import PyJWTError as JWTError
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.core.security import (
    create_mfa_setup_token,
    create_password_reset_token,
    verify_account_activation_token,
    verify_mfa_setup_token,
    verify_password_reset_token,
)
from app.models.auth_security import AuthSession
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
from app.services.mfa_service import MfaService
from app.services.session_service import SessionService


logger = logging.getLogger(__name__)

router = APIRouter()


class RefreshRequest(BaseModel):
    """Обновление access token."""

    refresh_token: str | None = Field(None, min_length=10)


class MfaSetupRequest(BaseModel):
    setup_token: str = Field(..., min_length=10)


class MfaConfirmRequest(MfaSetupRequest):
    code: str = Field(..., min_length=6, max_length=32)


class MfaSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class MfaConfirmResponse(Token):
    backup_codes: list[str]


class SessionResponse(BaseModel):
    id: UUID
    user_agent: str | None
    ip_address: str | None
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    current: bool


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

    if await MfaService.requires_mfa(db, user.id):
        credential = await MfaService.get_credential(db, user.id)
        if credential is None or credential.enabled_at is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "mfa_setup_required",
                    "setup_token": create_mfa_setup_token(user.id, user.token_version),
                },
            )
        if not data.mfa_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "mfa_code_required"},
            )
        if not MfaService.verify(credential, data.mfa_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "mfa_code_invalid"},
            )

    tokens, _ = await SessionService.issue(db, user, request)
    await db.commit()
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

    session_id = payload.get("sid")
    if session_id:
        try:
            parsed_session_id = UUID(session_id)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        auth_session = await SessionService.get_active(db, parsed_session_id, user.id)
        if auth_session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        tokens = await SessionService.rotate(db, auth_session, user, refresh_token)
        if tokens is None:
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token reuse detected",
            )
    else:
        # Privileged accounts must never upgrade a pre-session token: it was
        # issued without a session-bound MFA authentication event.
        if await MfaService.requires_mfa(db, user.id):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="MFA reauthentication required",
            )
        # Upgrade a pre-session non-privileged refresh token to a revocable session.
        tokens, _ = await SessionService.issue(db, user, request)
    await db.commit()
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
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Выход пользователя.

    Note:
        JWT stateless, поэтому просто возвращаем успех.
        Клиент должен удалить токен на своей стороне.
    """
    token = request.cookies.get("access_token")
    authorization = request.headers.get("authorization") or ""
    if not token and authorization.lower().startswith("bearer "):
        token = authorization[7:]
    if token:
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            session_id = payload.get("sid")
            if session_id:
                auth_session = await db.get(AuthSession, UUID(session_id))
                if auth_session and str(auth_session.user_id) == payload.get("sub"):
                    auth_session.revoked_at = datetime.utcnow()
                    await db.commit()
        except (JWTError, TypeError, ValueError):
            pass
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
    await SessionService.revoke_all(db, current_user.id)
    # The bumped token_version invalidated every prior session (incl. this one),
    # so re-issue fresh cookies to keep the current device logged in while other
    # devices are logged out.
    tokens, _ = await SessionService.issue(db, current_user, request)
    await db.commit()
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
            logger.exception("Failed to send password reset email")
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


@router.post("/activate")
@limiter.limit("10/minute")
async def activate_payment_account(
    request: Request,
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Set the first password for an account created by a successful payment."""
    invalid = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired activation token",
    )
    payload = verify_account_activation_token(data.token)
    if not payload or not payload.get("sub"):
        raise invalid
    try:
        user_uuid = UUID(payload["sub"])
    except ValueError:
        raise invalid
    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user or payload.get("ver") != user.token_version:
        raise invalid
    await AuthService.set_password(db, user, data.new_password)
    await db.commit()
    return {"message": "Account activated"}


async def _resolve_mfa_setup_user(
    db: AsyncSession,
    setup_token: str,
) -> User:
    invalid = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired MFA setup token",
    )
    payload = verify_mfa_setup_token(setup_token)
    if not payload or not payload.get("sub"):
        raise invalid
    try:
        user_id = UUID(payload["sub"])
    except (TypeError, ValueError):
        raise invalid
    user = await db.get(User, user_id)
    if user is None or payload.get("ver") != user.token_version:
        raise invalid
    if not await MfaService.requires_mfa(db, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MFA setup is restricted to privileged team accounts",
        )
    return user


@router.post("/mfa/setup", response_model=MfaSetupResponse)
@limiter.limit("10/minute")
async def setup_mfa(
    request: Request,
    data: MfaSetupRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await _resolve_mfa_setup_user(db, data.setup_token)
    try:
        _, secret, provisioning_uri = await MfaService.get_or_create_setup(db, user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    await db.commit()
    return MfaSetupResponse(secret=secret, provisioning_uri=provisioning_uri)


@router.post("/mfa/confirm", response_model=MfaConfirmResponse)
@limiter.limit("10/minute")
async def confirm_mfa(
    request: Request,
    response: Response,
    data: MfaConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await _resolve_mfa_setup_user(db, data.setup_token)
    credential = await MfaService.get_credential(db, user.id)
    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start MFA setup before confirmation",
        )
    backup_codes = MfaService.enable(credential, data.code)
    if backup_codes is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code",
        )
    user.token_version = (user.token_version or 0) + 1
    await SessionService.revoke_all(db, user.id)
    tokens, _ = await SessionService.issue(db, user, request)
    await db.commit()
    _set_auth_cookies(response, tokens)
    return MfaConfirmResponse(**tokens.model_dump(), backup_codes=backup_codes)


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AuthSession)
        .where(
            AuthSession.user_id == current_user.id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.utcnow(),
        )
        .order_by(AuthSession.last_seen_at.desc())
    )
    current_session_id = getattr(request.state, "auth_session_id", None)
    return [
        SessionResponse(
            id=item.id,
            user_agent=item.user_agent,
            ip_address=item.ip_address,
            created_at=item.created_at,
            last_seen_at=item.last_seen_at,
            expires_at=item.expires_at,
            current=item.id == current_session_id,
        )
        for item in result.scalars().all()
    ]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    auth_session = await db.get(AuthSession, session_id)
    if auth_session is None or auth_session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if auth_session.revoked_at is None:
        auth_session.revoked_at = datetime.utcnow()
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
