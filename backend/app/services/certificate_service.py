"""
Certificate claim flow: validates course completion and access, generates a
unique certificate number, renders the PNG/PDF diploma, stores the files on
disk, persists the Certificate row and sends a best-effort congratulations
email. No HTTPException here — the router (app/api) translates the domain
exceptions below into HTTP responses.
"""

import logging
import os
import secrets
from datetime import datetime
from typing import Awaitable, Callable
from uuid import UUID, uuid4

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.uploads import public_upload_url, upload_dir
from app.models.certificate import Certificate
from app.models.course import Course
from app.models.user import User
from app.services.certificate_renderer import png_to_pdf, render_certificate_png
from app.services.email_service import EmailService
from app.services.progress_service import ProgressService
from app.services.purchase_service import PurchaseService

logger = logging.getLogger(__name__)

# 31 unambiguous characters (no 0/O, 1/I/L confusion) for the human-typed
# verification code printed on the diploma and QR-encoded in verify_url.
_CERTIFICATE_NUMBER_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
_CERTIFICATE_NUMBER_SUFFIX_LENGTH = 6
_CERTIFICATE_NUMBER_MAX_ATTEMPTS = 5


class CertificateError(Exception):
    """Base error for the certificate claim flow."""


class NoCourseAccessError(CertificateError):
    """User has no successful purchase (and is not an admin) for this course."""


class CourseNotCompletedError(CertificateError):
    """User has not completed all published lessons of the course yet."""


class CourseNotFoundError(CertificateError):
    """The course does not exist."""


class CertificateStorageNotConfiguredError(CertificateError):
    """Upload storage is not configured (required in production)."""


class CertificateService:
    @staticmethod
    def generate_certificate_number() -> str:
        """Generates a certificate number like 'LN-2026-A7K3MX'."""
        year = datetime.utcnow().year
        suffix = "".join(
            secrets.choice(_CERTIFICATE_NUMBER_ALPHABET) for _ in range(_CERTIFICATE_NUMBER_SUFFIX_LENGTH)
        )
        return f"LN-{year}-{suffix}"

    @staticmethod
    async def _generate_unique_certificate_number(
        is_taken: Callable[[str], Awaitable[bool]],
        max_attempts: int = _CERTIFICATE_NUMBER_MAX_ATTEMPTS,
    ) -> str | None:
        """
        Generates a certificate number, retrying on collision up to max_attempts.
        `is_taken` is injectable so this retry loop is unit-testable without a DB.
        """
        for _ in range(max_attempts):
            candidate = CertificateService.generate_certificate_number()
            if not await is_taken(candidate):
                return candidate
        return None

    @staticmethod
    async def get_for_user_course(db: AsyncSession, user_id: UUID, course_id: UUID) -> Certificate | None:
        result = await db.execute(
            select(Certificate).where(
                and_(Certificate.user_id == user_id, Certificate.course_id == course_id)
            )
        )
        return result.scalars().first()

    @staticmethod
    async def _get_existing_with_course(db: AsyncSession, user_id: UUID, course_id: UUID) -> Certificate | None:
        """Same lookup as get_for_user_course, but with the course eager-loaded (course_title needed by callers)."""
        result = await db.execute(
            select(Certificate)
            .options(selectinload(Certificate.course))
            .where(and_(Certificate.user_id == user_id, Certificate.course_id == course_id))
        )
        return result.scalars().first()

    @staticmethod
    async def get_by_number(db: AsyncSession, certificate_number: str) -> Certificate | None:
        result = await db.execute(
            select(Certificate)
            .options(selectinload(Certificate.course))
            .where(Certificate.certificate_number == certificate_number)
        )
        return result.scalars().first()

    @staticmethod
    async def _has_course_access(db: AsyncSession, user: User, course_id: UUID) -> bool:
        """Access = admin, or any successful purchase ever (expiry ignored — completion
        could only have been earned while access was live)."""
        if user.role == "admin":
            return True
        purchase = await PurchaseService.get_any_successful_purchase(db, user.id, course_id)
        return purchase is not None

    @staticmethod
    async def get_status(
        db: AsyncSession,
        user: User,
        course_id: UUID,
    ) -> tuple[str, int, Certificate | None]:
        """Returns (status, progress_percent, certificate) for the claim-status check."""
        completion = await ProgressService.get_course_completion(db, user.id, course_id)

        # Course-eager-loaded lookup (not the bare get_for_user_course): callers
        # (the router) need certificate.course.title without triggering a lazy
        # load on the async session.
        existing = await CertificateService._get_existing_with_course(db, user.id, course_id)
        if existing:
            return "issued", completion.percent, existing

        has_access = await CertificateService._has_course_access(db, user, course_id)
        if completion.is_complete and has_access:
            return "available", completion.percent, None
        return "not_available", completion.percent, None

    @staticmethod
    async def claim(
        db: AsyncSession,
        user: User,
        course_id: UUID,
        full_name: str,
    ) -> tuple[Certificate, bool]:
        """
        Claims (issues) the certificate for the given user/course, or returns the
        already-issued one unchanged (diploma is frozen once issued).

        Returns (certificate, newly_issued).
        """
        # Captured up front: a rollback later in this function (concurrent-claim
        # race) expires every attribute on `user`, and accessing user.id after
        # that would trigger a synchronous lazy-refresh outside greenlet context
        # (MissingGreenlet). Use this local for the rest of the function instead.
        user_id = user.id

        existing = await CertificateService._get_existing_with_course(db, user_id, course_id)
        if existing:
            return existing, False

        course_result = await db.execute(select(Course).where(Course.id == course_id))
        course = course_result.scalars().first()
        if not course:
            raise CourseNotFoundError(f"Course {course_id} not found")

        if not await CertificateService._has_course_access(db, user, course_id):
            raise NoCourseAccessError("User has no access to this course")

        completion = await ProgressService.get_course_completion(db, user_id, course_id)
        if not completion.is_complete:
            raise CourseNotCompletedError("Course is not fully completed yet")

        # Mirror app/api/upload.py's production storage guard.
        if settings.ENVIRONMENT.lower() == "production" and (
            not settings.UPLOAD_STORAGE_DIR or not settings.UPLOAD_PUBLIC_BASE_URL
        ):
            raise CertificateStorageNotConfiguredError(
                "Certificate storage is not configured in production"
            )

        async def _number_is_taken(candidate: str) -> bool:
            result = await db.execute(
                select(Certificate.id).where(Certificate.certificate_number == candidate)
            )
            return result.scalars().first() is not None

        certificate_number = await CertificateService._generate_unique_certificate_number(_number_is_taken)
        if certificate_number is None:
            raise CertificateError("Could not generate a unique certificate number")

        verify_url = f"{settings.FRONTEND_URL.rstrip('/')}/certificate/{certificate_number}"
        issued_date = datetime.utcnow().date()

        png_bytes = await run_in_threadpool(
            render_certificate_png,
            student_name=full_name,
            course_title=course.title,
            certificate_number=certificate_number,
            issued_date=issued_date,
            verify_url=verify_url,
        )
        pdf_bytes = await run_in_threadpool(png_to_pdf, png_bytes)

        certs_dir = upload_dir() / "certificates"
        await run_in_threadpool(os.makedirs, certs_dir, exist_ok=True)

        file_stem = uuid4().hex
        png_path = certs_dir / f"{file_stem}.png"
        pdf_path = certs_dir / f"{file_stem}.pdf"
        await run_in_threadpool(png_path.write_bytes, png_bytes)
        await run_in_threadpool(pdf_path.write_bytes, pdf_bytes)

        certificate = Certificate(
            user_id=user_id,
            course_id=course_id,
            certificate_number=certificate_number,
            student_name=full_name,
            png_url=public_upload_url(f"certificates/{png_path.name}"),
            pdf_url=public_upload_url(f"certificates/{pdf_path.name}"),
        )
        user.full_name = full_name
        db.add(certificate)

        try:
            await db.commit()
        except IntegrityError:
            # Concurrent double-claim raced past the existence check above and both
            # hit the uq_certificates_user_course constraint; the loser's rendered
            # files are an accepted negligible leak (not cleaned up).
            await db.rollback()
            logger.warning(
                "Certificate claim race for user=%s course=%s: returning existing row",
                user_id,
                course_id,
            )
            existing = await CertificateService._get_existing_with_course(db, user_id, course_id)
            if existing is None:
                raise CertificateError("Certificate commit conflicted but no existing row found") from None
            return existing, False

        await db.refresh(certificate)
        # Populate the relationship from the already-loaded `course` in-memory —
        # expire_on_commit=False means this stays put and callers can safely read
        # certificate.course.title without an extra query or a lazy-load attempt
        # on the async session (which would raise MissingGreenlet).
        certificate.course = course

        try:
            await EmailService.send_certificate(
                user.email, full_name, course.title, certificate_number, verify_url, pdf_bytes
            )
        except Exception:
            logger.exception("Failed to send certificate email to %s", user.email)

        return certificate, True
