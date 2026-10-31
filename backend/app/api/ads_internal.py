"""Sync from the local ads pipeline (`ads/campaign/publish.py`) into the admin "Реклама" section.

Authenticated by the `X-Ads-Token` header against ADS_SYNC_TOKEN: the pipeline runs on a
workstation, without a browser session or MFA.
"""

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.ad import AdMaterial
from app.schemas.ads import KEY_PATTERN, AdCampaignDetail, AdCampaignSync, AdFileResponse, FileRole
from app.services import ads_service
from app.services.ads_service import (
    MAX_FILE_BYTES,
    AdFileRejected,
    AdFileTooLarge,
    AdsStorageNotConfigured,
)

router = APIRouter()


def require_sync_token(x_ads_token: str = Header(default="")) -> None:
    if len(settings.ADS_SYNC_TOKEN) < 32:
        raise HTTPException(status_code=503, detail="Ads sync is not configured")
    if not secrets.compare_digest(x_ads_token.encode(), settings.ADS_SYNC_TOKEN.encode()):
        raise HTTPException(status_code=401, detail="Invalid ads token")


SlugPath = Path(..., pattern=KEY_PATTERN, max_length=100)
CodePath = Path(..., pattern=KEY_PATTERN, max_length=32)
KeyPath = Path(..., pattern=KEY_PATTERN)


async def _campaign_or_404(db: AsyncSession, slug: str):
    campaign = await ads_service.load_campaign(db, slug=slug)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


def _material_or_404(campaign, code: str) -> AdMaterial:
    material = next((m for m in campaign.materials if m.code == code), None)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")
    return material


@router.get("/ads/campaigns/{slug}", response_model=AdCampaignDetail, include_in_schema=False)
async def get_synced_campaign(
    slug: str = SlugPath,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_sync_token),
) -> AdCampaignDetail:
    return ads_service.campaign_detail(await _campaign_or_404(db, slug))


@router.put("/ads/campaigns/{slug}", response_model=AdCampaignDetail, include_in_schema=False)
@limiter.limit("30/minute")
async def sync_campaign(
    request: Request,
    data: AdCampaignSync,
    slug: str = SlugPath,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_sync_token),
) -> AdCampaignDetail:
    campaign, dropped = await ads_service.sync_campaign(db, slug, data)
    await ads_service.commit_file_changes(db, added=[], replaced=dropped)
    return ads_service.campaign_detail(await ads_service.load_campaign(db, slug=slug))


@router.put(
    "/ads/campaigns/{slug}/materials/{code}/files/{key}",
    response_model=AdFileResponse,
    include_in_schema=False,
)
@limiter.limit("120/minute")
async def put_synced_file(
    request: Request,
    slug: str = SlugPath,
    code: str = CodePath,
    key: str = KeyPath,
    role: FileRole = Query(...),
    filename: str = Query(..., min_length=1, max_length=255),
    variant: str | None = Query(None, pattern=KEY_PATTERN, max_length=16),
    label: str | None = Query(None, max_length=255),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_sync_token),
) -> AdFileResponse:
    length = request.headers.get("content-length", "")
    if length.isdigit() and int(length) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File is too large")
    material = _material_or_404(await _campaign_or_404(db, slug), code)
    try:
        file, replaced = await ads_service.put_file(
            db,
            material,
            key=key,
            role=role,
            variant=variant,
            label=label,
            filename=filename,
            chunks=request.stream(),
        )
    except AdsStorageNotConfigured:
        raise HTTPException(status_code=503, detail="Ads storage is not configured") from None
    except AdFileTooLarge:
        raise HTTPException(status_code=413, detail="File is too large") from None
    except AdFileRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    await ads_service.commit_file_changes(
        db, added=[file.storage_key], replaced=[replaced] if replaced else []
    )
    material = await ads_service.load_material(db, material.id)
    return ads_service.file_response(next(f for f in material.files if f.key == key))


@router.delete(
    "/ads/campaigns/{slug}/materials/{code}/files/{key}",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
async def delete_synced_file(
    slug: str = SlugPath,
    code: str = CodePath,
    key: str = KeyPath,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_sync_token),
) -> None:
    material = _material_or_404(await _campaign_or_404(db, slug), code)
    file = next((f for f in material.files if f.key == key), None)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found")
    storage_key = file.storage_key
    material.files.remove(file)
    await ads_service.commit_file_changes(db, added=[], replaced=[storage_key])
