import pytest
from pydantic import ValidationError
from starlette.requests import Request

from app.core.config import Settings
from app.core.rate_limit import client_ip
from app.main import app


def _valid_prod(**overrides):
    """Build a Settings that passes validate_production_safety, with overrides."""
    kwargs = dict(
        _env_file=None,
        ENVIRONMENT="production",
        DEBUG=False,
        JWT_SECRET_KEY="production-secret-that-is-32-chars-min",
        MFA_ENCRYPTION_KEY="distinct-mfa-encryption-key-32-chars-min",
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
        COOKIE_DOMAIN="lucysmirnova.ru",
        TRUSTED_HOSTS="api.lucysmirnova.ru",
        REDIS_URL="redis://shared-redis.internal:6379/0",
        TELEGRAM_BOT_TOKEN="telegram-token",
        TELEGRAM_BOT_USERNAME="lucy_nails_bot",
        TELEGRAM_OWNER_CHAT_ID=123456789,
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


def test_production_config_requires_distinct_mfa_encryption_key():
    with pytest.raises(ValidationError) as exc_info:
        _valid_prod(MFA_ENCRYPTION_KEY="")

    assert "MFA_ENCRYPTION_KEY must be at least 32 characters" in str(exc_info.value)


def test_production_config_allows_smtp_disabled_for_registered_checkout_only():
    settings = _valid_prod(SMTP_REQUIRED_FOR_PAYMENT_EMAIL=False, RESEND_API_KEY="")

    assert settings.SMTP_REQUIRED_FOR_PAYMENT_EMAIL is False


def test_production_config_rejects_demo_mode():
    with pytest.raises(ValidationError) as exc_info:
        _valid_prod(PRODAMUS_DEMO_MODE=True)

    assert "PRODAMUS_DEMO_MODE must be false in production" in str(exc_info.value)


def test_isolated_staging_has_production_safety_and_demo_payments():
    config = _valid_prod(
        ENVIRONMENT="staging",
        PRODAMUS_DEMO_MODE=True,
        FRONTEND_URL="https://staging.lucysmirnova.ru",
        BACKEND_URL="https://api.staging.lucysmirnova.ru",
        COOKIE_DOMAIN="staging.lucysmirnova.ru",
        TRUSTED_HOSTS="api.staging.lucysmirnova.ru",
    )
    assert config.is_deployed
    with pytest.raises(ValidationError):
        _valid_prod(ENVIRONMENT="staging", DEBUG=True)
    with pytest.raises(ValidationError):
        _valid_prod(ENVIRONMENT="staging", PRODAMUS_DEMO_MODE=True)
    with pytest.raises(ValidationError):
        _valid_prod(ENVIRONMENT="staging", PRODAMUS_DEMO_MODE=False)


def test_production_config_requires_drm_signing_key():
    with pytest.raises(ValidationError) as exc_info:
        _valid_prod(KINESCOPE_JWT_PRIVATE_KEY_PEM="", KINESCOPE_JWK_KID="")

    assert "Kinescope DRM signing key is required in production" in str(exc_info.value)


def test_production_config_requires_drm_basic_auth():
    with pytest.raises(ValidationError) as exc_info:
        _valid_prod(KINESCOPE_DRM_BASIC_USER="", KINESCOPE_DRM_BASIC_PASS="")

    assert "KINESCOPE_DRM_BASIC_USER and KINESCOPE_DRM_BASIC_PASS are required" in str(
        exc_info.value
    )


def test_production_config_requires_shared_cookie_domain():
    with pytest.raises(ValidationError) as exc_info:
        _valid_prod(COOKIE_DOMAIN="")

    assert "COOKIE_DOMAIN is required in production" in str(exc_info.value)


def test_production_config_requires_shared_redis_rate_limit():
    with pytest.raises(ValidationError) as exc_info:
        _valid_prod(REDIS_URL="")

    assert "REDIS_URL is required in production" in str(exc_info.value)


def test_production_config_rejects_trusting_every_forwarded_sender():
    with pytest.raises(ValidationError) as exc_info:
        _valid_prod(FORWARDED_ALLOW_IPS="*")

    assert "FORWARDED_ALLOW_IPS must list trusted proxy" in str(exc_info.value)


def test_rate_limit_key_ignores_untrusted_forwarding_headers():
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [
                (b"x-forwarded-for", b"203.0.113.44"),
                (b"cf-connecting-ip", b"198.51.100.20"),
            ],
            "client": ("192.0.2.10", 12345),
            "server": ("test", 80),
            "scheme": "http",
            "query_string": b"",
        }
    )

    assert client_ip(request) == "192.0.2.10"


def test_production_config_requires_telegram_operations_channel():
    with pytest.raises(ValidationError) as exc_info:
        _valid_prod(TELEGRAM_BOT_TOKEN="", TELEGRAM_BOT_USERNAME="")

    assert "Telegram bot token and username are required" in str(exc_info.value)


@pytest.mark.parametrize("host", ["smtp.example.com", "mailpit.railway.internal"])
def test_production_rejects_disabled_smtp_starttls(host):
    with pytest.raises(ValidationError, match="SMTP_START_TLS"):
        _valid_prod(SMTP_HOST=host, SMTP_START_TLS=False)


@pytest.mark.parametrize(
    "host",
    [
        "smtp.example.com",
        "railway.internal",
        "mailpit.railway.internal.example.com",
        "localhost",
        "smtp.example.com@private.railway.internal",
    ],
)
def test_staging_rejects_cleartext_smtp_outside_private_railway(host):
    with pytest.raises(ValidationError, match="SMTP_START_TLS"):
        _valid_prod(
            ENVIRONMENT="staging",
            PRODAMUS_DEMO_MODE=True,
            FRONTEND_URL="https://staging.lucysmirnova.ru",
            BACKEND_URL="https://api.staging.lucysmirnova.ru",
            COOKIE_DOMAIN="staging.lucysmirnova.ru",
            SMTP_HOST=host,
            SMTP_START_TLS=False,
        )


def test_staging_allows_explicit_private_smtp_sink_without_starttls():
    config = _valid_prod(
        ENVIRONMENT="staging",
        PRODAMUS_DEMO_MODE=True,
        FRONTEND_URL="https://staging.lucysmirnova.ru",
        BACKEND_URL="https://api.staging.lucysmirnova.ru",
        COOKIE_DOMAIN="staging.lucysmirnova.ru",
        SMTP_HOST="mailpit.railway.internal",
        SMTP_START_TLS=False,
        RESEND_API_KEY="",
        SMTP_USER="sink-user",
        SMTP_PASSWORD="sink-password",
    )
    assert config.SMTP_START_TLS is False


@pytest.mark.parametrize("environment", ["development", "test"])
def test_local_smtp_can_disable_starttls(environment):
    config = Settings(
        _env_file=None,
        ENVIRONMENT=environment,
        SMTP_HOST="localhost",
        SMTP_START_TLS=False,
    )
    assert config.SMTP_START_TLS is False


def test_smtp_starttls_defaults_to_enabled(monkeypatch):
    monkeypatch.delenv("SMTP_START_TLS", raising=False)
    assert _valid_prod().SMTP_START_TLS is True
