"""
Общие хелперы для работы с путями загруженных файлов (uploads, certificates, ...).
"""

from pathlib import Path

from app.core.config import settings


def upload_dir() -> Path:
    if settings.UPLOAD_STORAGE_DIR:
        return Path(settings.UPLOAD_STORAGE_DIR)
    return Path(__file__).parent.parent.parent.parent / "frontend" / "public" / "uploads"


def public_upload_url(relative_path: str) -> str:
    # Normalize to forward slashes so URLs stay correct on Windows too.
    relative_path = relative_path.replace("\\", "/")
    if settings.UPLOAD_PUBLIC_BASE_URL:
        return f"{settings.UPLOAD_PUBLIC_BASE_URL.rstrip('/')}/{relative_path}"
    return f"/uploads/{relative_path}"
