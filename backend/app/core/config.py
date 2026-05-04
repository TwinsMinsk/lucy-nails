"""
Конфигурация приложения из переменных окружения.

Файлы .env (монорепозиторий):
- Корень репозитория `.env` — основной файл (как в README / Railway-переменные удобно дублировать локально).
- `backend/.env` — опционально; переопределяет значения из корня (полезно, если хотите только backend-секреты рядом с кодом).

Переменные из окружения ОС имеют приоритет над файлами.
"""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> backend = parents[2], repo root = parents[3]
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_DIR.parent


def _env_files() -> tuple[Path, ...]:
    paths: list[Path] = []
    root_env = _REPO_ROOT / ".env"
    backend_env = _BACKEND_DIR / ".env"
    if root_env.is_file():
        paths.append(root_env)
    if backend_env.is_file():
        paths.append(backend_env)
    return tuple(paths)


class Settings(BaseSettings):
    """Настройки приложения."""

    model_config = SettingsConfigDict(
        env_file=_env_files() or None,
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # === Database ===
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nails_course"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str | None) -> str:
        if not v:
            return "postgresql+asyncpg://postgres:postgres@localhost:5432/nails_course"
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    
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
    PRODAMUS_URL: str = ""              # e.g. https://yourshop.payform.ru/
    PRODAMUS_SECRET_KEY: str = ""
    PRODAMUS_SHOP_ID: str = ""
    
    # === SMTP (Email) ===
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "Lucy Nails Academy"

    # === Telegram ===
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_SUPPORT_GROUP_INVITE: str = ""
    
    # === Frontend ===
    FRONTEND_URL: str = "http://localhost:3000"
    
    # === Backend (public URL for webhooks) ===
    BACKEND_URL: str = "http://localhost:8000"
    
    # === Environment ===
    ENVIRONMENT: str = "development"
    DEBUG: bool = True


settings = Settings()
