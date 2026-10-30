
import logging
import sys
import os

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from telegram.error import InvalidToken
from telegram.ext import ApplicationBuilder, CommandHandler
from app.core.config import settings
from app.bot.handlers.start import start

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
    
    # Регистрация хендлеров
    application.add_handler(CommandHandler("start", start))
    
    # Запуск polling
    try:
        application.run_polling()
    except InvalidToken:
        # python-telegram-bot puts the rejected token into the exception text.
        logger.error("Telegram rejected TELEGRAM_BOT_TOKEN")
        raise SystemExit(1) from None

if __name__ == '__main__':
    main()
