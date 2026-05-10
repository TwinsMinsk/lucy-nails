"""
Public landing payload: hero + module copy + gallery for the home page SSR.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.course import Course
from app.models.gallery import GalleryItem
from app.models.module import Module
from app.schemas.landing import (
    GalleryItemResponse,
    LandingHeroResponse,
    LandingModuleResponse,
    LandingPayload,
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
        select(Course).where(Course.is_published.is_(True)).order_by(Course.created_at).limit(1)
    )
    course = course_result.scalars().first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No published course found",
        )

    modules_result = await db.execute(
        select(Module)
        .where(Module.course_id == course.id, Module.is_published.is_(True))
        .order_by(Module.order_index)
    )
    modules = modules_result.scalars().all()

    gallery_result = await db.execute(
        select(GalleryItem)
        .where(GalleryItem.is_published.is_(True))
        .order_by(GalleryItem.order_index, GalleryItem.created_at)
    )
    gallery = gallery_result.scalars().all()

    return LandingPayload(
        course_id=course.id,
        hero=LandingHeroResponse.model_validate(course),
        modules=[LandingModuleResponse.model_validate(m) for m in modules],
        gallery=[GalleryItemResponse.model_validate(g) for g in gallery],
    )
