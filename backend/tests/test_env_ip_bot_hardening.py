"""Regression tests: ENVIRONMENT casing, client IP spoofing, bot token checks."""

import urllib.parse
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.requests import Request

import app.bot.services.auth as bot_auth_module
from app.bot.services.auth import BotAuthService
from app.core.config import Settings, settings
from app.core.rate_limit import client_ip
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    get_password_hash,
)
from app.models.user import User
from app.services.kinescope_service import KinescopeService
from app.services.prodamus_service import ProdamusService

CF_EDGE_IP = "162.158.1.1"  # inside Cloudflare's 162.158.0.0/15


# --- ENVIRONMENT casing -------------------------------------------------------


def test_settings_normalize_environment_case():
    s = Settings(_env_file=None, ENVIRONMENT=" Development ")
    assert s.ENVIRONMENT == "development"


def test_payment_link_has_no_demo_mode_for_capitalized_production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "Production")
    monkeypatch.setattr(settings, "PRODAMUS_DEMO_MODE", False)
    url = ProdamusService.generate_payment_link(
        course_name="Course",
        price=5900,
        tariff="self",
        order_id="course|11111111-1111-1111-1111-111111111111|self|deadbeef",
    )
    params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
    assert "demo_mode" not in params


def test_kinescope_treats_capitalized_production_as_production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "Production")
    assert KinescopeService()._production is True


# --- client_ip ------------------------------------------------------------------


def _request(headers: dict[str, str], peer: str = "10.0.0.1") -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (peer, 12345),
    }
    return Request(scope)


def test_client_ip_ignores_cf_header_from_non_cloudflare_peer():
    # Direct hit on the Railway origin: the attacker controls CF-Connecting-IP
    # and X-Forwarded-For, but Railway's X-Real-IP is the actual peer.
    req = _request(
        {
            "X-Real-IP": "203.0.113.7",
            "CF-Connecting-IP": "198.51.100.1",
            "X-Forwarded-For": "198.51.100.2",
        }
    )
    assert client_ip(req) == "203.0.113.7"


def test_client_ip_trusts_cf_header_from_cloudflare_peer():
    req = _request({"X-Real-IP": CF_EDGE_IP, "CF-Connecting-IP": "198.51.100.1"})
    assert client_ip(req) == "198.51.100.1"


def test_client_ip_cloudflare_peer_without_cf_header_uses_peer():
    req = _request({"X-Real-IP": CF_EDGE_IP})
    assert client_ip(req) == CF_EDGE_IP


def test_client_ip_ignores_spoofed_forwarded_headers_without_proxy():
    req = _request(
        {"CF-Connecting-IP": "198.51.100.1", "X-Forwarded-For": "198.51.100.2"},
        peer="192.0.2.10",
    )
    assert client_ip(req) == "192.0.2.10"


# --- Telegram bot link_account ----------------------------------------------


@pytest.fixture
def bot_session(db, monkeypatch):
    """Point the bot's direct async_session_maker() at the test database."""
    maker = async_sessionmaker(bind=db.bind, expire_on_commit=False)
    monkeypatch.setattr(bot_auth_module, "async_session_maker", maker)
    return maker


async def _make_user(db: AsyncSession, token_version: int = 0) -> User:
    user = User(
        email=f"bot-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=get_password_hash("botpass123"),
        role="student",
        token_version=token_version,
    )
    db.add(user)
    await db.commit()
    return user


def _tg_user(tg_id: int = 777):
    return SimpleNamespace(id=tg_id, username="tg_user")


async def _telegram_id(maker, user_id: uuid.UUID) -> int | None:
    async with maker() as session:
        user = await session.get(User, user_id)
        return user.telegram_id


@pytest.mark.asyncio
async def test_link_account_accepts_current_access_token(db, bot_session):
    user = await _make_user(db)
    token = create_access_token({"sub": str(user.id), "ver": 0})
    msg = await BotAuthService.link_account(token, _tg_user())
    assert msg.startswith("✅")
    assert await _telegram_id(bot_session, user.id) == 777


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["refresh", "reset"])
async def test_link_account_rejects_non_access_tokens(db, bot_session, kind):
    user = await _make_user(db)
    if kind == "refresh":
        token = create_refresh_token({"sub": str(user.id), "ver": 0})
    else:
        token = create_password_reset_token(user.id, 0)
    msg = await BotAuthService.link_account(token, _tg_user())
    assert not msg.startswith("✅")
    assert await _telegram_id(bot_session, user.id) is None


@pytest.mark.asyncio
async def test_link_account_rejects_stale_token_version(db, bot_session):
    user = await _make_user(db, token_version=1)
    token = create_access_token({"sub": str(user.id), "ver": 0})
    msg = await BotAuthService.link_account(token, _tg_user())
    assert not msg.startswith("✅")
    assert await _telegram_id(bot_session, user.id) is None
