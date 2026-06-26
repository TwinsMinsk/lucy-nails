"""
Тесты для Kinescope DRM Authorization Backend.

Покрывают:
  - подпись/верификацию RS256 JWT (KinescopeJwtService);
  - happy-path и отказы webhook /api/integrations/kinescope/drm/authorize.
"""

from __future__ import annotations

import base64
import time
import uuid
from datetime import datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.purchase import Purchase
from app.models.user import User
from app.services.kinescope_jwt_service import (
    KinescopeJwtNotConfiguredError,
    KinescopeJwtService,
)


def _basic_auth_header(user: str, password: str) -> str:
    raw = f"{user}:{password}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _generate_pem() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem.decode("utf-8")


@pytest.fixture()
def configured_drm(monkeypatch):
    """Поднимает валидную DRM-конфигурацию на время теста."""
    pem = _generate_pem()
    monkeypatch.setattr(settings, "KINESCOPE_JWT_PRIVATE_KEY_PEM", pem)
    monkeypatch.setattr(settings, "KINESCOPE_JWT_PRIVATE_KEY_PATH", "")
    monkeypatch.setattr(settings, "KINESCOPE_JWK_KID", "test-kid")
    monkeypatch.setattr(settings, "KINESCOPE_DRM_BASIC_USER", "kinescope-drm")
    monkeypatch.setattr(settings, "KINESCOPE_DRM_BASIC_PASS", "test-pass-123")
    monkeypatch.setattr(settings, "KINESCOPE_DRM_TOKEN_TTL_SECONDS", 300)
    monkeypatch.setattr(settings, "BACKEND_URL", "https://api.test.local")
    # The webhook endpoint holds a module-level kinescope_jwt_service built at
    # import time (before these settings were patched). Rebuild it so the endpoint
    # verifies tokens with the same freshly-configured key.
    import app.api.integrations.kinescope as _kin_endpoint

    monkeypatch.setattr(_kin_endpoint, "kinescope_jwt_service", KinescopeJwtService())
    yield


def test_jwt_service_not_configured(monkeypatch):
    """Без приватного ключа сервис должен явно отказывать."""
    monkeypatch.setattr(settings, "KINESCOPE_JWT_PRIVATE_KEY_PEM", "")
    monkeypatch.setattr(settings, "KINESCOPE_JWT_PRIVATE_KEY_PATH", "")
    monkeypatch.setattr(settings, "KINESCOPE_JWK_KID", "")

    svc = KinescopeJwtService()
    assert svc.is_configured is False
    with pytest.raises(KinescopeJwtNotConfiguredError):
        svc.create_drm_token(user_id="u1")


def test_jwt_roundtrip(configured_drm):
    """Успешный roundtrip: подписали → верифицировали."""
    svc = KinescopeJwtService()
    user_id = str(uuid.uuid4())
    lesson_id = str(uuid.uuid4())
    token = svc.create_drm_token(
        user_id=user_id, email="user@example.com", lesson_id=lesson_id
    )
    claims = svc.verify_drm_token(token)
    assert claims.user_id == user_id
    assert claims.email == "user@example.com"
    assert claims.lesson_id == lesson_id
    assert claims.expires_at - claims.issued_at == 300


def test_jwt_rejects_tampered_token(configured_drm):
    """Изменённая подпись/payload — JWTError."""
    from jose import JWTError

    svc = KinescopeJwtService()
    token = svc.create_drm_token(user_id="u1")
    parts = token.split(".")
    parts[-1] = "AAAA" + parts[-1][4:]
    bad = ".".join(parts)
    with pytest.raises(JWTError):
        svc.verify_drm_token(bad)


def test_jwt_rejects_expired(configured_drm, monkeypatch):
    """Истёкший токен — JWTError."""
    from jose import JWTError

    monkeypatch.setattr(settings, "KINESCOPE_DRM_TOKEN_TTL_SECONDS", 1)
    svc = KinescopeJwtService()
    token = svc.create_drm_token(user_id="u1")
    time.sleep(2)
    with pytest.raises(JWTError):
        svc.verify_drm_token(token)


# ---- webhook endpoint integration tests ----


async def _seed_course(
    db: AsyncSession,
    *,
    with_paid_purchase: bool,
    video_id: str = "vid-abc",
) -> tuple[User, Lesson]:
    """Создаёт минимальную цепочку Course/Module/Lesson/User (+опц. Purchase)."""
    user = User(
        id=uuid.uuid4(),
        email="buyer@example.com",
        password_hash="x",
        role="student",
    )
    course = Course(
        id=uuid.uuid4(),
        title="Test Course",
        price_self=5900,
        price_support=11900,
        is_published=True,
    )
    module = Module(
        id=uuid.uuid4(),
        course_id=course.id,
        title="M1",
        order_index=1,
        is_published=True,
    )
    lesson = Lesson(
        id=uuid.uuid4(),
        module_id=module.id,
        title="L1",
        kinescope_video_id=video_id,
        duration_seconds=600,
        order_index=1,
        is_preview=False,
    )
    db.add_all([user, course, module, lesson])
    if with_paid_purchase:
        purchase = Purchase(
            id=uuid.uuid4(),
            user_id=user.id,
            course_id=course.id,
            tariff="self",
            amount_kopecks=590000,
            payment_status="success",
            expires_at=datetime.utcnow() + timedelta(days=10),
        )
        db.add(purchase)
    await db.commit()
    return user, lesson


@pytest.mark.asyncio
async def test_drm_authorize_503_when_not_configured(client: AsyncClient, monkeypatch):
    """Если basic auth не настроен — webhook отвечает 503."""
    monkeypatch.setattr(settings, "KINESCOPE_DRM_BASIC_USER", "")
    monkeypatch.setattr(settings, "KINESCOPE_DRM_BASIC_PASS", "")
    r = await client.post(
        "/api/integrations/kinescope/drm/authorize",
        json={"id": "vid-x", "token": ""},
    )
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_drm_authorize_401_no_basic(client: AsyncClient, configured_drm):
    """Без Basic Auth — 401."""
    r = await client.post(
        "/api/integrations/kinescope/drm/authorize",
        json={"id": "vid-x", "token": ""},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_drm_authorize_401_bad_basic(client: AsyncClient, configured_drm):
    """С неправильным Basic Auth — 401."""
    r = await client.post(
        "/api/integrations/kinescope/drm/authorize",
        json={"id": "vid-x", "token": ""},
        headers={"Authorization": _basic_auth_header("hax", "pwn")},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_drm_authorize_403_no_token(client: AsyncClient, configured_drm):
    """Basic ОК, но drmauthtoken пустой — 403."""
    r = await client.post(
        "/api/integrations/kinescope/drm/authorize",
        json={"id": "vid-x", "token": ""},
        headers={"Authorization": _basic_auth_header("kinescope-drm", "test-pass-123")},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_drm_authorize_403_invalid_token(client: AsyncClient, configured_drm):
    """Битый JWT — 403."""
    r = await client.post(
        "/api/integrations/kinescope/drm/authorize",
        json={"id": "vid-x", "token": "not-a-jwt"},
        headers={"Authorization": _basic_auth_header("kinescope-drm", "test-pass-123")},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_drm_authorize_200_when_paid(
    client: AsyncClient, db: AsyncSession, configured_drm
):
    """Активная покупка → 200."""
    from app.services.kinescope_jwt_service import KinescopeJwtService

    user, lesson = await _seed_course(db, with_paid_purchase=True, video_id="vid-paid")
    token = KinescopeJwtService().create_drm_token(
        user_id=str(user.id), email=user.email, lesson_id=str(lesson.id)
    )
    r = await client.post(
        "/api/integrations/kinescope/drm/authorize",
        json={"id": "vid-paid", "token": token, "ip": "1.2.3.4", "type": "video"},
        headers={"Authorization": _basic_auth_header("kinescope-drm", "test-pass-123")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "allowed"
    assert body["lesson_id"] == str(lesson.id)


@pytest.mark.asyncio
async def test_drm_authorize_403_without_purchase(
    client: AsyncClient, db: AsyncSession, configured_drm
):
    """Нет активной покупки → 403."""
    from app.services.kinescope_jwt_service import KinescopeJwtService

    user, lesson = await _seed_course(db, with_paid_purchase=False, video_id="vid-free")
    token = KinescopeJwtService().create_drm_token(
        user_id=str(user.id), email=user.email, lesson_id=str(lesson.id)
    )
    r = await client.post(
        "/api/integrations/kinescope/drm/authorize",
        json={"id": "vid-free", "token": token},
        headers={"Authorization": _basic_auth_header("kinescope-drm", "test-pass-123")},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_drm_authorize_403_video_mismatch(
    client: AsyncClient, db: AsyncSession, configured_drm
):
    """Если video_id из webhook не совпадает с уроком в JWT → 403."""
    from app.services.kinescope_jwt_service import KinescopeJwtService

    user, lesson = await _seed_course(db, with_paid_purchase=True, video_id="vid-real")
    token = KinescopeJwtService().create_drm_token(
        user_id=str(user.id), email=user.email, lesson_id=str(lesson.id)
    )
    r = await client.post(
        "/api/integrations/kinescope/drm/authorize",
        json={"id": "vid-OTHER", "token": token},
        headers={"Authorization": _basic_auth_header("kinescope-drm", "test-pass-123")},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_embed_url_includes_drm_token_when_configured(configured_drm):
    """`get_embed_url` подкладывает drmauthtoken и watermark в реальном режиме."""
    from app.services.kinescope_service import KinescopeService

    svc = KinescopeService()
    if svc.is_mock_mode:
        pytest.skip("mock mode active (no KINESCOPE_API_KEY in test env)")

    fake_user = User(
        id=uuid.uuid4(),
        email="drm@example.com",
        password_hash="x",
        role="student",
    )
    url = svc.get_embed_url("vid-1", fake_user, lesson_id=uuid.uuid4())
    assert "drmauthtoken=" in url
    assert "watermark=" in url
