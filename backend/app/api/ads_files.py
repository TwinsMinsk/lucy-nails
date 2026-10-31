"""Ad files by signed link: the admin page plays and downloads reels without cookies on the API host."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.ad import AdFile
from app.services import ads_service

router = APIRouter()


# Exempt from the global limit: a video player sends many range requests while seeking.
@router.api_route("/files/{file_id}", methods=["GET", "HEAD"], include_in_schema=False)
@limiter.exempt
async def get_ad_file(
    file_id: UUID,
    exp: int = Query(...),
    sig: str = Query(..., max_length=64),
    download: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    if not ads_service.verify_link(file_id, exp, sig):
        raise HTTPException(status_code=403, detail="Link expired or invalid")
    file = await db.get(AdFile, file_id)
    path = ads_service.stored_path(file.storage_key) if file else None
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path,
        media_type=file.content_type,
        filename=file.filename,
        content_disposition_type="attachment" if download else "inline",
        headers={"Cache-Control": "private, max-age=3600"},
    )
