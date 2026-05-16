"""
Конфигурация приложения из переменных окружения.

Файлы .env (монорепозиторий):
- Корень репозитория `.env` — основной файл (как в README / Railway-переменные удобно дублировать локально).
- `backend/.env` — опционально; переопределяет значения из корня (полезно, если хотите только backend-секреты рядом с кодом).

Переменные из окружения ОС имеют приоритет над файлами.
"""

from pathlib import Path

from pydantic import field_validator, model_validator
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
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE_SECONDS: int = 1800

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
    # Parent domain for auth/CSRF cookies. Empty = host-only cookies (single-host dev).
    # Set to e.g. "lucysmirnova.ru" so cookies are readable by frontend on a sibling
    # subdomain (lucysmirnova.ru reading cookies set by api.lucysmirnova.ru).
    COOKIE_DOMAIN: str = ""
    
    # === Kinescope ===
    KINESCOPE_API_KEY: str = ""
    KINESCOPE_PROJECT_ID: str = ""

    # === Kinescope DRM Authorization Backend ===
    # Приватный ключ RSA (PEM). Можно задать одним из двух способов:
    #   - KINESCOPE_JWT_PRIVATE_KEY_PATH = absolute path to PEM file
    #   - KINESCOPE_JWT_PRIVATE_KEY_PEM  = inline PEM (удобно для Railway secrets)
    # Публичная часть как JWK заливается в Kinescope скриптом scripts/kinescope/setup_drm.py
    KINESCOPE_JWT_PRIVATE_KEY_PATH: str = ""
    KINESCOPE_JWT_PRIVATE_KEY_PEM: str = ""
    KINESCOPE_JWK_KID: str = ""
    KINESCOPE_DRM_TOKEN_TTL_SECONDS: int = 300
    # HTTP Basic Auth, ожидаемый от Kinescope при вызове нашего webhook
    KINESCOPE_DRM_BASIC_USER: str = ""
    KINESCOPE_DRM_BASIC_PASS: str = ""
    
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
    SMTP_REQUIRED_FOR_PAYMENT_EMAIL: bool = False

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

    # Сколько дней доступа к курсу после успешной оплаты (production v1)
    COURSE_ACCESS_DAYS: int = 30

    # Список разрешённых Origin для CORS (через запятую). Пусто — только FRONTEND_URL.
    CORS_ORIGINS: str = ""

    # Для production: список Host заголовков (через запятую), например api.example.com,localhost
    TRUSTED_HOSTS: str = ""

    # Persistent upload directory. Leave empty in production to disable local uploads.
    UPLOAD_STORAGE_DIR: str = ""
    UPLOAD_PUBLIC_BASE_URL: str = ""

    @model_validator(mode="after")
    def validate_production_safety(self):
        """Fail fast when production starts with unsafe defaults."""
        if self.ENVIRONMENT.lower() != "production":
            return self

        errors: list[str] = []
        if self.DEBUG:
            errors.append("DEBUG must be false in production")
        if self.JWT_SECRET_KEY == "your-super-secret-key-change-in-production":
            errors.append("JWT_SECRET_KEY must be changed in production")
        if not self.KINESCOPE_API_KEY:
            errors.append("KINESCOPE_API_KEY is required in production")
        if not self.PRODAMUS_URL:
            errors.append("PRODAMUS_URL is required in production")
        if not self.PRODAMUS_SECRET_KEY:
            errors.append("PRODAMUS_SECRET_KEY is required in production")
        if not self.PRODAMUS_SHOP_ID:
            errors.append("PRODAMUS_SHOP_ID is required in production")
        if self.SMTP_REQUIRED_FOR_PAYMENT_EMAIL and (not self.SMTP_USER or not self.SMTP_PASSWORD):
            errors.append("SMTP_USER and SMTP_PASSWORD are required in production")
        if "localhost" in self.FRONTEND_URL or "127.0.0.1" in self.FRONTEND_URL:
            errors.append("FRONTEND_URL must be public in production")
        if "localhost" in self.BACKEND_URL or "127.0.0.1" in self.BACKEND_URL:
            errors.append("BACKEND_URL must be public in production")
        if not self.TRUSTED_HOSTS:
            errors.append("TRUSTED_HOSTS is required in production")

        if errors:
            raise ValueError("; ".join(errors))

        return self


settings = Settings()
