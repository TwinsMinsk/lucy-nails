"""Local development entry point: the support bot over long polling.

Production receives updates through POST /api/telegram/webhook instead; both
transports hand the raw update to app.services.telegram_helpdesk_service.
Polling only works while no webhook is set (backend/scripts/telegram_webhook.py delete).
"""

import logging
import sys
import os

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from telegram import Update
from telegram.error import InvalidToken
from telegram.ext import ApplicationBuilder, TypeHandler
from app.core.config import settings
from app.bot.handlers.updates import handle_update
from app.services.telegram_helpdesk_service import ALLOWED_UPDATES

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# httpx logs full request URLs at INFO, and Telegram URLs contain the bot token.
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def main():
    """Запуск бота."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set in .env")
        return

    logger.info("Starting Telegram Bot...")

    application = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Every update goes to the shared handling service (/start included).
    application.add_handler(TypeHandler(Update, handle_update))

    # Запуск polling
    try:
        application.run_polling(allowed_updates=list(ALLOWED_UPDATES))
    except InvalidToken:
        # python-telegram-bot puts the rejected token into the exception text.
        logger.error("Telegram rejected TELEGRAM_BOT_TOKEN")
        raise SystemExit(1) from None

if __name__ == '__main__':
    main()
