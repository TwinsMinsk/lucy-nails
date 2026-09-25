"""Creation, rotation, validation, and revocation of auth sessions."""

import hashlib
import hmac
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.auth_security import AuthSession
from app.models.user import User
from app.schemas.auth import Token
from app.services.auth_service import AuthService


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class SessionService:
    @staticmethod
    async def issue(
        db: AsyncSession,
        user: User,
        request: Request,
    ) -> tuple[Token, AuthSession]:
        session = AuthSession(
            user_id=user.id,
            refresh_token_hash="pending",
            ip_address=request.client.host if request.client else None,
            user_agent=(request.headers.get("user-agent") or "")[:512] or None,
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(session)
        await db.flush()
        tokens = AuthService.create_tokens(user.id, user.token_version, session.id)
        session.refresh_token_hash = hash_refresh_token(tokens.refresh_token)
        return tokens, session

    @staticmethod
    async def get_active(
        db: AsyncSession,
        session_id: UUID,
        user_id: UUID,
        *,
        for_update: bool = False,
    ) -> AuthSession | None:
        query = select(AuthSession).where(
                AuthSession.id == session_id,
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > datetime.utcnow(),
            )
        if for_update:
            query = query.with_for_update()
        return await db.scalar(query)

    @staticmethod
    async def rotate(
        db: AsyncSession,
        session: AuthSession,
        user: User,
        presented_refresh_token: str,
    ) -> Token | None:
        if not hmac_compare(
            session.refresh_token_hash,
            hash_refresh_token(presented_refresh_token),
        ):
            session.revoked_at = datetime.utcnow()
            return None
        tokens = AuthService.create_tokens(user.id, user.token_version, session.id)
        session.refresh_token_hash = hash_refresh_token(tokens.refresh_token)
        session.last_seen_at = datetime.utcnow()
        return tokens

    @staticmethod
    async def revoke_all(db: AsyncSession, user_id: UUID) -> None:
        await db.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=datetime.utcnow())
        )


def hmac_compare(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)
