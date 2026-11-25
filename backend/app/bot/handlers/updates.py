"""Polling transport: hand every update to the same service the webhook uses."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.core.database import async_session_maker
from app.services.telegram_helpdesk_service import HelpdeskTransientError, process_update

logger = logging.getLogger(__name__)


async def handle_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with async_session_maker() as db:
        try:
            await process_update(db, update.to_dict())
        except HelpdeskTransientError:
            # getUpdates has already moved past this update; in local
            # development a lost update is acceptable, production uses the webhook.
            logger.warning("Telegram update %s failed with a temporary error", update.update_id)
