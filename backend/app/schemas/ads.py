"""
Pydantic schemas for the ads section: the admin pages and the sync from the local ads pipeline.
"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

CampaignStatus = Literal["draft", "active", "finished"]
MaterialKind = Literal["reel", "photo", "story", "post", "other"]
MaterialStatus = Literal["draft", "ready", "published"]
FileRole = Literal["video", "cover", "photo", "voice", "other"]

KEY_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,63}$"


class AdGroup(BaseModel):
    key: str = Field(..., pattern=KEY_PATTERN)
    title: str = Field(..., min_length=1, max_length=120)
    note: str | None = Field(None, max_length=500)


class AdSection(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    body: str = Field(..., max_length=20_000)


# === Sync from the ads pipeline ===


class AdMaterialSync(BaseModel):
    code: str = Field(..., pattern=KEY_PATTERN, max_length=32)
    kind: MaterialKind = "reel"
    title: str = Field(..., min_length=1, max_length=255)
    group_key: str | None = Field(None, max_length=64)
    hook: str | None = Field(None, max_length=500)
    voiceover: str | None = Field(None, max_length=20_000)
    caption: str | None = Field(None, max_length=20_000)
    link_url: str | None = Field(None, max_length=500)
    utm_content: str | None = Field(None, max_length=100)
    duration_seconds: int | None = Field(None, ge=0, le=36_000)
    order_index: int = 0


class AdTaskSync(BaseModel):
    key: str = Field(..., pattern=KEY_PATTERN)
    title: str = Field(..., min_length=1, max_length=500)
    note: str | None = Field(None, max_length=5_000)
    order_index: int = 0


class AdCalendarSync(BaseModel):
    key: str = Field(..., pattern=KEY_PATTERN)
    day: date
    time: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")
    week: int | None = Field(None, ge=1, le=520)
    title: str = Field(..., min_length=1, max_length=2_000)
    note: str | None = Field(None, max_length=2_000)
    material_code: str | None = Field(None, max_length=32)
    order_index: int = 0


class AdCampaignSync(BaseModel):
    """Full campaign text. Materials and tasks are matched by code/key; the team's
    publishing status, task marks, files and comments survive every sync."""

    title: str = Field(..., min_length=1, max_length=255)
    summary: str | None = Field(None, max_length=2_000)
    status: CampaignStatus = "active"
    starts_on: date | None = None
    order_index: int = 0
    groups: list[AdGroup] = Field(default_factory=list, max_length=20)
    about: list[AdSection] = Field(default_factory=list, max_length=30)
    materials: list[AdMaterialSync] = Field(default_factory=list, max_length=200)
    tasks: list[AdTaskSync] = Field(default_factory=list, max_length=100)
    calendar: list[AdCalendarSync] = Field(default_factory=list, max_length=500)
    # Delete materials and tasks that are missing from this payload.
    prune: bool = False


# === Responses ===


class AdPerson(BaseModel):
    id: UUID
    name: str


class AdFileResponse(BaseModel):
    id: UUID
    key: str
    role: FileRole
    variant: str | None
    label: str | None
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    uploaded_by: AdPerson | None
    created_at: datetime
    updated_at: datetime
    # Signed links relative to the API root; they expire, refetch the campaign for fresh ones.
    url: str
    download_url: str


class AdCommentResponse(BaseModel):
    id: UUID
    material_id: UUID | None
    author: AdPerson | None
    body: str
    created_at: datetime
    is_mine: bool = False


class AdMaterialResponse(BaseModel):
    id: UUID
    code: str
    kind: MaterialKind
    title: str
    group_key: str | None
    hook: str | None
    voiceover: str | None
    caption: str | None
    link_url: str | None
    utm_content: str | None
    duration_seconds: int | None
    order_index: int
    status: MaterialStatus
    published_url: str | None
    published_at: datetime | None
    files: list[AdFileResponse]


class AdTaskResponse(BaseModel):
    id: UUID
    key: str
    title: str
    note: str | None
    order_index: int
    done_at: datetime | None
    done_by: AdPerson | None


class AdCalendarEntryResponse(BaseModel):
    id: UUID
    day: date
    time: str | None
    week: int | None
    title: str
    note: str | None
    material_id: UUID | None


class AdCampaignSummary(BaseModel):
    id: UUID
    slug: str
    title: str
    summary: str | None
    status: CampaignStatus
    starts_on: date | None
    materials_total: int
    materials_ready: int
    materials_published: int
    tasks_total: int
    tasks_done: int
    cover_url: str | None
    updated_at: datetime


class AdCampaignDetail(BaseModel):
    id: UUID
    slug: str
    title: str
    summary: str | None
    status: CampaignStatus
    starts_on: date | None
    groups: list[AdGroup]
    about: list[AdSection]
    materials: list[AdMaterialResponse]
    tasks: list[AdTaskResponse]
    calendar: list[AdCalendarEntryResponse]
    comments: list[AdCommentResponse]
    updated_at: datetime


# === Admin updates ===


class AdMaterialUpdate(BaseModel):
    status: MaterialStatus | None = None
    published_url: str | None = Field(None, max_length=500)


class AdTaskUpdate(BaseModel):
    done: bool


class AdCommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=5_000)
    material_id: UUID | None = None
