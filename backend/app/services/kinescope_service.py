"""
Сервис для работы с Kinescope API.
"""

import httpx
import urllib.parse
from typing import Dict

from app.core.config import settings
from app.models.user import User


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

    def get_embed_url(self, video_id: str, user: User) -> str:
        """
        Генерировать URL для iframe плеера с защитой.

        Args:
            video_id: ID видео в Kinescope
            user: Пользователь для watermark

        Returns:
            URL для embed с параметрами защиты
        """
        self._require_key_for_production()

        if self.is_mock_mode:
            return self.MOCK_EMBED_URL

        base_embed_url = f"https://kinescope.io/embed/{video_id}"
        q = urllib.parse.urlencode(
            {
                "email": user.email or "",
                "external_id": str(user.id),
            }
        )
        return f"{base_embed_url}?{q}"

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
