"""
Сервис подписи и верификации JWT для авторизационного бэкенда Kinescope DRM.

Поток (см. Docs/integrations/KINESCOPE_AUTH_BACKEND.md):

1. Backend вкладывает короткоживущий JWT (RS256, ~5 мин) в URL плеера
   `?drmauthtoken=<JWT>`. Подписывает приватным ключом, который НИКОГДА
   не покидает сервер.
2. Когда зритель пытается воспроизвести защищённое DRM видео, Kinescope
   шлёт webhook на наш эндпоинт `/api/integrations/kinescope/drm/authorize`
   и кладёт этот же JWT в поле `token`.
3. Webhook парсит и верифицирует JWT через `verify_drm_token`, извлекает
   `user_id`/`lesson_id`, проверяет права доступа и отвечает 200/403.

Ассиметричная схема (RS256) выбрана по рекомендации Kinescope —
приватный ключ остаётся у нас, а в Kinescope заливается только публичный
JWK (см. scripts/kinescope/setup_drm.py).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from jose import JWTError, jwt
from jose.constants import ALGORITHMS

from app.core.config import settings


_JWT_AUDIENCE = "lucy-nails-drm"


class KinescopeJwtNotConfiguredError(RuntimeError):
    """Приватный ключ или kid не настроены — DRM-токены недоступны."""


@dataclass
class DrmTokenClaims:
    """Декодированные claims DRM-токена."""

    user_id: str
    email: str | None
    lesson_id: str | None
    issued_at: int
    expires_at: int


def _load_private_key_pem() -> str | None:
    """Загружает PEM приватного ключа: сначала из инлайн-env, потом из файла."""
    inline = (settings.KINESCOPE_JWT_PRIVATE_KEY_PEM or "").strip()
    if inline:
        # Railway удобно хранит многострочный PEM с экранированными \n
        return inline.replace("\\n", "\n")

    path = (settings.KINESCOPE_JWT_PRIVATE_KEY_PATH or "").strip()
    if path:
        p = Path(path)
        if p.is_file():
            return p.read_text(encoding="utf-8")
    return None


class KinescopeJwtService:
    """Подписывает / верифицирует RS256 JWT для DRM webhook."""

    ALGORITHM = ALGORITHMS.RS256

    def __init__(self) -> None:
        self._private_key_pem = _load_private_key_pem()
        self._kid = (settings.KINESCOPE_JWK_KID or "").strip() or None
        self._issuer = (settings.BACKEND_URL or "").rstrip("/") or "lucy-nails"
        self._ttl_seconds = int(settings.KINESCOPE_DRM_TOKEN_TTL_SECONDS or 300)
        self._public_key_pem: str | None = None
        if self._private_key_pem:
            try:
                priv = serialization.load_pem_private_key(
                    self._private_key_pem.encode("utf-8"), password=None
                )
                self._public_key_pem = (
                    priv.public_key()
                    .public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    )
                    .decode("utf-8")
                )
            except (ValueError, TypeError):
                # При битом PEM is_configured останется True по private+kid,
                # но verify упадёт более явно ниже.
                self._public_key_pem = None

    @property
    def is_configured(self) -> bool:
        return bool(self._private_key_pem and self._kid)

    def _require_configured(self) -> None:
        if not self.is_configured:
            raise KinescopeJwtNotConfiguredError(
                "Kinescope DRM JWT service not configured: "
                "KINESCOPE_JWT_PRIVATE_KEY_PATH/PEM and KINESCOPE_JWK_KID are required.",
            )

    def create_drm_token(
        self,
        *,
        user_id: str,
        email: str | None = None,
        lesson_id: str | None = None,
    ) -> str:
        """Возвращает короткоживущий JWT для query-параметра `drmauthtoken`."""
        self._require_configured()
        now = int(time.time())
        payload: dict[str, Any] = {
            "aud": _JWT_AUDIENCE,
            "iss": self._issuer,
            "iat": now,
            "nbf": now,
            "exp": now + self._ttl_seconds,
            "user_id": user_id,
        }
        if email:
            payload["email"] = email
        if lesson_id:
            payload["lesson_id"] = lesson_id

        return jwt.encode(
            payload,
            self._private_key_pem,
            algorithm=self.ALGORITHM,
            headers={"kid": self._kid},
        )

    def verify_drm_token(self, token: str) -> DrmTokenClaims:
        """
        Проверяет подпись и обязательные поля JWT, возвращает claims.

        Поднимает `JWTError`, если токен битый, истёк или подпись неверна.
        """
        self._require_configured()
        if not self._public_key_pem:
            raise JWTError("public key not derived; cannot verify")
        decoded = jwt.decode(
            token,
            self._public_key_pem,
            algorithms=[self.ALGORITHM],
            audience=_JWT_AUDIENCE,
            issuer=self._issuer,
            options={"require_exp": True, "require_iat": True, "require_nbf": False},
        )

        user_id = str(decoded.get("user_id") or "").strip()
        if not user_id:
            raise JWTError("user_id claim missing")

        return DrmTokenClaims(
            user_id=user_id,
            email=decoded.get("email"),
            lesson_id=decoded.get("lesson_id"),
            issued_at=int(decoded.get("iat", 0)),
            expires_at=int(decoded.get("exp", 0)),
        )


kinescope_jwt_service = KinescopeJwtService()
