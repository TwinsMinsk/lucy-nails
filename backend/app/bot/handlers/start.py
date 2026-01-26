
from telegram import Update
from telegram.ext import ContextTypes

from app.bot.services.auth import BotAuthService

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /start.
    Поддерживает deep linking для привязки аккаунта.
    """
    user = update.effective_user
    args = context.args

    if not args:
        await update.message.reply_text(
            f"Привет, {user.first_name}! 👋\n\n"
            "Я бот курса по дизайну ногтей. "
            "Чтобы привязать аккаунт, перейдите по ссылке из личного кабинета на сайте."
        )
        return

    # Если есть аргументы, пробуем привязать аккаунт
    token = args[0]
    
    # Отправляем сообщение о процессе
    status_message = await update.message.reply_text("⏳ Проверяю данные...")
    
    # Вызываем сервис
    result_message = await BotAuthService.link_account(token, user)
    
    # Обновляем сообщение
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=status_message.message_id,
        text=result_message
    )
