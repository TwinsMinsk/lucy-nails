"""
API эндпоинты для загрузки файлов.
"""

import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from pydantic import BaseModel

from app.api.admin import require_admin
from app.core.config import settings
from app.models.user import User


router = APIRouter()


def _is_production() -> bool:
    return settings.ENVIRONMENT.lower() == "production"


def _upload_dir() -> Path:
    if settings.UPLOAD_STORAGE_DIR:
        return Path(settings.UPLOAD_STORAGE_DIR)
    return Path(__file__).parent.parent.parent.parent / "frontend" / "public" / "uploads"


def _public_upload_url(filename: str) -> str:
    if settings.UPLOAD_PUBLIC_BASE_URL:
        return f"{settings.UPLOAD_PUBLIC_BASE_URL.rstrip('/')}/{filename}"
    return f"/uploads/{filename}"


class UploadResponse(BaseModel):
    """Схема ответа после загрузки файла."""
    url: str
    filename: str


def ensure_upload_dir():
    """Создать директорию для загрузок, если не существует."""
    os.makedirs(_upload_dir(), exist_ok=True)


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin)
):
    """
    Загрузить файл (только для админов).
    Поддерживаемые форматы: jpg, jpeg, png, webp, gif.
    """
    if _is_production() and (not settings.UPLOAD_STORAGE_DIR or not settings.UPLOAD_PUBLIC_BASE_URL):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Uploads are disabled in production. Configure persistent storage and public URL first.",
        )

    # Проверка типа файла
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Генерация уникального имени файла
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    
    # Создаем директорию если не существует
    ensure_upload_dir()
    
    # Полный путь к файлу
    file_path = _upload_dir() / unique_filename
    
    # Сохраняем файл
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Возвращаем URL (относительный путь от public/)
    return UploadResponse(
        url=_public_upload_url(unique_filename),
        filename=unique_filename
    )
