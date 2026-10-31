"""
Ad campaigns for the admin "Реклама" section: reels, their files, texts, posting calendar and tasks.

Text and files arrive from the local ads pipeline (`/api/internal/ads`); the team adds voice
recordings, comments, task marks and publishing status from the admin panel.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


CAMPAIGN_STATUSES = ("draft", "active", "finished")
MATERIAL_KINDS = ("reel", "photo", "story", "post", "other")
MATERIAL_STATUSES = ("draft", "ready", "published")
FILE_ROLES = ("video", "cover", "photo", "voice", "other")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class AdCampaign(Base):
    __tablename__ = "ad_campaigns"
    __table_args__ = (CheckConstraint(_in("status", CAMPAIGN_STATUSES), name="ck_ad_campaigns_status"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    starts_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    # [{key, title, note}]: how materials are grouped on the campaign page.
    groups: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # [{title, body}]: the "О кампании" tab.
    about: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    materials: Mapped[list["AdMaterial"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan", order_by="AdMaterial.order_index"
    )
    tasks: Mapped[list["AdTask"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan", order_by="AdTask.order_index"
    )
    calendar: Mapped[list["AdCalendarEntry"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="[AdCalendarEntry.day, AdCalendarEntry.order_index]",
    )
    comments: Mapped[list["AdComment"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan", order_by="AdComment.created_at"
    )


class AdMaterial(Base):
    __tablename__ = "ad_materials"
    __table_args__ = (
        UniqueConstraint("campaign_id", "code", name="uq_ad_materials_campaign_code"),
        CheckConstraint(_in("kind", MATERIAL_KINDS), name="ck_ad_materials_kind"),
        CheckConstraint(_in("status", MATERIAL_STATUSES), name="ck_ad_materials_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ad_campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="reel")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    group_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hook: Mapped[str | None] = mapped_column(String(500), nullable=True)
    voiceover: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    link_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    published_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    campaign: Mapped[AdCampaign] = relationship(back_populates="materials")
    files: Mapped[list["AdFile"]] = relationship(
        back_populates="material", cascade="all, delete-orphan", order_by="AdFile.created_at"
    )


class AdFile(Base):
    __tablename__ = "ad_files"
    __table_args__ = (
        UniqueConstraint("material_id", "key", name="uq_ad_files_material_key"),
        CheckConstraint(_in("role", FILE_ROLES), name="ck_ad_files_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    material_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ad_materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Stable identity within the material ("video", "cover", "video-b", "voice-<hex>").
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # Hook variant ("b", "c"); NULL for the main cut.
    variant: Mapped[str | None] = mapped_column(String(16), nullable=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    # Path relative to ADS_STORAGE_DIR; files are never served from the public uploads mount.
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    # NULL for files from the ads pipeline, set for files the team uploaded in the admin.
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    material: Mapped[AdMaterial] = relationship(back_populates="files")
    uploaded_by: Mapped["User | None"] = relationship()


class AdTask(Base):
    __tablename__ = "ad_tasks"
    __table_args__ = (UniqueConstraint("campaign_id", "key", name="uq_ad_tasks_campaign_key"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ad_campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    done_at: Mapped[datetime | None] = mapped_column(nullable=True)
    done_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    campaign: Mapped[AdCampaign] = relationship(back_populates="tasks")
    done_by: Mapped["User | None"] = relationship()


class AdCalendarEntry(Base):
    __tablename__ = "ad_calendar_entries"
    __table_args__ = (UniqueConstraint("campaign_id", "key", name="uq_ad_calendar_campaign_key"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ad_campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    material_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ad_materials.id", ondelete="SET NULL"), nullable=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    campaign: Mapped[AdCampaign] = relationship(back_populates="calendar")


class AdComment(Base):
    __tablename__ = "ad_comments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ad_campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    material_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ad_materials.id", ondelete="CASCADE"), nullable=True, index=True
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    campaign: Mapped[AdCampaign] = relationship(back_populates="comments")
    author: Mapped["User | None"] = relationship()
