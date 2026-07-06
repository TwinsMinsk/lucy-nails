import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.main import app


def test_app_registers_slowapi_middleware():
    middleware_names = {middleware.cls.__name__ for middleware in app.user_middleware}

    assert "SlowAPIMiddleware" in middleware_names


def test_production_config_rejects_insecure_defaults():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            DEBUG=True,
            JWT_SECRET_KEY="your-super-secret-key-change-in-production",
            KINESCOPE_API_KEY="",
            PRODAMUS_URL="",
            PRODAMUS_SECRET_KEY="",
            FRONTEND_URL="http://localhost:3000",
            BACKEND_URL="http://localhost:8000",
            TRUSTED_HOSTS="",
        )

    message = str(exc_info.value)
    assert "DEBUG must be false in production" in message
    assert "JWT_SECRET_KEY must be changed in production" in message


def test_production_config_requires_smtp_for_payment_credentials():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            DEBUG=False,
            JWT_SECRET_KEY="production-secret-that-is-32-chars-min",
            KINESCOPE_API_KEY="kinescope-key",
            PRODAMUS_URL="https://shop.payform.ru/",
            PRODAMUS_SECRET_KEY="prodamus-secret",
            PRODAMUS_SHOP_ID="shop-id",
            FRONTEND_URL="https://lucysmirnova.ru",
            BACKEND_URL="https://api.lucysmirnova.ru",
            TRUSTED_HOSTS="api.lucysmirnova.ru",
            SMTP_REQUIRED_FOR_PAYMENT_EMAIL=True,
            SMTP_USER="",
            SMTP_PASSWORD="",
        )

    assert "SMTP_USER and SMTP_PASSWORD are required in production" in str(exc_info.value)


def test_production_config_allows_smtp_disabled_for_registered_checkout_only():
    settings = Settings(
        _env_file=None,
        ENVIRONMENT="production",
        DEBUG=False,
        JWT_SECRET_KEY="production-secret-that-is-32-chars-min",
        KINESCOPE_API_KEY="kinescope-key",
        PRODAMUS_URL="https://shop.payform.ru/",
        PRODAMUS_SECRET_KEY="prodamus-secret",
        PRODAMUS_SHOP_ID="shop-id",
        FRONTEND_URL="https://lucysmirnova.ru",
        BACKEND_URL="https://api.lucysmirnova.ru",
        TRUSTED_HOSTS="api.lucysmirnova.ru",
        SMTP_REQUIRED_FOR_PAYMENT_EMAIL=False,
        SMTP_USER="",
        SMTP_PASSWORD="",
    )

    assert settings.SMTP_REQUIRED_FOR_PAYMENT_EMAIL is False
