"""
API эндпоинты для курсов.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.course import CourseResponse, CourseListResponse
from app.schemas.module import ModuleResponse, ModuleWithLessonsResponse
from app.services.course_service import CourseService
from app.services.module_service import ModuleService


router = APIRouter()


@router.get("", response_model=CourseListResponse)
async def get_courses(
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список всех опубликованных курсов.
    
    Returns:
        Список курсов с количеством модулей и уроков
    """
    courses = await CourseService.get_courses(db, only_published=True)
    
    # Обогатить данные статистикой
    courses_with_stats = []
    for course in courses:
        stats = await CourseService.get_course_stats(db, course.id)
        course_data = CourseResponse.from_orm(course)
        course_data.modules_count = stats["modules_count"]
        course_data.lessons_count = stats["lessons_count"]
        course_data.total_duration = stats["total_duration"]
        courses_with_stats.append(course_data)
    
    return CourseListResponse(
        courses=courses_with_stats,
        total=len(courses_with_stats)
    )


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить детали курса по ID.
    
    Args:
        course_id: UUID курса
    
    Returns:
        Детали курса
    
    Raises:
        HTTPException 404: Курс не найден
    """
    course = await CourseService.get_course_by_id(db, course_id)
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    stats = await CourseService.get_course_stats(db, course_id)
    course_data = CourseResponse.from_orm(course)
    course_data.modules_count = stats["modules_count"]
    course_data.lessons_count = stats["lessons_count"]
    course_data.total_duration = stats["total_duration"]
    
    return course_data


@router.get("/{course_id}/modules", response_model=list[ModuleWithLessonsResponse])
async def get_course_modules(
    course_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список модулей курса с уроками.
    
    Args:
        course_id: UUID курса
    
    Returns:
        Список модулей с уроками
    """
    # Проверить существование курса
    course = await CourseService.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    modules = await ModuleService.get_course_modules(db, course_id, include_lessons=True)
    
    # Обогатить модули статистикой
    modules_with_stats = []
    for module in modules:
        stats = await ModuleService.get_module_stats(db, module.id)
        module_data = ModuleWithLessonsResponse.from_orm(module)
        module_data.lessons_count = stats["lessons_count"]
        module_data.total_duration = stats["total_duration"]
        modules_with_stats.append(module_data)
    
    return modules_with_stats


from app.api.auth import get_current_user
from app.models.user import User
from app.models.progress import Progress
from app.models.module import Module
from app.models.lesson import Lesson
from sqlalchemy import select, and_
from pydantic import BaseModel

class CourseProgressResponse(BaseModel):
    completed_lesson_ids: list[UUID]
    progress_percent: int

@router.get("/{course_id}/my-progress", response_model=CourseProgressResponse)
async def get_my_course_progress(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить прогресс пользователя по курсу.
    """
    # 1. Получаем все уроки курса для подсчета общего количества
    # Используем join для эффективности
    query_lessons = (
        select(Lesson.id)
        .join(Module, Module.id == Lesson.module_id)
        .where(Module.course_id == course_id)
    )
    result_lessons = await db.execute(query_lessons)
    all_lesson_ids = result_lessons.scalars().all()
    total_lessons = len(all_lesson_ids)

    if total_lessons == 0:
        return CourseProgressResponse(completed_lesson_ids=[], progress_percent=0)

    # 2. Получаем завершенные уроки пользователя для этого курса
    query_progress = (
        select(Progress.lesson_id)
        .where(
            and_(
                Progress.user_id == current_user.id,
                Progress.is_completed == True,
                Progress.lesson_id.in_(all_lesson_ids)
            )
        )
    )
    result_progress = await db.execute(query_progress)
    completed_lesson_ids = result_progress.scalars().all()
    
    completed_count = len(completed_lesson_ids)
    progress_percent = int((completed_count / total_lessons) * 100)
    
    return CourseProgressResponse(
        completed_lesson_ids=completed_lesson_ids,
        progress_percent=progress_percent
    )
