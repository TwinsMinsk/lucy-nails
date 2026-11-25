"""Token-bearing links leave the outbox payload once a message is finished."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.outbox_service as outbox_service
from app.core.security import get_password_hash
from app.models.outbox import OutboxMessage
from app.models.rbac import Permission, Role, UserRoleAssignment
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.outbox_service import enqueue_outbox_message, process_outbox_batch

RESET_URL = "https://lucy.example/auth/reset-password?token=secret.reset.token"
LOGIN_URL = "https://lucy.example/auth/activate?token=secret.login.token"
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "redact_outbox_links.py"


def _reset_message(db: AsyncSession, key: str, **fields) -> OutboxMessage:
    message = enqueue_outbox_message(
        db,
        kind="password_reset",
        recipient="student@example.com",
        payload={"reset_url": RESET_URL},
        dedupe_key=key,
    )
    for name, value in fields.items():
        setattr(message, name, value)
    return message


@pytest.mark.asyncio
async def test_sent_message_keeps_no_usable_link(db: AsyncSession):
    message = enqueue_outbox_message(
        db,
        kind="account_activation",
        recipient="buyer@example.com",
        payload={"activation_url": LOGIN_URL, "course_title": "Course", "expires_at": None},
        dedupe_key="test:redact:sent",
    )
    await db.commit()
    delivered: list[str] = []

    async def deliver(current: OutboxMessage) -> None:
        delivered.append(current.payload["activation_url"])

    await process_outbox_batch(db, deliver=deliver)
    await db.refresh(message)

    assert delivered == [LOGIN_URL]
    assert message.status == "sent"
    assert message.payload == {
        "activation_url": "[REDACTED]",
        "course_title": "Course",
        "expires_at": None,
    }


@pytest.mark.asyncio
async def test_retry_keeps_the_link_until_delivery(db: AsyncSession):
    message = _reset_message(db, "test:redact:retry")
    await db.commit()

    async def fail(_current: OutboxMessage) -> None:
        raise RuntimeError("email provider unavailable")

    await process_outbox_batch(db, deliver=fail)
    await db.refresh(message)
    assert message.status == "retry"
    assert message.payload == {"reset_url": RESET_URL}

    message.next_attempt_at = message.created_at
    await db.commit()
    delivered: list[str] = []

    async def deliver(current: OutboxMessage) -> None:
        delivered.append(current.payload["reset_url"])

    await process_outbox_batch(db, deliver=deliver)
    await db.refresh(message)
    assert delivered == [RESET_URL]
    assert message.payload == {"reset_url": "[REDACTED]"}


@pytest.mark.asyncio
async def test_dead_letter_keeps_no_usable_link(db: AsyncSession):
    message = _reset_message(db, "test:redact:dead", max_attempts=1)
    await db.commit()

    async def fail(_current: OutboxMessage) -> None:
        raise RuntimeError("mailbox rejected")

    await process_outbox_batch(db, deliver=fail)
    await db.refresh(message)
    assert message.status == "dead_letter"
    assert message.payload == {"reset_url": "[REDACTED]"}


@pytest.mark.asyncio
async def test_links_without_a_token_and_telegram_text_are_handled(db: AsyncSession):
    certificate = enqueue_outbox_message(
        db,
        kind="certificate_issued",
        recipient="student@example.com",
        payload={
            "student_name": "Student",
            "course_title": "Course",
            "certificate_number": "LS-1",
            "verify_url": "https://lucy.example/certificate/LS-1",
        },
        dedupe_key="test:redact:certificate",
    )
    telegram = enqueue_outbox_message(
        db,
        kind="owner_alert",
        channel="telegram",
        recipient="42",
        payload={"text": f"Ссылка: {LOGIN_URL} — отправлена"},
        dedupe_key="test:redact:telegram",
    )
    await db.commit()

    async def deliver(_current: OutboxMessage) -> None:
        return None

    await process_outbox_batch(db, deliver=deliver)
    await db.refresh(certificate)
    await db.refresh(telegram)
    assert certificate.payload["verify_url"] == "https://lucy.example/certificate/LS-1"
    assert telegram.payload == {"text": "Ссылка: [REDACTED] — отправлена"}


@pytest.mark.asyncio
async def test_redacted_link_is_never_sent(monkeypatch):
    sent: list[str] = []

    async def send_password_reset(recipient: str, url: str) -> None:
        sent.append(url)

    monkeypatch.setattr(outbox_service.EmailService, "send_password_reset", send_password_reset)
    message = OutboxMessage(
        kind="password_reset",
        channel="email",
        recipient="student@example.com",
        payload={"reset_url": "[REDACTED]"},
        dedupe_key="test:redact:manual-retry",
    )

    with pytest.raises(ValueError, match="send a new one"):
        await outbox_service.deliver_outbox_message(message)
    assert sent == []


@pytest.mark.asyncio
async def test_notifications_list_still_works_after_redaction(
    client: AsyncClient, db: AsyncSession
):
    staff = User(email="curator@example.com", password_hash=get_password_hash("x" * 12), role="student")
    role = Role(name="curator", description="curator", is_system=True)
    role.permissions = [Permission(name="notifications.manage", description="n")]
    db.add_all([staff, role])
    await db.flush()
    db.add(UserRoleAssignment(user_id=staff.id, role_id=role.id))
    _reset_message(db, "test:redact:list")
    await db.commit()

    async def deliver(_current: OutboxMessage) -> None:
        return None

    await process_outbox_batch(db, deliver=deliver)
    token = AuthService.create_tokens(staff.id, staff.token_version).access_token
    response = await client.get(
        "/api/admin/notifications", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["status"] == "sent"
    assert "secret" not in response.text


def _run_script(dsn: str, *args: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env={**os.environ, "DATABASE_URL": dsn},
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "secret." not in result.stdout + result.stderr
    return json.loads(result.stdout)


@pytest.mark.asyncio
async def test_cleanup_script_redacts_only_finished_rows_and_only_with_apply(
    db: AsyncSession,
):
    sent = _reset_message(db, "test:script:sent", status="sent")
    dead = _reset_message(db, "test:script:dead", status="dead_letter")
    pending = _reset_message(db, "test:script:pending")
    retry = _reset_message(db, "test:script:retry", status="retry")
    certificate = enqueue_outbox_message(
        db,
        kind="certificate_issued",
        recipient="student@example.com",
        payload={"verify_url": "https://lucy.example/certificate/LS-1"},
        dedupe_key="test:script:certificate",
    )
    certificate.status = "sent"
    await db.commit()
    dsn = db.bind.url.render_as_string(hide_password=False)

    assert _run_script(dsn) == {"applied": False, "rows": {"outbox_messages.payload": 2}}
    await db.refresh(sent)
    assert sent.payload == {"reset_url": RESET_URL}

    assert _run_script(dsn, "--apply") == {"applied": True, "rows": {"outbox_messages.payload": 2}}
    for row in (sent, dead, pending, retry, certificate):
        await db.refresh(row)
    assert sent.payload == {"reset_url": "[REDACTED]"}
    assert dead.payload == {"reset_url": "[REDACTED]"}
    assert pending.payload == {"reset_url": RESET_URL}
    assert retry.payload == {"reset_url": RESET_URL}
    assert certificate.payload == {"verify_url": "https://lucy.example/certificate/LS-1"}

    assert _run_script(dsn, "--apply")["rows"] == {"outbox_messages.payload": 0}
