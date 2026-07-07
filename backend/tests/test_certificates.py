import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.certificate import Certificate
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.progress import Progress
from app.models.purchase import Purchase
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.certificate_service import CertificateService

_CERT_NUMBER_RE = re.compile(r"^LN-\d{4}-[2-9A-HJ-NP-Z]{6}$")


@pytest.fixture(autouse=True)
def certificate_storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Points upload_dir()/public_upload_url() at a tmp directory for every test."""
    monkeypatch.setattr(settings, "UPLOAD_STORAGE_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def mock_send_certificate(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Captures CertificateService's best-effort congratulations email calls."""
    calls: list[dict] = []

    async def fake_send_certificate(
        email: str,
        student_name: str,
        course_title: str,
        certificate_number: str,
        verify_url: str,
        pdf_bytes: bytes,
    ) -> None:
        calls.append(
            {
                "email": email,
                "student_name": student_name,
                "course_title": course_title,
                "certificate_number": certificate_number,
                "verify_url": verify_url,
                "pdf_bytes": pdf_bytes,
            }
        )

    monkeypatch.setattr(
        "app.services.certificate_service.EmailService.send_certificate", fake_send_certificate
    )
    return calls


async def _create_authenticated_student(
    db: AsyncSession, email: str, password: str = "password123"
) -> tuple[User, dict[str, str]]:
    """Creates a student user directly and mints a real JWT via AuthService.create_tokens
    (the exact same code /api/auth/login calls) rather than going through
    /api/auth/register + /api/auth/login over HTTP.

    Deliberate deviation from the register-then-login idiom used elsewhere in this test
    suite: /api/auth/register is capped at 15/minute (see app/api/auth.py), a shared
    in-memory bucket keyed by client IP that persists across the whole pytest run. This
    file alone needs more distinct users than that budget allows once run alongside the
    rest of the suite (test_auth.py, test_courses.py, test_purchases.py all also call
    register), which was observed to cascade into unrelated failures in those files.
    Bypassing registration/login here avoids the shared rate limiter entirely while
    still exercising the real JWT-validation path (get_current_user) on every request.
    """
    user = User(email=email, password_hash=get_password_hash(password), role="student")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    tokens = AuthService.create_tokens(user.id)
    return user, {"Authorization": f"Bearer {tokens.access_token}"}


async def _setup_course(
    db: AsyncSession, *, lesson_count: int = 2, title: str = "Nail Art Mastery"
) -> tuple[Course, list[Lesson]]:
    """Published course + one published module with `lesson_count` published lessons."""
    course = Course(title=title, price_self=1000, price_support=2000, is_published=True)
    db.add(course)
    await db.flush()
    module = Module(course_id=course.id, title="Module 1", order_index=1, is_published=True)
    db.add(module)
    await db.flush()
    lessons = [
        Lesson(module_id=module.id, title=f"Lesson {i + 1}", duration_seconds=60, order_index=i + 1)
        for i in range(lesson_count)
    ]
    db.add_all(lessons)
    await db.commit()
    await db.refresh(course)
    for lesson in lessons:
        await db.refresh(lesson)
    return course, lessons


async def _add_purchase(
    db: AsyncSession, user_id: uuid.UUID, course_id: uuid.UUID, *, expires_at: datetime | None = None
) -> Purchase:
    purchase = Purchase(
        user_id=user_id,
        course_id=course_id,
        tariff="self",
        amount_kopecks=100000,
        payment_status="success",
        payment_id=f"test-payment-{uuid.uuid4().hex}",
        expires_at=expires_at or (datetime.utcnow() + timedelta(days=30)),
    )
    db.add(purchase)
    await db.commit()
    return purchase


async def _complete_lessons(db: AsyncSession, user_id: uuid.UUID, lessons: list[Lesson]) -> None:
    for lesson in lessons:
        db.add(
            Progress(
                user_id=user_id,
                lesson_id=lesson.id,
                watched_seconds=lesson.duration_seconds,
                is_completed=True,
                completed_at=datetime.utcnow(),
            )
        )
    await db.commit()


# ---------------------------------------------------------------------------
# 1. Claim at <100% -> 409
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_claim_below_full_completion_returns_409(client: AsyncClient, db: AsyncSession):
    course, lessons = await _setup_course(db, lesson_count=2)
    user, headers = await _create_authenticated_student(db, "partial@example.com")
    await _add_purchase(db, user.id, course.id)
    await _complete_lessons(db, user.id, lessons[:1])

    response = await client.post(
        f"/api/courses/{course.id}/certificate",
        json={"full_name": "Anna Ivanova"},
        headers=headers,
    )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# 2. Claim with no purchase at all -> 403
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_claim_without_purchase_returns_403(client: AsyncClient, db: AsyncSession):
    course, _lessons = await _setup_course(db, lesson_count=2)
    _user, headers = await _create_authenticated_student(db, "no-purchase@example.com")

    response = await client.post(
        f"/api/courses/{course.id}/certificate",
        json={"full_name": "Anna Ivanova"},
        headers=headers,
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# 3. Happy path 100% completion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_claim_happy_path_issues_certificate(
    client: AsyncClient, db: AsyncSession, tmp_path: Path, mock_send_certificate: list[dict]
):
    course, lessons = await _setup_course(db, lesson_count=2)
    user, headers = await _create_authenticated_student(db, "graduate@example.com")
    await _add_purchase(db, user.id, course.id)
    await _complete_lessons(db, user.id, lessons)

    response = await client.post(
        f"/api/courses/{course.id}/certificate",
        json={"full_name": "Anna Ivanova"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert _CERT_NUMBER_RE.fullmatch(data["certificate_number"])
    assert data["student_name"] == "Anna Ivanova"
    assert data["course_title"] == course.title
    assert data["png_url"]
    assert data["pdf_url"]

    png_path = tmp_path / "certificates" / Path(data["png_url"]).name
    pdf_path = tmp_path / "certificates" / Path(data["pdf_url"]).name
    assert png_path.is_file()
    assert pdf_path.is_file()
    png_bytes = png_path.read_bytes()
    pdf_bytes = pdf_path.read_bytes()
    assert len(png_bytes) > 0
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b"%PDF"

    await db.refresh(user)
    assert user.full_name == "Anna Ivanova"

    assert len(mock_send_certificate) == 1
    sent = mock_send_certificate[0]
    assert sent["email"] == "graduate@example.com"
    assert sent["student_name"] == "Anna Ivanova"
    assert sent["course_title"] == course.title
    assert sent["certificate_number"] == data["certificate_number"]
    assert sent["pdf_bytes"][:4] == b"%PDF"


# ---------------------------------------------------------------------------
# 4. Idempotency: second claim with a different name doesn't change anything
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_claim_is_idempotent(client: AsyncClient, db: AsyncSession, tmp_path: Path):
    course, lessons = await _setup_course(db, lesson_count=2)
    user, headers = await _create_authenticated_student(db, "repeat@example.com")
    await _add_purchase(db, user.id, course.id)
    await _complete_lessons(db, user.id, lessons)

    first = await client.post(
        f"/api/courses/{course.id}/certificate",
        json={"full_name": "Anna Ivanova"},
        headers=headers,
    )
    assert first.status_code == 200
    first_data = first.json()

    certs_dir = tmp_path / "certificates"
    files_before = sorted(p.name for p in certs_dir.iterdir())

    second = await client.post(
        f"/api/courses/{course.id}/certificate",
        json={"full_name": "Anna Petrovna Sidorova"},
        headers=headers,
    )

    assert second.status_code == 200
    second_data = second.json()
    assert second_data["certificate_number"] == first_data["certificate_number"]
    assert second_data["student_name"] == "Anna Ivanova"

    files_after = sorted(p.name for p in certs_dir.iterdir())
    assert files_after == files_before


# ---------------------------------------------------------------------------
# 5. Expired purchase + 100% progress -> claim still succeeds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_claim_succeeds_with_expired_purchase(client: AsyncClient, db: AsyncSession):
    course, lessons = await _setup_course(db, lesson_count=2)
    user, headers = await _create_authenticated_student(db, "expired@example.com")
    await _add_purchase(db, user.id, course.id, expires_at=datetime.utcnow() - timedelta(days=1))
    await _complete_lessons(db, user.id, lessons)

    response = await client.post(
        f"/api/courses/{course.id}/certificate",
        json={"full_name": "Anna Ivanova"},
        headers=headers,
    )

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# 6. Course with zero published lessons -> 409
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_claim_course_with_zero_lessons_returns_409(client: AsyncClient, db: AsyncSession):
    course, _lessons = await _setup_course(db, lesson_count=0)
    user, headers = await _create_authenticated_student(db, "empty-course@example.com")
    await _add_purchase(db, user.id, course.id)

    response = await client.post(
        f"/api/courses/{course.id}/certificate",
        json={"full_name": "Anna Ivanova"},
        headers=headers,
    )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# 7. GET status tri-state: not_available -> available -> issued
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_certificate_status_transitions(client: AsyncClient, db: AsyncSession):
    course, lessons = await _setup_course(db, lesson_count=2)
    user, headers = await _create_authenticated_student(db, "status@example.com")
    await _add_purchase(db, user.id, course.id)

    not_available = await client.get(f"/api/courses/{course.id}/certificate", headers=headers)
    assert not_available.status_code == 200
    not_available_data = not_available.json()
    assert not_available_data["status"] == "not_available"
    assert not_available_data["progress_percent"] == 0
    assert not_available_data["certificate"] is None

    await _complete_lessons(db, user.id, lessons)

    available = await client.get(f"/api/courses/{course.id}/certificate", headers=headers)
    assert available.status_code == 200
    available_data = available.json()
    assert available_data["status"] == "available"
    assert available_data["progress_percent"] == 100
    assert available_data["certificate"] is None

    claim = await client.post(
        f"/api/courses/{course.id}/certificate",
        json={"full_name": "Anna Ivanova"},
        headers=headers,
    )
    assert claim.status_code == 200

    issued = await client.get(f"/api/courses/{course.id}/certificate", headers=headers)
    assert issued.status_code == 200
    issued_data = issued.json()
    assert issued_data["status"] == "issued"
    assert issued_data["progress_percent"] == 100
    assert issued_data["certificate"] is not None
    assert issued_data["certificate"]["certificate_number"] == claim.json()["certificate_number"]
    assert issued_data["certificate"]["course_title"] == course.title


# ---------------------------------------------------------------------------
# 8. Public verify endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_certificate_public(client: AsyncClient, db: AsyncSession):
    course, lessons = await _setup_course(db, lesson_count=2)
    user, headers = await _create_authenticated_student(db, "verify@example.com")
    await _add_purchase(db, user.id, course.id)
    await _complete_lessons(db, user.id, lessons)

    claim = await client.post(
        f"/api/courses/{course.id}/certificate",
        json={"full_name": "Anna Ivanova"},
        headers=headers,
    )
    number = claim.json()["certificate_number"]

    # Public endpoint: no auth headers at all.
    found = await client.get(f"/api/certificates/verify/{number}")
    assert found.status_code == 200
    data = found.json()
    assert data["student_name"] == "Anna Ivanova"
    assert data["course_title"] == course.title
    assert data["course_id"] == str(course.id)
    assert data["png_url"]
    assert data["pdf_url"]

    missing = await client.get("/api/certificates/verify/LN-2026-ZZZZZZ")
    assert missing.status_code == 404


# ---------------------------------------------------------------------------
# 9. File download endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_download_certificate_file(client: AsyncClient, db: AsyncSession):
    course, lessons = await _setup_course(db, lesson_count=2)
    user, headers = await _create_authenticated_student(db, "download@example.com")
    await _add_purchase(db, user.id, course.id)
    await _complete_lessons(db, user.id, lessons)

    claim = await client.post(
        f"/api/courses/{course.id}/certificate",
        json={"full_name": "Anna Ivanova"},
        headers=headers,
    )
    number = claim.json()["certificate_number"]

    pdf_response = await client.get(f"/api/certificates/{number}/file", params={"format": "pdf"})
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert f"Lucy-Nails-Certificate-{number}.pdf" in pdf_response.headers["content-disposition"]
    assert pdf_response.content[:4] == b"%PDF"

    png_response = await client.get(f"/api/certificates/{number}/file", params={"format": "png"})
    assert png_response.status_code == 200
    assert png_response.headers["content-type"] == "image/png"
    assert f"Lucy-Nails-Certificate-{number}.png" in png_response.headers["content-disposition"]
    assert png_response.content[:8] == b"\x89PNG\r\n\x1a\n"

    bad_format = await client.get(f"/api/certificates/{number}/file", params={"format": "gif"})
    assert bad_format.status_code == 422

    missing = await client.get("/api/certificates/LN-2026-ZZZZZZ/file", params={"format": "pdf"})
    assert missing.status_code == 404


# ---------------------------------------------------------------------------
# 10. Name validation via the API (schema is the contract)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_claim_rejects_script_tag_name(client: AsyncClient, db: AsyncSession):
    course, _lessons = await _setup_course(db, lesson_count=2)
    _user, headers = await _create_authenticated_student(db, "xss@example.com")

    response = await client.post(
        f"/api/courses/{course.id}/certificate",
        json={"full_name": "<script>alert(1)</script>"},
        headers=headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_claim_rejects_emoji_in_name(client: AsyncClient, db: AsyncSession):
    course, _lessons = await _setup_course(db, lesson_count=2)
    _user, headers = await _create_authenticated_student(db, "emoji@example.com")

    response = await client.post(
        f"/api/courses/{course.id}/certificate",
        json={"full_name": "Анна😀"},
        headers=headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_claim_rejects_overly_long_name(client: AsyncClient, db: AsyncSession):
    course, _lessons = await _setup_course(db, lesson_count=2)
    _user, headers = await _create_authenticated_student(db, "longname@example.com")

    response = await client.post(
        f"/api/courses/{course.id}/certificate",
        json={"full_name": "A" * 300},
        headers=headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_claim_rejects_name_that_collapses_below_min_length(client: AsyncClient, db: AsyncSession):
    # "И " is 2 raw chars (passes Field(min_length=2) on the unnormalized string) but
    # collapses to the 1-char "И" once whitespace is stripped/collapsed — the
    # validator must re-check length AFTER normalization, not just before.
    course, _lessons = await _setup_course(db, lesson_count=2)
    _user, headers = await _create_authenticated_student(db, "shortname@example.com")

    response = await client.post(
        f"/api/courses/{course.id}/certificate",
        json={"full_name": "И "},
        headers=headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_claim_accepts_single_word_name(client: AsyncClient, db: AsyncSession):
    # Schema is the contract: a single word passes _FULL_NAME_PATTERN, so the
    # router must not invent a stricter rule.
    course, lessons = await _setup_course(db, lesson_count=2)
    user, headers = await _create_authenticated_student(db, "singleword@example.com")
    await _add_purchase(db, user.id, course.id)
    await _complete_lessons(db, user.id, lessons)

    response = await client.post(
        f"/api/courses/{course.id}/certificate",
        json={"full_name": "Анна"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["student_name"] == "Анна"


# ---------------------------------------------------------------------------
# 11. certificate_number surfaces in GET /purchases/my after claim
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_certificate_number_appears_in_my_purchases(client: AsyncClient, db: AsyncSession):
    course, lessons = await _setup_course(db, lesson_count=2)
    user, headers = await _create_authenticated_student(db, "myprogress@example.com")
    await _add_purchase(db, user.id, course.id)
    await _complete_lessons(db, user.id, lessons)

    claim = await client.post(
        f"/api/courses/{course.id}/certificate",
        json={"full_name": "Anna Ivanova"},
        headers=headers,
    )
    number = claim.json()["certificate_number"]

    my_purchases = await client.get("/api/purchases/my", headers=headers)
    assert my_purchases.status_code == 200
    entries = my_purchases.json()
    matching = [entry for entry in entries if entry["id"] == str(course.id)]
    assert len(matching) == 1
    assert matching[0]["certificate_number"] == number


# ---------------------------------------------------------------------------
# 12. Claim requires auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_claim_requires_authentication(client: AsyncClient, db: AsyncSession):
    course, _lessons = await _setup_course(db, lesson_count=2)

    response = await client.post(
        f"/api/courses/{course.id}/certificate",
        json={"full_name": "Anna Ivanova"},
    )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# 13. Concurrent double-claim race: IntegrityError recovery must not 500
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_claim_survives_commit_race_after_rollback(
    client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """
    Simulates two concurrent claim() calls both passing the "does a certificate
    already exist" pre-check, then racing to commit — the loser hits the
    uq_certificates_user_course IntegrityError and must recover by returning the
    winner's row (200), not blow up with a post-rollback MissingGreenlet (500).
    """
    course, lessons = await _setup_course(db, lesson_count=2)
    user, headers = await _create_authenticated_student(db, "race@example.com")
    await _add_purchase(db, user.id, course.id)
    await _complete_lessons(db, user.id, lessons)

    # Pre-insert the "winner" row directly, as if another concurrent request had
    # already committed it.
    winner_number = CertificateService.generate_certificate_number()
    db.add(
        Certificate(
            user_id=user.id,
            course_id=course.id,
            certificate_number=winner_number,
            student_name="Winner Name",
            png_url="/uploads/certificates/winner.png",
            pdf_url="/uploads/certificates/winner.pdf",
        )
    )
    await db.commit()

    # Make the pre-check miss the just-inserted row exactly once, so claim()
    # proceeds to build and commit a second row for the same (user, course) —
    # colliding with the unique constraint and exercising the real
    # IntegrityError -> rollback -> recovery-select branch.
    real_check = CertificateService._get_existing_with_course
    calls = {"n": 0}

    async def flaky_existing_check(db_arg, user_id, course_id):
        calls["n"] += 1
        if calls["n"] == 1:
            return None
        return await real_check(db_arg, user_id, course_id)

    monkeypatch.setattr(
        CertificateService, "_get_existing_with_course", staticmethod(flaky_existing_check)
    )

    response = await client.post(
        f"/api/courses/{course.id}/certificate",
        json={"full_name": "Someone Else"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["certificate_number"] == winner_number
    assert data["student_name"] == "Winner Name"
