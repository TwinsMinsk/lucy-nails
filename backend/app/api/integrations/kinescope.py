"""
Kinescope DRM Authorization Backend webhook.

Kinescope, видя у видео параметр `?drmauthtoken=<JWT>`, при попытке зрителя
воспроизвести защищённое DRM видео отправляет POST на этот endpoint с
JSON `{ id, ip, type, token, user_agent }`. Мы проверяем JWT, находим урок
и активную покупку, и отвечаем:
- 200 — разрешить (Kinescope выдаст ключ дешифровки)
- 403 — запретить (видео не воспроизведётся)

Аутентификация webhook'а — HTTP Basic с парой
KINESCOPE_DRM_BASIC_USER / KINESCOPE_DRM_BASIC_PASS, которая задана в
настройках проекта Kinescope (PUT /v1/drm/auth/{project_id}).
"""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from jose import JWTError
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.user import User
from app.services.kinescope_jwt_service import (
    KinescopeJwtNotConfiguredError,
    kinescope_jwt_service,
)
from app.services.lesson_service import LessonService


router = APIRouter()
_basic = HTTPBasic(auto_error=False)


class DrmAuthorizeRequest(BaseModel):
    """JSON, который Kinescope шлёт нам при попытке воспроизведения."""

    id: str = Field(..., description="ID видео в Kinescope (UUID)")
    token: str = Field("", description="Содержимое drmauthtoken (наш JWT)")
    ip: str | None = Field(None, description="IP зрителя")
    type: str | None = Field(None, description="Тип контента (обычно 'video')")
    user_agent: str | None = Field(None, description="User-Agent зрителя")


def _verify_basic_auth(
    credentials: HTTPBasicCredentials | None = Depends(_basic),
) -> None:
    """
    Сверяет Basic-Auth заголовок с настройками. Если auth-пара в env пустая,
    webhook считается незаконфигурированным — возвращает 503.
    """
    expected_user = (settings.KINESCOPE_DRM_BASIC_USER or "").strip()
    expected_pass = settings.KINESCOPE_DRM_BASIC_PASS or ""

    if not expected_user or not expected_pass:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DRM authorization backend is not configured",
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Basic auth required",
            headers={"WWW-Authenticate": 'Basic realm="kinescope-drm"'},
        )

    user_ok = secrets.compare_digest(credentials.username, expected_user)
    pass_ok = secrets.compare_digest(credentials.password, expected_pass)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid basic auth credentials",
            headers={"WWW-Authenticate": 'Basic realm="kinescope-drm"'},
        )


async def _find_lesson_by_video_id(db: AsyncSession, video_id: str) -> Lesson | None:
    """Ищет урок по `kinescope_video_id` (с подгрузкой module/course для access-check)."""
    query = (
        select(Lesson)
        .options(selectinload(Lesson.module).selectinload(Module.course))
        .where(Lesson.kinescope_video_id == video_id)
        .limit(1)
    )
    res = await db.execute(query)
    return res.scalars().first()


@router.post(
    "/drm/authorize",
    status_code=status.HTTP_200_OK,
    summary="DRM access check (called by Kinescope on playback)",
)
@limiter.limit("600/minute")
async def authorize_drm(
    request: Request,
    payload: DrmAuthorizeRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_verify_basic_auth),
):
    """
    Возвращает 200 (разрешить просмотр) или 403 (запретить).

    Логика:
    1. Валидируем JWT из `payload.token` — извлекаем `user_id`, `lesson_id` (опц).
    2. Берём активного пользователя.
    3. Находим урок: либо по `lesson_id` из JWT, либо fallback по
       `kinescope_video_id == payload.id`.
    4. Проверяем доступ через `LessonService.check_access` (превью / админ /
       активная Purchase).
    """
    if not payload.token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="missing drmauthtoken",
        )

    try:
        claims = kinescope_jwt_service.verify_drm_token(payload.token)
    except KinescopeJwtNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid drmauthtoken",
        ) from None

    user_res = await db.execute(select(User).where(User.id == claims.user_id))
    user = user_res.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="unknown user",
        )

    lesson: Lesson | None = None
    if claims.lesson_id:
        try:
            lesson = await LessonService.get_lesson_by_id(db, claims.lesson_id)
        except Exception:
            lesson = None

    if not lesson:
        lesson = await _find_lesson_by_video_id(db, payload.id)

    if not lesson:
        # Видео залито в Kinescope, но к уроку не привязано — это не наш сценарий.
        # На время промо-роликов на лендинге (если они тоже под DRM) можно
        # вернуть 200. Сейчас возвращаем 403 как безопасный default.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="lesson not found for video",
        )

    # Доп. защита: id видео из webhook должен совпадать с настройкой урока.
    if lesson.kinescope_video_id and lesson.kinescope_video_id != payload.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="video/lesson mismatch",
        )

    has_access = await LessonService.check_access(db, user, lesson)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="course access required",
        )

    return {"status": "allowed", "user_id": str(user.id), "lesson_id": str(lesson.id)}
