"""
Admin "Реклама" section: campaigns with reels, texts, calendar and tasks.

`ads.read` views and downloads; `ads.manage` uploads voice recordings, comments, ticks tasks and
marks materials as published. Campaign text and pipeline files arrive through `ads_internal.py`.
"""

import uuid
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.ad import AdCampaign, AdComment, AdFile, AdMaterial, AdTask
from app.models.user import User
from app.schemas.ads import (
    AdCampaignDetail,
    AdCampaignSummary,
    AdCommentCreate,
    AdCommentResponse,
    AdFileResponse,
    AdMaterialResponse,
    AdMaterialUpdate,
    AdTaskResponse,
    AdTaskUpdate,
)
from app.services import ads_service
from app.services.ads_service import (
    AUDIO_SUFFIXES,
    MAX_FILE_BYTES,
    TEAM_FILE_ROLES,
    AdFileRejected,
    AdFileTooLarge,
    AdsStorageNotConfigured,
)


router = APIRouter()


async def _get_or_404(db: AsyncSession, model, object_id: UUID, name: str):
    obj = await db.get(model, object_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} not found")
    return obj


@router.get("/ads/campaigns", response_model=list[AdCampaignSummary])
async def list_ad_campaigns(
    db: AsyncSession = Depends(get_db),
    viewer: User = Depends(require_permission("ads.read")),
) -> list[AdCampaignSummary]:
    return [ads_service.campaign_summary(c) for c in await ads_service.list_campaigns(db)]


@router.get("/ads/campaigns/{campaign_id}", response_model=AdCampaignDetail)
async def get_ad_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    viewer: User = Depends(require_permission("ads.read")),
) -> AdCampaignDetail:
    campaign = await ads_service.load_campaign(db, campaign_id=campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return ads_service.campaign_detail(campaign, viewer)


@router.patch("/ads/materials/{material_id}", response_model=AdMaterialResponse)
async def update_ad_material(
    material_id: UUID,
    data: AdMaterialUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ads.manage")),
) -> AdMaterialResponse:
    material = await ads_service.load_material(db, material_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    changes = data.model_dump(exclude_unset=True)
    if "published_url" in changes:
        url = (changes["published_url"] or "").strip()
        if url and not url.startswith("https://"):
            raise HTTPException(status_code=422, detail="Ссылка на пост должна начинаться с https://")
        material.published_url = url or None
    if changes.get("status"):
        material.status = changes["status"]
        if material.status == "published":
            material.published_at = material.published_at or datetime.utcnow()
        else:
            material.published_at = None
    material.updated_at = datetime.utcnow()
    await db.commit()
    return ads_service.material_response(await ads_service.load_material(db, material_id))


@router.post(
    "/ads/materials/{material_id}/files",
    response_model=AdFileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_ad_file(
    material_id: UUID,
    request: Request,
    filename: str = Query(..., min_length=1, max_length=255),
    label: str | None = Query(None, max_length=255),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ads.manage")),
) -> AdFileResponse:
    """Upload one file as the raw request body: a voice recording or any other attachment."""
    length = request.headers.get("content-length", "")
    if length.isdigit() and int(length) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Файл больше 400 МБ")
    material = await ads_service.load_material(db, material_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    role = "voice" if Path(filename).suffix.lower() in AUDIO_SUFFIXES else "other"
    try:
        file, _ = await ads_service.put_file(
            db,
            material,
            key=f"{role}-{uuid.uuid4().hex[:12]}",
            role=role,
            filename=filename,
            label=label,
            chunks=request.stream(),
            uploaded_by=admin,
        )
    except AdsStorageNotConfigured:
        raise HTTPException(status_code=503, detail="Ads storage is not configured") from None
    except AdFileTooLarge:
        raise HTTPException(status_code=413, detail="Файл больше 400 МБ") from None
    except AdFileRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    await ads_service.commit_file_changes(db, added=[file.storage_key], replaced=[])
    material = await ads_service.load_material(db, material_id)
    return ads_service.file_response(next(f for f in material.files if f.id == file.id))


@router.delete("/ads/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ad_file(
    file_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ads.manage")),
) -> None:
    file = await _get_or_404(db, AdFile, file_id, "File")
    # Pipeline files are replaced by the next sync; only the team's own uploads are removable here.
    if file.uploaded_by_id is None or file.role not in TEAM_FILE_ROLES:
        raise HTTPException(status_code=409, detail="Этот файл обновляется автоматически, удалить его нельзя")
    storage_key = file.storage_key
    await db.delete(file)
    await ads_service.commit_file_changes(db, added=[], replaced=[storage_key])


@router.patch("/ads/tasks/{task_id}", response_model=AdTaskResponse)
async def update_ad_task(
    task_id: UUID,
    data: AdTaskUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ads.manage")),
) -> AdTaskResponse:
    task = await _get_or_404(db, AdTask, task_id, "Task")
    if data.done and task.done_at is None:
        task.done_at = datetime.utcnow()
        task.done_by_id = admin.id
    elif not data.done:
        task.done_at = None
        task.done_by_id = None
    await db.commit()
    task = await db.scalar(
        select(AdTask)
        .where(AdTask.id == task_id)
        .options(selectinload(AdTask.done_by))
        .execution_options(populate_existing=True)
    )
    return ads_service.task_response(task)


@router.post(
    "/ads/campaigns/{campaign_id}/comments",
    response_model=AdCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ad_comment(
    campaign_id: UUID,
    data: AdCommentCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ads.manage")),
) -> AdCommentResponse:
    await _get_or_404(db, AdCampaign, campaign_id, "Campaign")
    if data.material_id is not None:
        material = await db.get(AdMaterial, data.material_id)
        if material is None or material.campaign_id != campaign_id:
            raise HTTPException(status_code=404, detail="Material not found")
    comment = AdComment(
        campaign_id=campaign_id,
        material_id=data.material_id,
        author_id=admin.id,
        body=data.body.strip(),
    )
    db.add(comment)
    await db.commit()
    comment = await db.scalar(
        select(AdComment).where(AdComment.id == comment.id).options(selectinload(AdComment.author))
    )
    return ads_service.comment_response(comment, admin)


@router.delete("/ads/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ad_comment(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ads.manage")),
) -> None:
    comment = await _get_or_404(db, AdComment, comment_id, "Comment")
    if comment.author_id != admin.id:
        raise HTTPException(status_code=403, detail="Удалить можно только свой комментарий")
    await db.delete(comment)
    await db.commit()
