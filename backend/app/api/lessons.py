"""
API эндпоинты для уроков.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.lesson import LessonDetailResponse, VideoPlayResponse
from app.schemas.progress import ProgressResponse, ProgressUpdate
from app.services.lesson_service import LessonService
from app.services.kinescope_service import kinescope_service


router = APIRouter()


@router.get("/{lesson_id}", response_model=LessonDetailResponse)
async def get_lesson(
    lesson_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить детали урока по ID.
    
    Args:
        lesson_id: UUID урока
        
    Returns:
        Детали урока (видео доступно только при наличии прав)
    """
    lesson, has_access = await LessonService.get_lesson_with_access(db, lesson_id, current_user)
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    # Формируем ответ
    response = LessonDetailResponse.from_orm(lesson)
    
    if not has_access:
        # Скрываем данные видео
        response.kinescope_video_id = None
        response.video_url = None
    else:
        # TODO: В будущем здесь будет генерация signed URL для Kinescope
        # Пока просто возвращаем ID как URL или placeholder
        if lesson.kinescope_video_id:
             response.video_url = f"https://kinescope.io/embed/{lesson.kinescope_video_id}"
    
    return response


@router.post("/{lesson_id}/progress", response_model=ProgressResponse)
async def update_lesson_progress(
    lesson_id: UUID,
    progress_data: ProgressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обновить прогресс просмотра урока.
    
    Args:
        lesson_id: UUID урока
        progress_data: Данные прогресса
        
    Returns:
        Обновленный прогресс
    """
    # 1. Проверяем существование урока и доступ
    lesson, has_access = await LessonService.get_lesson_with_access(db, lesson_id, current_user)
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
        
    if not has_access:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # 2. Обновляем прогресс
    progress = await LessonService.update_progress(
        db, 
        current_user.id, 
        lesson_id, 
        progress_data
    )
    
    return progress


@router.get("/{lesson_id}/play", response_model=VideoPlayResponse)
async def get_lesson_play_url(
    lesson_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить URL для воспроизведения видео урока.
    
    Проверяет права доступа:
    - Пользователь авторизован (через get_current_user)
    - Есть активная покупка курса ИЛИ пользователь админ
    
    Args:
        lesson_id: UUID урока
        
    Returns:
        Данные для воспроизведения (video_url, provider, title)
        
    Raises:
        404: Урок не найден
        403: Нет доступа к курсу
    """
    # 1. Получаем урок и проверяем доступ
    lesson, has_access = await LessonService.get_lesson_with_access(db, lesson_id, current_user)
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Course access required. Please purchase the course to watch this lesson."
        )
    
    # 2. Проверяем наличие video_id
    if not lesson.kinescope_video_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not configured for this lesson"
        )
    
    # 3. Генерируем защищенный URL через KinescopeService
    video_url = kinescope_service.get_embed_url(
        video_id=lesson.kinescope_video_id,
        user=current_user
    )
    
    return VideoPlayResponse(
        video_url=video_url,
        provider="kinescope",
        title=lesson.title
    )
