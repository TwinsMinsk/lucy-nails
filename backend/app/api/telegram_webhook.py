"""Telegram Bot API webhook: the support bot's updates in production.

Telegram authenticates itself with the X-Telegram-Bot-Api-Secret-Token header
(the secret_token given to setWebhook, see backend/scripts/telegram_webhook.py).
No cookies are involved, so the endpoint is exempt from the CSRF middleware.
"""

import hmac
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.services.telegram_helpdesk_service import HelpdeskTransientError, process_update

logger = logging.getLogger(__name__)

router = APIRouter()

# Updates are a few kilobytes; Telegram itself never sends anything close.
MAX_UPDATE_BODY_BYTES = 256 * 1024
SECRET_HEADER = "x-telegram-bot-api-secret-token"


async def _read_update_body(request: Request) -> bytes:
    """Read the body, counting the bytes received rather than Content-Length."""
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_UPDATE_BODY_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Payload too large")
    return bytes(body)


@router.post("/webhook", include_in_schema=False)
# Replaces the global per-IP limit for this route: Telegram delivers every
# update of the bot from a handful of addresses.
@limiter.limit("600/minute")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    secret = settings.TELEGRAM_WEBHOOK_SECRET
    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    supplied = request.headers.get(SECRET_HEADER, "")
    if not hmac.compare_digest(supplied.encode("utf-8"), secret.encode("utf-8")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    body = await _read_update_body(request)
    try:
        update = json.loads(body)
    except (ValueError, RecursionError):
        # Redelivering a malformed body cannot help.
        logger.warning("Telegram webhook: unparseable update ignored")
        return {"ok": True}

    try:
        await process_update(db, update)
    except HelpdeskTransientError:
        logger.warning("Telegram webhook: temporary failure, Telegram will redeliver", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Temporary failure"},
        )
    return {"ok": True}
