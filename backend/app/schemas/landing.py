"""
Pydantic schemas for the landing-page editor (hero / module copy / gallery).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class HeroStat(BaseModel):
    label: str = Field(..., min_length=1, max_length=120)
    value: str = Field(..., min_length=1, max_length=120)


class LandingHeroResponse(BaseModel):
    """Hero block payload merged with course-content.ts on the frontend."""

    landing_title: str | None = None
    landing_subtitle: str | None = None
    landing_description: str | None = None
    landing_audience: str | None = None
    landing_support_note: str | None = None
    landing_hero_stats: list[HeroStat] | None = None
    landing_benefits: list[str] | None = None
    landing_instructor_image_url: str | None = None

    class Config:
        from_attributes = True


class LandingHeroUpdate(BaseModel):
    """Admin update for course hero copy. All fields optional."""

    landing_title: str | None = Field(None, max_length=255)
    landing_subtitle: str | None = Field(None, max_length=500)
    landing_description: str | None = None
    landing_audience: str | None = None
    landing_support_note: str | None = None
    landing_hero_stats: list[HeroStat] | None = None
    landing_benefits: list[str] | None = None
    landing_instructor_image_url: str | None = Field(None, max_length=500)


class LandingModuleResponse(BaseModel):
    """Module landing copy payload (joined with module title/order)."""

    id: UUID
    title: str
    order_index: int
    landing_description: str | None = None
    landing_outcome: str | None = None
    landing_bullets: list[str] | None = None
    landing_mistakes: list[str] | None = None
    landing_duration_label: str | None = None

    class Config:
        from_attributes = True


class LandingModuleUpdate(BaseModel):
    landing_description: str | None = None
    landing_outcome: str | None = None
    landing_bullets: list[str] | None = None
    landing_mistakes: list[str] | None = None
    landing_duration_label: str | None = Field(None, max_length=32)


class GalleryItemBase(BaseModel):
    image_url: str = Field(..., min_length=1, max_length=500)
    title: str = Field(..., min_length=1, max_length=255)
    caption: str | None = None
    alt: str | None = Field(None, max_length=255)
    is_published: bool = True
    order_index: int = 0


class GalleryItemCreate(GalleryItemBase):
    pass


class GalleryItemUpdate(BaseModel):
    image_url: str | None = Field(None, min_length=1, max_length=500)
    title: str | None = Field(None, min_length=1, max_length=255)
    caption: str | None = None
    alt: str | None = Field(None, max_length=255)
    is_published: bool | None = None
    order_index: int | None = None


class GalleryItemResponse(GalleryItemBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GalleryReorderItem(BaseModel):
    id: UUID
    order_index: int


class LandingPayload(BaseModel):
    """Full landing payload returned by GET /api/landing for SSR."""

    course_id: UUID | None = None
    hero: LandingHeroResponse
    modules: list[LandingModuleResponse]
    gallery: list[GalleryItemResponse]
