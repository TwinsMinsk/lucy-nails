"""
Сервис для работы с Kinescope API.
"""

import httpx
from typing import Dict, Optional

from app.core.config import settings
from app.models.user import User


class KinescopeService:
    """Сервис для интеграции с Kinescope API v1."""
    
    BASE_URL = "https://api.kinescope.io/v1"
    MOCK_VIDEO_TITLE = "Demo Video"
    MOCK_VIDEO_DURATION = 600  # 10 минут
    MOCK_VIDEO_THUMBNAIL = "https://via.placeholder.com/1280x720/1a1a1a/ffffff?text=Video+Placeholder"
    MOCK_EMBED_URL = "https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=0"
    
    def __init__(self):
        """Инициализация сервиса."""
        self.api_key = settings.KINESCOPE_API_KEY
        self.is_mock_mode = not self.api_key or self.api_key == ""
        
    async def get_video_info(self, video_id: str) -> Dict:
        """
        Получить метаданные видео из Kinescope.
        
        Args:
            video_id: ID видео в Kinescope
            
        Returns:
            Словарь с метаданными видео (title, duration, poster)
        """
        if self.is_mock_mode:
            return self._get_mock_video_info(video_id)
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/videos/{video_id}",
                    headers=headers,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                return {
                    "title": data.get("title", "Untitled Video"),
                    "duration": data.get("duration", 0),
                    "poster": data.get("poster", {}).get("url", "")
                }
                
        except httpx.HTTPError as e:
            # В случае ошибки API возвращаем моковые данные
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
        if self.is_mock_mode:
            return self.MOCK_EMBED_URL
        
        # Базовая ссылка на embed
        base_embed_url = f"https://kinescope.io/embed/{video_id}"
        
        # Добавляем параметры для водяных знаков (DRM защита)
        # Kinescope поддерживает передачу email и external_id для отображения watermark
        watermark_params = f"?email={user.email}&external_id={user.id}"
        
        return base_embed_url + watermark_params
    
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
            "poster": self.MOCK_VIDEO_THUMBNAIL
        }


# Singleton instance
kinescope_service = KinescopeService()
