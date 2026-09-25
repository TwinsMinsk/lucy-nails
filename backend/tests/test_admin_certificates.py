from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.certificate import Certificate
from app.models.course import Course
from app.models.outbox import OutboxMessage
from app.models.user import User


@pytest.mark.asyncio
async def test_admin_certificate_registry_revoke_and_reissue(
    client: AsyncClient, db: AsyncSession
):
    admin = User(
        email="cert-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    student = User(
        email="graduate-admin@example.com",
        password_hash=get_password_hash("studentpass1"),
        role="student",
    )
    course = Course(title="Certificate Admin Course", price_self=1000, price_support=2000)
    db.add_all([admin, student, course])
    await db.flush()
    certificate = Certificate(
        user_id=student.id,
        course_id=course.id,
        certificate_number="LN-2026-ADMIN2",
        student_name="Anna Graduate",
        pdf_url="/uploads/certificates/admin.pdf",
        png_url="/uploads/certificates/admin.png",
        issued_at=datetime.utcnow(),
    )
    db.add(certificate)
    await db.commit()
    login = await client.post(
        "/api/auth/login",
        json={"email": admin.email, "password": "adminpass1"},
    )
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    registry = await client.get("/api/admin/certificates", headers=headers)
    assert registry.status_code == 200, registry.text
    assert registry.json()["items"][0]["student_email"] == student.email

    reissued = await client.post(
        f"/api/admin/certificates/{certificate.id}/reissue",
        json={"reason": "Student requested a replacement email"},
        headers=headers,
    )
    assert reissued.status_code == 200, reissued.text
    queued = await db.scalar(
        select(OutboxMessage).where(OutboxMessage.kind == "certificate_reissue")
    )
    assert queued is not None

    revoked = await client.post(
        f"/api/admin/certificates/{certificate.id}/revoke",
        json={"reason": "Certificate issued with incorrect legal name"},
        headers=headers,
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["status"] == "revoked"

    public = await client.get(f"/api/certificates/verify/{certificate.certificate_number}")
    assert public.status_code == 410
