"""
API эндпоинты для загрузки файлов.
"""

import uuid
import tempfile
import warnings
from pathlib import Path
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from pydantic import BaseModel
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from app.core.dependencies import require_permission
from app.core.config import settings
from app.core.uploads import public_upload_url as _public_upload_url
from app.core.uploads import upload_dir as _upload_dir
from app.models.user import User


router = APIRouter()
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
IMAGE_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
    ".gif": "GIF",
}


def _save_image(source, file_path: Path, expected_format: str) -> None:
    partial = file_path.with_suffix(file_path.suffix + ".partial")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            try:
                source.seek(0)
                with Image.open(source) as image:
                    if (
                        image.format != expected_format
                        or image.width * image.height > MAX_IMAGE_PIXELS
                    ):
                        raise ValueError("Invalid image format or dimensions")
                    image.verify()
                source.seek(0)
                with Image.open(source) as image:
                    image.load()
                    cleaned = image.convert(
                        "RGB" if expected_format == "JPEG" else "RGBA"
                    )
            except OSError as exc:
                raise ValueError("Invalid image") from exc
            file_path.parent.mkdir(parents=True, exist_ok=True)
            cleaned.save(partial, format=expected_format)
        partial.replace(file_path)
    finally:
        partial.unlink(missing_ok=True)


def _is_production() -> bool:
    return settings.is_deployed


class UploadResponse(BaseModel):
    """Схема ответа после загрузки файла."""

    url: str
    filename: str


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    admin: User = Depends(require_permission("content.manage")),
):
    """
    Загрузить файл (только для админов).
    Поддерживаемые форматы: jpg, jpeg, png, webp, gif.
    """
    if _is_production() and (
        not settings.UPLOAD_STORAGE_DIR or not settings.UPLOAD_PUBLIC_BASE_URL
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Uploads are disabled in production. Configure persistent storage and public URL first.",
        )

    # Проверка типа файла
    allowed_extensions = set(IMAGE_FORMATS)
    file_ext = Path(file.filename or "").suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}",
        )

    # Генерация уникального имени файла
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"

    # Полный путь к файлу
    file_path = _upload_dir() / unique_filename

    # Сохраняем файл
    try:
        with tempfile.SpooledTemporaryFile(max_size=MAX_UPLOAD_BYTES) as source:
            total = 0
            while chunk := await file.read(64 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413, detail="Image exceeds the 10 MB limit"
                    )
                source.write(chunk)
            await run_in_threadpool(
                _save_image, source, file_path, IMAGE_FORMATS[file_ext]
            )
    except HTTPException:
        raise
    except (
        UnidentifiedImageError,
        ValueError,
        SyntaxError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise HTTPException(status_code=400, detail="Invalid or oversized image")
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save image",
        )
    finally:
        await file.close()

    # Возвращаем URL (относительный путь от public/)
    return UploadResponse(
        url=_public_upload_url(unique_filename), filename=unique_filename
    )
