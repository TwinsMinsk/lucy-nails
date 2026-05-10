"""
Admin endpoints for landing-page editor: course hero, module landing copy and gallery CRUD.
"""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.course import Course
from app.models.gallery import GalleryItem
from app.models.module import Module
from app.models.user import User
from app.schemas.landing import (
    GalleryItemCreate,
    GalleryItemResponse,
    GalleryItemUpdate,
    GalleryReorderItem,
    LandingHeroResponse,
    LandingHeroUpdate,
    LandingModuleResponse,
    LandingModuleUpdate,
)


router = APIRouter()


# === Course hero ===

@router.get("/courses/{course_id}/landing-hero", response_model=LandingHeroResponse)
async def get_course_landing_hero(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> LandingHeroResponse:
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return LandingHeroResponse.model_validate(course)


@router.put("/courses/{course_id}/landing-hero", response_model=LandingHeroResponse)
async def update_course_landing_hero(
    course_id: UUID,
    data: LandingHeroUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> LandingHeroResponse:
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    update_data = data.model_dump(exclude_unset=True)
    # heroStats is list[HeroStat]; serialize back to plain dicts for JSON column.
    if "landing_hero_stats" in update_data and update_data["landing_hero_stats"] is not None:
        update_data["landing_hero_stats"] = [
            stat.model_dump() if hasattr(stat, "model_dump") else stat
            for stat in update_data["landing_hero_stats"]
        ]
    for key, value in update_data.items():
        setattr(course, key, value)

    await db.commit()
    await db.refresh(course)
    return LandingHeroResponse.model_validate(course)


# === Module landing copy ===

@router.get("/courses/{course_id}/landing-modules", response_model=list[LandingModuleResponse])
async def list_course_landing_modules(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> list[LandingModuleResponse]:
    result = await db.execute(
        select(Module).where(Module.course_id == course_id).order_by(Module.order_index)
    )
    modules = result.scalars().all()
    return [LandingModuleResponse.model_validate(m) for m in modules]


@router.put("/modules/{module_id}/landing", response_model=LandingModuleResponse)
async def update_module_landing(
    module_id: UUID,
    data: LandingModuleUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> LandingModuleResponse:
    module = await db.get(Module, module_id)
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(module, key, value)

    await db.commit()
    await db.refresh(module)
    return LandingModuleResponse.model_validate(module)


# === Gallery CRUD ===

@router.get("/gallery", response_model=list[GalleryItemResponse])
async def list_gallery(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> list[GalleryItemResponse]:
    result = await db.execute(
        select(GalleryItem).order_by(GalleryItem.order_index, GalleryItem.created_at)
    )
    return [GalleryItemResponse.model_validate(g) for g in result.scalars().all()]


@router.post("/gallery", response_model=GalleryItemResponse, status_code=status.HTTP_201_CREATED)
async def create_gallery_item(
    data: GalleryItemCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> GalleryItemResponse:
    item = GalleryItem(id=uuid4(), **data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return GalleryItemResponse.model_validate(item)


@router.put("/gallery/reorder", response_model=list[GalleryItemResponse])
async def reorder_gallery(
    items: list[GalleryReorderItem],
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> list[GalleryItemResponse]:
    if not items:
        return []
    ids = [it.id for it in items]
    result = await db.execute(select(GalleryItem).where(GalleryItem.id.in_(ids)))
    by_id = {g.id: g for g in result.scalars().all()}
    missing = [str(i) for i in ids if i not in by_id]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gallery items not found: {', '.join(missing)}",
        )
    for it in items:
        by_id[it.id].order_index = it.order_index
    await db.commit()

    result = await db.execute(
        select(GalleryItem).order_by(GalleryItem.order_index, GalleryItem.created_at)
    )
    return [GalleryItemResponse.model_validate(g) for g in result.scalars().all()]


@router.put("/gallery/{item_id}", response_model=GalleryItemResponse)
async def update_gallery_item(
    item_id: UUID,
    data: GalleryItemUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> GalleryItemResponse:
    item = await db.get(GalleryItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gallery item not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return GalleryItemResponse.model_validate(item)


@router.delete("/gallery/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gallery_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> None:
    item = await db.get(GalleryItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gallery item not found")
    await db.delete(item)
    await db.commit()
