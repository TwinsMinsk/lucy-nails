"""One-time Telegram account linking used by the standalone bot."""

import hashlib
import logging
from datetime import datetime

from sqlalchemy import select
from telegram import User as TelegramUser

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.entitlement import Entitlement
from app.models.telegram_link import TelegramLinkToken
from app.models.user import User


logger = logging.getLogger(__name__)


class BotAuthService:
    @staticmethod
    async def link_account(token: str, telegram_user: TelegramUser) -> str:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = datetime.utcnow()

        async with async_session_maker() as session:
            try:
                token_row = await session.scalar(
                    select(TelegramLinkToken)
                    .where(TelegramLinkToken.token_hash == token_hash)
                    .with_for_update()
                )
                if token_row is None:
                    return "Ссылка некорректна. Создайте новую в личном кабинете."
                if token_row.used_at is not None:
                    return "Эта ссылка уже использована. Создайте новую в личном кабинете."
                if token_row.expires_at <= now:
                    return "Ссылка устарела. Создайте новую в личном кабинете."

                user = await session.get(User, token_row.user_id)
                if user is None:
                    return "Пользователь не найден."

                telegram_owner = await session.scalar(
                    select(User).where(User.telegram_id == telegram_user.id)
                )
                if telegram_owner is not None and telegram_owner.id != user.id:
                    return "Этот Telegram уже используется другим пользователем."
                if user.telegram_id is not None and user.telegram_id != telegram_user.id:
                    return "Сначала отключите прежний Telegram в личном кабинете."

                user.telegram_id = telegram_user.id
                user.telegram_username = telegram_user.username
                token_row.used_at = now
                await session.commit()

                support = await session.scalar(
                    select(Entitlement.id).where(
                        Entitlement.user_id == user.id,
                        Entitlement.tariff == "support",
                        Entitlement.status == "active",
                        Entitlement.starts_at <= now,
                        Entitlement.expires_at > now,
                    )
                )
                suffix = ""
                if support is not None and settings.TELEGRAM_SUPPORT_GROUP_INVITE:
                    suffix = f"\n\nЧат поддержки: {settings.TELEGRAM_SUPPORT_GROUP_INVITE}"
                return (
                    "✅ Аккаунт успешно привязан. Теперь сюда будут приходить "
                    f"уведомления о курсе.{suffix}"
                )
            except Exception:
                await session.rollback()
                logger.exception("Telegram account linking failed")
                return "Произошла ошибка при привязке. Попробуйте позже."
