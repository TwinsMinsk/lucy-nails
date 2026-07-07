"""
Pydantic schemas for course completion certificates.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# First character must be a letter (Latin or Cyrillic); the rest may also
# contain apostrophes, spaces, dots and hyphens (double-barrelled names,
# initials). Blocks emoji/HTML/control chars from reaching the diploma render
# and the email HTML.
_FULL_NAME_PATTERN = re.compile(r"^[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё'’ .\-]*$")


class CertificateClaimRequest(BaseModel):
    """Request body for claiming a certificate — the student's full name for the diploma."""

    full_name: str = Field(..., min_length=2, max_length=120, description="Full name for the certificate")

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        # Strip and collapse internal whitespace runs to a single space.
        normalized = " ".join(value.split())
        if not _FULL_NAME_PATTERN.fullmatch(normalized):
            raise ValueError("Full name contains unsupported characters")
        return normalized


class CertificateResponse(BaseModel):
    """Schema for an issued certificate."""

    id: UUID
    certificate_number: str
    course_id: UUID
    course_title: str  # not a Certificate column — supplied separately (loaded course)
    student_name: str
    png_url: str | None
    pdf_url: str | None
    issued_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_certificate(cls, certificate: Any, course_title: str) -> CertificateResponse:
        """Builds the response from a Certificate ORM row plus its course title."""
        from app.models.certificate import Certificate as CertificateModel

        if not isinstance(certificate, CertificateModel):
            raise TypeError("Expected Certificate ORM instance")
        return cls(
            id=certificate.id,
            certificate_number=certificate.certificate_number,
            course_id=certificate.course_id,
            course_title=course_title,
            student_name=certificate.student_name,
            png_url=certificate.png_url,
            pdf_url=certificate.pdf_url,
            issued_at=certificate.issued_at,
        )


class CertificateStatusResponse(BaseModel):
    """Schema for GET certificate status (not_available / available / issued)."""

    status: Literal["not_available", "available", "issued"]
    progress_percent: int
    certificate: CertificateResponse | None = None


class CertificateVerifyResponse(BaseModel):
    """Public schema for verifying a certificate by its number."""

    certificate_number: str
    student_name: str
    course_id: UUID
    course_title: str
    issued_at: datetime
    png_url: str | None
    pdf_url: str | None
