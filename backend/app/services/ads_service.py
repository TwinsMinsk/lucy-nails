"""
Ad campaigns: private file storage, signed file links and the sync from the local ads pipeline.

Files live under ADS_STORAGE_DIR, never under the public uploads mount. The admin page gets
short-lived HMAC-signed links, so <video> and downloads work without cookies on the API host.
"""

import hashlib
import hmac
import logging
import re
import time
import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.models.ad import AdCalendarEntry, AdCampaign, AdComment, AdFile, AdMaterial, AdTask
from app.models.user import User
from app.schemas.ads import (
    AdCalendarEntryResponse,
    AdCampaignDetail,
    AdCampaignSummary,
    AdCampaignSync,
    AdCommentResponse,
    AdFileResponse,
    AdMaterialResponse,
    AdPerson,
    AdTaskResponse,
)

logger = logging.getLogger(__name__)

DEV_STORAGE_DIR = Path(__file__).resolve().parents[2] / ".ads-storage"
LINK_TTL_SECONDS = 12 * 3600
MAX_FILE_BYTES = 400 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024

# The content type always comes from this map, never from the client: files are served inline
# from the API host, so an uploaded HTML or SVG must not be able to run there.
CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".flac": "audio/flac",
    ".webm": "audio/webm",
    ".pdf": "application/pdf",
}
AUDIO_SUFFIXES = {suffix for suffix, kind in CONTENT_TYPES.items() if kind.startswith("audio/")}
TEAM_FILE_ROLES = {"voice", "other"}


class AdsStorageNotConfigured(Exception):
    pass


class AdFileRejected(ValueError):
    pass


class AdFileTooLarge(Exception):
    pass


# === Storage ===


def storage_root() -> Path | None:
    if settings.ADS_STORAGE_DIR:
        return Path(settings.ADS_STORAGE_DIR)
    return None if settings.is_deployed else DEV_STORAGE_DIR


def stored_path(storage_key: str) -> Path | None:
    root = storage_root()
    return root / storage_key if root else None


def clean_filename(name: str) -> tuple[str, str]:
    """Return a safe download name and its content type, or raise AdFileRejected."""
    base = Path(name.replace("\\", "/")).name.strip()
    suffix = Path(base).suffix.lower()
    if suffix not in CONTENT_TYPES:
        raise AdFileRejected(f"Unsupported file type: {suffix or 'none'}")
    stem = re.sub(r"[^\w.\- ]+", "_", Path(base).stem).strip(" ._") or "file"
    return f"{stem[:120]}{suffix}", CONTENT_TYPES[suffix]


async def store_stream(chunks: AsyncIterator[bytes], suffix: str) -> tuple[str, int, str]:
    """Write a stream into storage; return (storage_key, size, sha256)."""
    root = storage_root()
    if root is None:
        raise AdsStorageNotConfigured()
    name = uuid.uuid4().hex
    storage_key = f"{name[:2]}/{name}{suffix}"
    dest = root / storage_key
    partial = dest.with_name(dest.name + ".partial")
    digest = hashlib.sha256()
    size = 0
    await run_in_threadpool(dest.parent.mkdir, parents=True, exist_ok=True)
    try:
        out = await run_in_threadpool(partial.open, "wb")
        try:
            async for chunk in chunks:
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_FILE_BYTES:
                    raise AdFileTooLarge()
                digest.update(chunk)
                await run_in_threadpool(out.write, chunk)
        finally:
            await run_in_threadpool(out.close)
        if size == 0:
            raise AdFileRejected("Empty file")
        await run_in_threadpool(partial.replace, dest)
    finally:
        await run_in_threadpool(partial.unlink, missing_ok=True)
    return storage_key, size, digest.hexdigest()


async def discard_stored(storage_keys: list[str]) -> None:
    for key in storage_keys:
        path = stored_path(key)
        if path is not None:
            try:
                await run_in_threadpool(path.unlink, missing_ok=True)
            except OSError:
                logger.warning("Could not delete ad file %s", key, exc_info=True)


async def commit_file_changes(db: AsyncSession, *, added: list[str], replaced: list[str]) -> None:
    """Commit, then drop replaced files; on failure drop the files this request wrote."""
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        await discard_stored(added)
        raise
    await discard_stored(replaced)


# === Signed links ===


def _link_key() -> bytes:
    return hmac.new(settings.JWT_SECRET_KEY.encode(), b"ads-file-link", hashlib.sha256).digest()


def _signature(file_id: uuid.UUID, expires: int) -> str:
    return hmac.new(_link_key(), f"{file_id}:{expires}".encode(), hashlib.sha256).hexdigest()[:32]


def link_expiry(now: float | None = None) -> int:
    # Rounded to the hour so refetching the page keeps the same URLs and the browser cache.
    hour = int(now if now is not None else time.time()) // 3600 * 3600
    return hour + LINK_TTL_SECONDS


def file_links(file: AdFile) -> tuple[str, str]:
    expires = link_expiry()
    url = f"/ads/files/{file.id}?exp={expires}&sig={_signature(file.id, expires)}&v={file.sha256[:12]}"
    return url, f"{url}&download=1"


def verify_link(file_id: uuid.UUID, expires: int, signature: str) -> bool:
    if expires < time.time():
        return False
    return hmac.compare_digest(signature.encode(), _signature(file_id, expires).encode())


# === Files ===


async def put_file(
    db: AsyncSession,
    material: AdMaterial,
    *,
    key: str,
    role: str,
    filename: str,
    chunks: AsyncIterator[bytes],
    variant: str | None = None,
    label: str | None = None,
    uploaded_by: User | None = None,
) -> tuple[AdFile, str | None]:
    """Store a file under `key`, replacing an older one; return it and the replaced storage key."""
    name, content_type = clean_filename(filename)
    storage_key, size, sha256 = await store_stream(chunks, Path(name).suffix)
    file = next((f for f in material.files if f.key == key), None)
    replaced = file.storage_key if file else None
    if file is None:
        file = AdFile(key=key)
        material.files.append(file)
    file.role = role
    file.variant = variant
    file.label = label
    file.filename = name
    file.content_type = content_type
    file.size_bytes = size
    file.sha256 = sha256
    file.storage_key = storage_key
    file.uploaded_by = uploaded_by
    file.updated_at = datetime.utcnow()
    await db.flush()
    return file, replaced


# === Loading and serialization ===


def _campaign_options():
    return (
        selectinload(AdCampaign.materials).selectinload(AdMaterial.files).selectinload(AdFile.uploaded_by),
        selectinload(AdCampaign.tasks).selectinload(AdTask.done_by),
        selectinload(AdCampaign.calendar),
        selectinload(AdCampaign.comments).selectinload(AdComment.author),
    )


async def load_campaign(db: AsyncSession, *, campaign_id: uuid.UUID | None = None, slug: str | None = None):
    query = select(AdCampaign).options(*_campaign_options()).execution_options(populate_existing=True)
    query = query.where(AdCampaign.id == campaign_id) if campaign_id else query.where(AdCampaign.slug == slug)
    return await db.scalar(query)


async def load_material(db: AsyncSession, material_id: uuid.UUID) -> AdMaterial | None:
    return await db.scalar(
        select(AdMaterial)
        .where(AdMaterial.id == material_id)
        .options(selectinload(AdMaterial.files).selectinload(AdFile.uploaded_by))
        .execution_options(populate_existing=True)
    )


def person(user: User | None) -> AdPerson | None:
    if user is None:
        return None
    return AdPerson(id=user.id, name=user.full_name or user.email.split("@")[0])


def file_response(file: AdFile) -> AdFileResponse:
    url, download_url = file_links(file)
    return AdFileResponse(
        id=file.id,
        key=file.key,
        role=file.role,
        variant=file.variant,
        label=file.label,
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=file.size_bytes,
        sha256=file.sha256,
        uploaded_by=person(file.uploaded_by),
        created_at=file.created_at,
        updated_at=file.updated_at,
        url=url,
        download_url=download_url,
    )


def material_response(material: AdMaterial) -> AdMaterialResponse:
    return AdMaterialResponse(
        id=material.id,
        code=material.code,
        kind=material.kind,
        title=material.title,
        group_key=material.group_key,
        hook=material.hook,
        voiceover=material.voiceover,
        caption=material.caption,
        link_url=material.link_url,
        utm_content=material.utm_content,
        duration_seconds=material.duration_seconds,
        order_index=material.order_index,
        status=material.status,
        published_url=material.published_url,
        published_at=material.published_at,
        files=[file_response(f) for f in material.files],
    )


def task_response(task: AdTask) -> AdTaskResponse:
    return AdTaskResponse(
        id=task.id,
        key=task.key,
        title=task.title,
        note=task.note,
        order_index=task.order_index,
        done_at=task.done_at,
        done_by=person(task.done_by),
    )


def comment_response(comment: AdComment, viewer: User | None) -> AdCommentResponse:
    return AdCommentResponse(
        id=comment.id,
        material_id=comment.material_id,
        author=person(comment.author),
        body=comment.body,
        created_at=comment.created_at,
        is_mine=viewer is not None and comment.author_id == viewer.id,
    )


def campaign_detail(campaign: AdCampaign, viewer: User | None = None) -> AdCampaignDetail:
    return AdCampaignDetail(
        id=campaign.id,
        slug=campaign.slug,
        title=campaign.title,
        summary=campaign.summary,
        status=campaign.status,
        starts_on=campaign.starts_on,
        groups=campaign.groups or [],
        about=campaign.about or [],
        materials=[material_response(m) for m in campaign.materials],
        tasks=[task_response(t) for t in campaign.tasks],
        calendar=[
            AdCalendarEntryResponse(
                id=e.id, day=e.day, time=e.time, week=e.week, title=e.title, note=e.note, material_id=e.material_id
            )
            for e in campaign.calendar
        ],
        comments=[comment_response(c, viewer) for c in campaign.comments],
        updated_at=campaign.updated_at,
    )


def campaign_summary(campaign: AdCampaign) -> AdCampaignSummary:
    materials = campaign.materials
    cover = next(
        (f for m in materials for f in m.files if f.role == "cover" and f.variant is None),
        None,
    )
    return AdCampaignSummary(
        id=campaign.id,
        slug=campaign.slug,
        title=campaign.title,
        summary=campaign.summary,
        status=campaign.status,
        starts_on=campaign.starts_on,
        materials_total=len(materials),
        materials_ready=sum(m.status == "ready" for m in materials),
        materials_published=sum(m.status == "published" for m in materials),
        tasks_total=len(campaign.tasks),
        tasks_done=sum(t.done_at is not None for t in campaign.tasks),
        cover_url=file_links(cover)[0] if cover else None,
        updated_at=campaign.updated_at,
    )


async def list_campaigns(db: AsyncSession) -> list[AdCampaign]:
    result = await db.scalars(
        select(AdCampaign)
        .options(
            selectinload(AdCampaign.materials).selectinload(AdMaterial.files),
            selectinload(AdCampaign.tasks),
        )
        .order_by(AdCampaign.order_index, AdCampaign.created_at.desc())
    )
    return list(result)


# === Sync from the ads pipeline ===


async def sync_campaign(db: AsyncSession, slug: str, data: AdCampaignSync) -> tuple[AdCampaign, list[str]]:
    """Upsert the campaign text; return it and the storage keys of files dropped by `prune`."""
    campaign = await load_campaign(db, slug=slug)
    if campaign is None:
        campaign = AdCampaign(slug=slug, materials=[], tasks=[], calendar=[], comments=[])
        db.add(campaign)
    campaign.title = data.title
    campaign.summary = data.summary
    campaign.status = data.status
    campaign.starts_on = data.starts_on
    campaign.order_index = data.order_index
    campaign.groups = [g.model_dump() for g in data.groups]
    campaign.about = [s.model_dump() for s in data.about]
    campaign.updated_at = datetime.utcnow()

    dropped: list[str] = []
    materials = {m.code: m for m in campaign.materials}
    for item in data.materials:
        material = materials.get(item.code)
        if material is None:
            material = AdMaterial(code=item.code, status="draft", files=[])
            campaign.materials.append(material)
            materials[item.code] = material
        for field in (
            "kind", "title", "group_key", "hook", "voiceover", "caption",
            "link_url", "utm_content", "duration_seconds", "order_index",
        ):
            setattr(material, field, getattr(item, field))
    wanted = {item.code for item in data.materials}
    if data.prune:
        for material in [m for m in campaign.materials if m.code not in wanted]:
            dropped.extend(f.storage_key for f in material.files)
            campaign.materials.remove(material)
            del materials[material.code]

    tasks = {t.key: t for t in campaign.tasks}
    for item in data.tasks:
        task = tasks.get(item.key)
        if task is None:
            task = AdTask(key=item.key)
            campaign.tasks.append(task)
            tasks[item.key] = task
        task.title = item.title
        task.note = item.note
        task.order_index = item.order_index
    if data.prune:
        wanted_tasks = {item.key for item in data.tasks}
        for task in [t for t in campaign.tasks if t.key not in wanted_tasks]:
            campaign.tasks.remove(task)

    # The calendar holds no team state, so it is replaced as a whole.
    await db.flush()
    entries = {e.key: e for e in campaign.calendar}
    for item in data.calendar:
        entry = entries.pop(item.key, None)
        if entry is None:
            entry = AdCalendarEntry(key=item.key)
            campaign.calendar.append(entry)
        entry.day = item.day
        entry.time = item.time
        entry.week = item.week
        entry.title = item.title
        entry.note = item.note
        entry.order_index = item.order_index
        linked = materials.get(item.material_code) if item.material_code else None
        entry.material_id = linked.id if linked is not None else None
    for entry in entries.values():
        campaign.calendar.remove(entry)
    await db.flush()
    return campaign, dropped
