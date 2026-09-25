"""Authenticated Telegram account linking endpoints."""

import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.models.telegram_link import TelegramLinkToken
from app.models.user import User


router = APIRouter()


@router.get("/status")
async def telegram_status(current_user: User = Depends(get_current_user)) -> dict:
    return {
        "connected": current_user.telegram_id is not None,
        "username": current_user.telegram_username,
    }


@router.post("/link", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_telegram_link(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_BOT_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram integration is not configured",
        )

    now = datetime.utcnow()
    await db.execute(
        delete(TelegramLinkToken).where(
            TelegramLinkToken.user_id == current_user.id,
            TelegramLinkToken.used_at.is_(None),
        )
    )
    opaque_token = secrets.token_urlsafe(32)
    expires_at = now + timedelta(minutes=15)
    db.add(
        TelegramLinkToken(
            user_id=current_user.id,
            token_hash=hashlib.sha256(opaque_token.encode("utf-8")).hexdigest(),
            expires_at=expires_at,
        )
    )
    await db.commit()
    username = settings.TELEGRAM_BOT_USERNAME.lstrip("@")
    return {
        "url": f"https://t.me/{username}?start={opaque_token}",
        "expires_at": expires_at,
        "connected": current_user.telegram_id is not None,
    }


@router.delete("/link", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_telegram(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    current_user.telegram_id = None
    current_user.telegram_username = None
    await db.execute(
        delete(TelegramLinkToken).where(
            TelegramLinkToken.user_id == current_user.id,
            TelegramLinkToken.used_at.is_(None),
        )
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
