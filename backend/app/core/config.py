"""
Конфигурация приложения из переменных окружения.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # === Database ===
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nails_course"
    
    # === Redis ===
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # === Auth ===
    JWT_SECRET_KEY: str = "your-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # === Kinescope ===
    KINESCOPE_API_KEY: str = ""
    KINESCOPE_PROJECT_ID: str = ""
    
    # === Prodamus ===
    PRODAMUS_API_KEY: str = ""
    PRODAMUS_SECRET_KEY: str = ""
    PRODAMUS_SHOP_ID: str = ""
    
    # === Telegram ===
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_SUPPORT_GROUP_INVITE: str = ""
    
    # === Frontend ===
    FRONTEND_URL: str = "http://localhost:3000"
    
    # === Environment ===
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
