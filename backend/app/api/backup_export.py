"""Uploads export for the backup job: the volume is mounted only on this service."""

import logging
import secrets
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.core.config import settings
from app.services.uploads_archive_service import build_uploads_archive

logger = logging.getLogger(__name__)
router = APIRouter()


# A sync route on purpose: FastAPI runs it in a thread, so archiving does not block the loop.
@router.get("/backup/uploads.tar", include_in_schema=False)
def export_uploads(x_backup_token: str = Header(default="")) -> FileResponse:
    if len(settings.BACKUP_EXPORT_TOKEN) < 32:
        raise HTTPException(status_code=503, detail="Backup export is not configured")
    if not secrets.compare_digest(x_backup_token.encode(), settings.BACKUP_EXPORT_TOKEN.encode()):
        raise HTTPException(status_code=401, detail="Invalid backup token")
    if not settings.UPLOAD_STORAGE_DIR:
        raise HTTPException(status_code=503, detail="Upload storage is not configured")
    try:
        archive = build_uploads_archive(Path(settings.UPLOAD_STORAGE_DIR))
    except (OSError, RuntimeError):
        logger.exception("Uploads export failed")
        raise HTTPException(status_code=500, detail="Uploads export failed") from None
    return FileResponse(
        archive,
        media_type="application/x-tar",
        background=BackgroundTask(archive.unlink, missing_ok=True),
    )
