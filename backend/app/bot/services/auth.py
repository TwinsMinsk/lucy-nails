
from uuid import UUID
from telegram import User as TelegramUser
from sqlalchemy import select
from jose import jwt, JWTError

from app.core.database import async_session_maker
from app.core.config import settings
from app.models.user import User

class BotAuthService:
    """Сервис для аутентификации через Telegram."""
    
    @staticmethod
    async def link_account(token: str, telegram_user: TelegramUser) -> str:
        """
        Привязывает Telegram аккаунт к пользователю по JWT токену.
        
        Args:
            token: JWT токен из deep link
            telegram_user: Объект пользователя Telegram
            
        Returns:
            Сообщение о результатах операции
        """
        # 1. Валидация токена
        try:
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET_KEY, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            user_id_str: str = payload.get("sub")
            if not user_id_str:
                return "Некорректный токен. Попробуйте снова."
                
            user_id = UUID(user_id_str)
        except JWTError:
            return "Ссылка устарела или некорректна. Попробуйте сгенерировать новую в личном кабинете."
        except ValueError:
            return "Ошибка данных пользователя."

        # 2. Поиск и обновление пользователя в БД
        async with async_session_maker() as session:
            try:
                # Проверяем, не привязан ли уже этот Telegram ID к кому-то
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_user.id)
                )
                existing_telegram_user = result.scalar_one_or_none()
                
                if existing_telegram_user:
                    if existing_telegram_user.id == user_id:
                        return "Этот аккаунт Telegram уже привязан к вашему профилю."
                    else:
                        return "Этот аккаунт Telegram уже используется другим пользователем."
                
                # Ищем пользователя по ID из токена
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    return "Пользователь не найден."
                
                # Привязываем
                user.telegram_id = telegram_user.id
                user.telegram_username = telegram_user.username
                
                await session.commit()
                return "✅ Аккаунт успешно привязан! Теперь вы сможете получать уведомления и доступ к чату."
                
            except Exception as e:
                await session.rollback()
                # Логируем ошибку реально
                print(f"Error linking account: {e}")
                return "Произошла ошибка при привязке. Попробуйте позже."
