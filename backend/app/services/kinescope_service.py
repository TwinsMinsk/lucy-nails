"""
Сервис для работы с Kinescope API.
"""

import httpx
import urllib.parse
from typing import Dict
from uuid import UUID

from app.core.config import settings
from app.models.user import User
from app.services.kinescope_jwt_service import (
    KinescopeJwtNotConfiguredError,
    kinescope_jwt_service,
)


class KinescopeNotConfiguredError(RuntimeError):
    """Kinescope не настроен (production без API-ключа)."""


class KinescopeService:
    """Сервис для интеграции с Kinescope API v1."""

    BASE_URL = "https://api.kinescope.io/v1"
    MOCK_VIDEO_TITLE = "Demo Video"
    MOCK_VIDEO_DURATION = 600  # 10 минут
    MOCK_VIDEO_THUMBNAIL = "https://via.placeholder.com/1280x720/1a1a1a/ffffff?text=Video+Placeholder"
    MOCK_EMBED_URL = "https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=0"

    def __init__(self):
        """Инициализация сервиса."""
        self.api_key = (settings.KINESCOPE_API_KEY or "").strip()
        self._production = settings.ENVIRONMENT == "production"
        # В development/test без ключа разрешён mock; в production — нет
        self.is_mock_mode = not self.api_key

    def _require_key_for_production(self) -> None:
        if self._production and self.is_mock_mode:
            raise KinescopeNotConfiguredError(
                "KINESCOPE_API_KEY is required in production; mock embed is disabled.",
            )

    async def get_video_info(self, video_id: str) -> Dict:
        """
        Получить метаданные видео из Kinescope.

        Args:
            video_id: ID видео в Kinescope

        Returns:
            Словарь с метаданными видео (title, duration, poster)
        """
        self._require_key_for_production()

        if self.is_mock_mode:
            return self._get_mock_video_info(video_id)

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/videos/{video_id}",
                    headers=headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "title": data.get("title", "Untitled Video"),
                    "duration": data.get("duration", 0),
                    "poster": data.get("poster", {}).get("url", ""),
                }

        except httpx.HTTPError as e:
            if self._production:
                raise RuntimeError(f"Kinescope API error: {e}") from e
            print(f"Kinescope API error: {e}. Falling back to mock mode.")
            return self._get_mock_video_info(video_id)

    def get_embed_url(
        self,
        video_id: str,
        user: User,
        *,
        lesson_id: UUID | str | None = None,
    ) -> str:
        """
        Генерировать URL для iframe плеера с защитой.

        Если настроен KinescopeJwtService (приватный ключ + kid), вкладывает
        короткоживущий JWT в `drmauthtoken` — Kinescope при воспроизведении
        дёрнет наш webhook /api/integrations/kinescope/drm/authorize.

        Параметр `watermark` всегда содержит email/ID пользователя — это видно
        на видео и помогает идентифицировать источник утечки (если в шаблоне
        плеера включены динамические водяные знаки).

        Args:
            video_id: ID видео в Kinescope
            user: Авторизованный пользователь
            lesson_id: UUID урока, для дополнительной привязки в JWT

        Returns:
            URL для embed с параметрами защиты
        """
        self._require_key_for_production()

        if self.is_mock_mode:
            return self.MOCK_EMBED_URL

        base_embed_url = f"https://kinescope.io/embed/{video_id}"
        params: dict[str, str] = {
            # Динамический ватермарк: текст видно поверх видео,
            # если в шаблоне плеера включена опция «Водяной знак».
            "watermark": user.email or str(user.id),
        }

        # Если auth backend настроен — подписываем короткоживущий JWT и кладём
        # в drmauthtoken. Kinescope передаст его в webhook авторизации.
        if kinescope_jwt_service.is_configured:
            try:
                token = kinescope_jwt_service.create_drm_token(
                    user_id=str(user.id),
                    email=user.email,
                    lesson_id=str(lesson_id) if lesson_id else None,
                )
                params["drmauthtoken"] = token
            except KinescopeJwtNotConfiguredError:
                # На случай ошибки конфигурации не ломаем embed —
                # видео откроется, но без серверной авторизации DRM.
                pass

        return f"{base_embed_url}?{urllib.parse.urlencode(params)}"

    async def upload_video_file(
        self,
        file_path: str,
        title: str,
        description: str = "",
        parent_id: str | None = None,
    ) -> dict:
        """
        Загрузка MP4 в Kinescope (uploader v2, один POST).
        Требуются KINESCOPE_API_KEY и KINESCOPE_PROJECT_ID.
        """
        self._require_key_for_production()
        if self.is_mock_mode:
            return {
                "id": "mock-promo-id",
                "poster": self.MOCK_VIDEO_THUMBNAIL,
                "title": title,
            }

        import pathlib

        path = pathlib.Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(file_path)

        pid = (parent_id or settings.KINESCOPE_PROJECT_ID or "").strip()
        if not pid:
            raise RuntimeError("KINESCOPE_PROJECT_ID is required for upload")

        body = path.read_bytes()
        url = "https://uploader.kinescope.io/v2/video"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Parent-ID": pid,
            "X-Video-Title": title[:500],
            "Content-Type": "video/mp4",
        }
        if description:
            headers["X-Video-Description"] = description[:2000]

        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(url, headers=headers, content=body)
            response.raise_for_status()

        try:
            data = response.json()
        except Exception:
            data = {}

        vid = (
            data.get("id")
            or (data.get("data") or {}).get("id")
            or (data.get("data") or {}).get("video_id")
        )
        if not vid:
            loc = response.headers.get("Location") or ""
            if "/videos/" in loc:
                vid = loc.rstrip("/").split("/")[-1]

        if not vid:
            raise RuntimeError("Upload response missing video id")

        poster_url = None
        if isinstance(data.get("poster"), dict):
            poster_url = data["poster"].get("url")

        if not poster_url:
            async with httpx.AsyncClient(timeout=30.0) as client:
                info_r = await client.get(
                    f"{self.BASE_URL}/videos/{vid}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                if info_r.is_success:
                    info = info_r.json()
                    poster_url = (info.get("poster") or {}).get("url")

        if not poster_url:
            poster_url = f"https://kinescope.io/{vid}/poster.jpg"

        return {"id": vid, "poster": poster_url, "title": title}

    def _get_mock_video_info(self, video_id: str) -> Dict:
        """
        Возвращает моковые данные для разработки.

        Args:
            video_id: ID видео

        Returns:
            Словарь с фейковыми метаданными
        """
        return {
            "title": self.MOCK_VIDEO_TITLE,
            "duration": self.MOCK_VIDEO_DURATION,
            "poster": self.MOCK_VIDEO_THUMBNAIL,
        }


# Singleton instance
kinescope_service = KinescopeService()
