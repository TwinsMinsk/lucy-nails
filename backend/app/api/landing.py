"""
Public landing payload: hero + module copy + gallery for the home page SSR.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.course import Course
from app.models.gallery import GalleryItem
from app.models.module import Module
from app.models.lesson import Lesson
from app.schemas.landing import (
    GalleryItemResponse,
    LandingHeroResponse,
    LandingModuleResponse,
    LandingPayload,
    LandingCourseSnapshot,
)

router = APIRouter()


@router.get("", response_model=LandingPayload)
async def get_landing(db: AsyncSession = Depends(get_db)) -> LandingPayload:
    """Return hero, module landing copy and gallery for the public landing page.

    The hero comes from the first published course; module copy from its
    published modules; gallery is global (all published items ordered by
    order_index).
    """
    course_result = await db.execute(
        select(Course).where(Course.is_published.is_(True)).order_by(Course.created_at, Course.id).limit(1)
    )
    course = course_result.scalars().first()
    if not course:
        return LandingPayload(hero=LandingHeroResponse(), modules=[], gallery=[])

    modules_result = await db.execute(
        select(Module)
        .where(Module.course_id == course.id, Module.is_published.is_(True))
        .order_by(Module.order_index, Module.created_at, Module.id)
    )
    modules = modules_result.scalars().all()

    gallery_result = await db.execute(
        select(GalleryItem)
        .where(GalleryItem.is_published.is_(True))
        .order_by(GalleryItem.order_index, GalleryItem.created_at)
    )
    gallery = gallery_result.scalars().all()

    lessons_count, total_duration = (await db.execute(
        select(func.count(Lesson.id), func.coalesce(func.sum(Lesson.duration_seconds), 0))
        .join(Module, Module.id == Lesson.module_id)
        .where(Module.course_id == course.id, Module.is_published.is_(True))
    )).one()

    return LandingPayload(
        course_id=course.id,
        course=LandingCourseSnapshot(id=course.id, title=course.title, price_self=course.price_self, access_days=course.access_days, lessons_count=lessons_count, total_duration=total_duration),
        hero=LandingHeroResponse.model_validate(course),
        modules=[LandingModuleResponse.model_validate(m) for m in modules],
        gallery=[GalleryItemResponse.model_validate(g) for g in gallery],
    )
