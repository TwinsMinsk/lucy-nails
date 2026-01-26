"""
API эндпоинты для загрузки файлов.
"""

import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from pydantic import BaseModel

from app.api.admin import require_admin
from app.models.user import User


router = APIRouter()


# Директория для сохранения файлов
# Абсолютный путь от backend к frontend/public/uploads
UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "frontend" / "public" / "uploads"


class UploadResponse(BaseModel):
    """Схема ответа после загрузки файла."""
    url: str
    filename: str


def ensure_upload_dir():
    """Создать директорию для загрузок, если не существует."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin)
):
    """
    Загрузить файл (только для админов).
    Поддерживаемые форматы: jpg, jpeg, png, webp, gif.
    """
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
    file_path = UPLOAD_DIR / unique_filename
    
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
        url=f"/uploads/{unique_filename}",
        filename=unique_filename
    )
