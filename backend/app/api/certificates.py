"""
API эндпоинты для сертификатов о прохождении курса.
"""

from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.core.uploads import upload_dir
from app.models.user import User
from app.schemas.certificate import (
    CertificateClaimRequest,
    CertificateResponse,
    CertificateStatusResponse,
    CertificateVerifyResponse,
)
from app.services.certificate_service import (
    CertificateService,
    CertificateStorageNotConfiguredError,
    CourseNotCompletedError,
    CourseNotFoundError,
    NoCourseAccessError,
)

router = APIRouter()

# format -> (media type, stored-file extension)
_FILE_FORMATS: dict[str, str] = {"pdf": "application/pdf", "png": "image/png"}


@router.post("/courses/{course_id}/certificate", response_model=CertificateResponse)
@limiter.limit("10/minute")
async def claim_certificate(
    request: Request,
    course_id: UUID,
    data: CertificateClaimRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Выдаёт сертификат о прохождении курса текущему пользователю, либо возвращает
    уже выданный ранее (идемпотентный повторный запрос).
    """
    try:
        certificate, _newly_issued = await CertificateService.claim(
            db, current_user, course_id, data.full_name
        )
    except CourseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    except NoCourseAccessError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course access required")
    except CourseNotCompletedError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Course is not fully completed yet")
    except CertificateStorageNotConfiguredError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Certificate storage is not configured",
        )

    return CertificateResponse.from_certificate(certificate, certificate.course.title)


@router.get("/courses/{course_id}/certificate", response_model=CertificateStatusResponse)
async def get_certificate_status(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Возвращает статус доступности сертификата для текущего пользователя/курса."""
    cert_status, progress_percent, certificate = await CertificateService.get_status(
        db, current_user, course_id
    )

    certificate_response = None
    if certificate is not None:
        certificate_response = CertificateResponse.from_certificate(certificate, certificate.course.title)

    return CertificateStatusResponse(
        status=cert_status,
        progress_percent=progress_percent,
        certificate=certificate_response,
    )


@router.get("/certificates/verify/{certificate_number}", response_model=CertificateVerifyResponse)
@limiter.limit("30/minute")
async def verify_certificate(
    request: Request,
    certificate_number: str,
    db: AsyncSession = Depends(get_db),
):
    """Публичная проверка сертификата по номеру (без авторизации)."""
    certificate = await CertificateService.get_by_number(db, certificate_number)
    if certificate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    return CertificateVerifyResponse(
        certificate_number=certificate.certificate_number,
        student_name=certificate.student_name,
        course_id=certificate.course_id,
        course_title=certificate.course.title,
        issued_at=certificate.issued_at,
        png_url=certificate.png_url,
        pdf_url=certificate.pdf_url,
    )


@router.get("/certificates/{certificate_number}/file")
@limiter.limit("30/minute")
async def download_certificate_file(
    request: Request,
    certificate_number: str,
    format: Literal["pdf", "png"],
    db: AsyncSession = Depends(get_db),
):
    """Публичная выгрузка PNG/PDF-файла сертификата (без авторизации)."""
    certificate = await CertificateService.get_by_number(db, certificate_number)
    if certificate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    stored_url = certificate.pdf_url if format == "pdf" else certificate.png_url
    if not stored_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    # The stored URL is OUR db row, not user input — but we still only trust the
    # filename component of it, re-joined under upload_dir() below, rather than
    # trusting any path-like structure in the stored string directly.
    filename = Path(stored_url).name
    file_path = upload_dir() / "certificates" / filename
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    return FileResponse(
        file_path,
        media_type=_FILE_FORMATS[format],
        filename=f"Lucy-Nails-Certificate-{certificate_number}.{format}",
    )
