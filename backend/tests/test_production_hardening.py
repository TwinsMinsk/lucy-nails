import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.main import app


def _valid_prod(**overrides):
    """Build a Settings that passes validate_production_safety, with overrides."""
    kwargs = dict(
        _env_file=None,
        ENVIRONMENT="production",
        DEBUG=False,
        JWT_SECRET_KEY="production-secret-that-is-32-chars-min",
        KINESCOPE_API_KEY="kinescope-key",
        KINESCOPE_JWT_PRIVATE_KEY_PEM="dummy-pem",
        KINESCOPE_JWK_KID="kid-test",
        KINESCOPE_DRM_BASIC_USER="drm-user",
        KINESCOPE_DRM_BASIC_PASS="drm-pass",
        PRODAMUS_URL="https://shop.payform.ru/",
        PRODAMUS_SECRET_KEY="prodamus-secret",
        PRODAMUS_SHOP_ID="shop-id",
        PRODAMUS_DEMO_MODE=False,
        FRONTEND_URL="https://lucysmirnova.ru",
        BACKEND_URL="https://api.lucysmirnova.ru",
        TRUSTED_HOSTS="api.lucysmirnova.ru",
        SMTP_REQUIRED_FOR_PAYMENT_EMAIL=True,
        RESEND_API_KEY="re_default_key",
        SMTP_USER="",
        SMTP_PASSWORD="",
    )
    kwargs.update(overrides)
    return Settings(**kwargs)


def test_app_registers_slowapi_middleware():
    middleware_names = {middleware.cls.__name__ for middleware in app.user_middleware}

    assert "SlowAPIMiddleware" in middleware_names


@pytest.mark.asyncio
async def test_health_endpoint_reports_ok_with_db(client):
    """Readiness probe returns ok when the database is reachable."""
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


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


def test_production_config_requires_email_transport():
    with pytest.raises(ValidationError) as exc_info:
        _valid_prod(RESEND_API_KEY="", SMTP_USER="", SMTP_PASSWORD="")

    assert "Email transport required in production" in str(exc_info.value)


def test_production_config_accepts_resend_api_key():
    settings = _valid_prod(RESEND_API_KEY="re_test_key")

    assert settings.RESEND_API_KEY == "re_test_key"


def test_production_config_allows_smtp_disabled_for_registered_checkout_only():
    settings = _valid_prod(SMTP_REQUIRED_FOR_PAYMENT_EMAIL=False, RESEND_API_KEY="")

    assert settings.SMTP_REQUIRED_FOR_PAYMENT_EMAIL is False


def test_production_config_rejects_demo_mode():
    with pytest.raises(ValidationError) as exc_info:
        _valid_prod(PRODAMUS_DEMO_MODE=True)

    assert "PRODAMUS_DEMO_MODE must be false in production" in str(exc_info.value)


def test_production_config_requires_drm_signing_key():
    with pytest.raises(ValidationError) as exc_info:
        _valid_prod(KINESCOPE_JWT_PRIVATE_KEY_PEM="", KINESCOPE_JWK_KID="")

    assert "Kinescope DRM signing key is required in production" in str(exc_info.value)


def test_production_config_requires_drm_basic_auth():
    with pytest.raises(ValidationError) as exc_info:
        _valid_prod(KINESCOPE_DRM_BASIC_USER="", KINESCOPE_DRM_BASIC_PASS="")

    assert "KINESCOPE_DRM_BASIC_USER and KINESCOPE_DRM_BASIC_PASS are required" in str(exc_info.value)
