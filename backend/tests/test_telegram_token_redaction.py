"""The Telegram bot token must not surface in errors, stored rows or logs."""

import json
import logging
import os
import subprocess
import sys
import traceback
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.outbox_service as outbox_service
import app.workers.outbox as outbox_worker
from app.core.config import settings
from app.models.outbox import DeliveryAttempt, OutboxMessage
from app.services.outbox_service import enqueue_outbox_message

TOKEN_FRAGMENT = "FAKEFAKE"
FAKE_TOKEN = f"123456789:{TOKEN_FRAGMENT * 4}FAKE"
BACKEND_DIR = Path(__file__).resolve().parents[1]
CLEANUP_SCRIPT = BACKEND_DIR.parent / "scripts" / "ops" / "redact_telegram_tokens.py"
LEAKED_HTTPX_ERROR = (
    f"Client error '403 Forbidden' for url 'https://api.telegram.org/bot{FAKE_TOKEN}/sendMessage'\n"
    "For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/403"
)

BOT_WITH_REJECTED_TOKEN = """
import httpx

real_client = httpx.AsyncClient


def rejected(_request):
    return httpx.Response(
        401, json={"ok": False, "error_code": 401, "description": "Unauthorized"}
    )


httpx.AsyncClient = lambda **kwargs: real_client(
    **{**kwargs, "transport": httpx.MockTransport(rejected)}
)

from app.bot.main import main

main()
"""


@pytest.fixture
def telegram_api(monkeypatch: pytest.MonkeyPatch):
    """Answer outbox_service's Telegram calls with a handler instead of the network."""
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", FAKE_TOKEN)
    real_client = httpx.AsyncClient

    def install(handler) -> None:
        monkeypatch.setattr(
            outbox_service.httpx,
            "AsyncClient",
            lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
        )

    return install


@pytest.fixture
def default_httpx_log_level():
    """Undo configure_logging's process-wide change so tests stay independent."""
    httpx_logger = logging.getLogger("httpx")
    previous = httpx_logger.level
    httpx_logger.setLevel(logging.NOTSET)
    yield
    httpx_logger.setLevel(previous)


async def _rendered_failure(awaitable) -> str:
    """Return the exception as a traceback would print it, chained causes included."""
    try:
        await awaitable
    except Exception as exc:
        return "".join(traceback.format_exception(exc))
    pytest.fail("expected the Telegram call to fail")


def _run_cleanup_script(dsn: str, *args: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(CLEANUP_SCRIPT), *args],
        env={**os.environ, "DATABASE_URL": dsn},
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert TOKEN_FRAGMENT not in result.stdout + result.stderr
    return json.loads(result.stdout)


def _queue_telegram_message(db: AsyncSession, dedupe_key: str) -> OutboxMessage:
    return enqueue_outbox_message(
        db,
        kind="owner_alert",
        channel="telegram",
        recipient="42",
        payload={"text": "hello"},
        dedupe_key=dedupe_key,
    )


async def _only_attempt(db: AsyncSession, message: OutboxMessage) -> DeliveryAttempt:
    return await db.scalar(
        select(DeliveryAttempt).where(DeliveryAttempt.outbox_message_id == message.id)
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [302, 403, 500])
async def test_telegram_error_response_keeps_status_but_hides_token(telegram_api, status_code: int):
    telegram_api(lambda _request: httpx.Response(status_code, json={"ok": False}))

    rendered = await _rendered_failure(outbox_service.send_telegram_message("42", "hello"))

    assert TOKEN_FRAGMENT not in rendered
    assert str(status_code) in rendered


@pytest.mark.asyncio
async def test_telegram_transport_failure_hides_token(telegram_api):
    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot reach {request.url}", request=request)

    telegram_api(unreachable)

    rendered = await _rendered_failure(outbox_service.send_telegram_message("42", "hello"))

    assert TOKEN_FRAGMENT not in rendered
    assert "ConnectError" in rendered


@pytest.mark.asyncio
async def test_failed_telegram_delivery_stores_and_logs_no_token(
    db: AsyncSession,
    telegram_api,
    caplog: pytest.LogCaptureFixture,
    default_httpx_log_level,
):
    telegram_api(lambda _request: httpx.Response(403, json={"ok": False}))
    message = _queue_telegram_message(db, "test:token-redaction:delivery")
    await db.commit()

    outbox_worker.configure_logging()
    with caplog.at_level(logging.INFO):
        await outbox_service.process_outbox_batch(db)

    await db.refresh(message)
    attempt = await _only_attempt(db, message)
    assert message.status == "retry"
    assert "403" in message.last_error
    assert TOKEN_FRAGMENT not in message.last_error
    assert TOKEN_FRAGMENT not in attempt.error
    assert TOKEN_FRAGMENT not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("configured_token", "error_text"),
    [
        pytest.param(FAKE_TOKEN, LEAKED_HTTPX_ERROR, id="telegram-url"),
        pytest.param(FAKE_TOKEN, f"token {FAKE_TOKEN} was rejected", id="bare-token"),
        pytest.param(FAKE_TOKEN, "x" * 1980 + FAKE_TOKEN, id="token-across-length-limit"),
        pytest.param(
            FAKE_TOKEN,
            f"see https://api.telegram.org/botold-{TOKEN_FRAGMENT}-shape/getMe",
            id="url-with-previous-token",
        ),
        pytest.param(f"custom-{TOKEN_FRAGMENT}", f"bad custom-{TOKEN_FRAGMENT} value", id="unusual-shape"),
    ],
)
async def test_stored_delivery_error_is_redacted_whatever_raised_it(
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    configured_token: str,
    error_text: str,
):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", configured_token)
    message = _queue_telegram_message(db, "test:token-redaction:any-error")
    await db.commit()

    async def fail_delivery(_message: OutboxMessage) -> None:
        raise RuntimeError(error_text)

    await outbox_service.process_outbox_batch(db, deliver=fail_delivery)

    await db.refresh(message)
    attempt = await _only_attempt(db, message)
    assert TOKEN_FRAGMENT not in message.last_error
    assert TOKEN_FRAGMENT not in attempt.error
    assert "[REDACTED]" in message.last_error


def test_bot_with_rejected_token_exits_without_printing_it():
    result = subprocess.run(
        [sys.executable, "-c", BOT_WITH_REJECTED_TOKEN],
        env={
            **os.environ,
            "PYTHONPATH": str(BACKEND_DIR),
            "PYTHONIOENCODING": "utf-8",
            "TELEGRAM_BOT_TOKEN": FAKE_TOKEN,
        },
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    output = result.stdout + result.stderr

    assert TOKEN_FRAGMENT not in output
    assert "Telegram rejected TELEGRAM_BOT_TOKEN" in output
    assert result.returncode == 1


@pytest.mark.asyncio
async def test_cleanup_script_redacts_stored_tokens_only_with_apply(db: AsyncSession):
    leaked = _queue_telegram_message(db, "test:token-redaction:leaked")
    leaked.last_error = LEAKED_HTTPX_ERROR
    unrelated = _queue_telegram_message(db, "test:token-redaction:unrelated")
    unrelated.last_error = "SMTP timeout at 12:30"
    await db.flush()
    leaked_attempt = DeliveryAttempt(
        outbox_message_id=leaked.id, attempt_number=1, status="failed", error=LEAKED_HTTPX_ERROR
    )
    successful_attempt = DeliveryAttempt(
        outbox_message_id=unrelated.id, attempt_number=1, status="sent"
    )
    db.add_all([leaked_attempt, successful_attempt])
    await db.commit()
    dsn = db.bind.url.render_as_string(hide_password=False)
    expected_counts = {"outbox_messages.last_error": 1, "delivery_attempts.error": 1}

    assert _run_cleanup_script(dsn) == {"applied": False, "rows": expected_counts}
    await db.refresh(leaked)
    assert leaked.last_error == LEAKED_HTTPX_ERROR

    assert _run_cleanup_script(dsn, "--apply") == {"applied": True, "rows": expected_counts}
    for row in (leaked, leaked_attempt, unrelated, successful_attempt):
        await db.refresh(row)
    expected_text = LEAKED_HTTPX_ERROR.replace(FAKE_TOKEN, "[REDACTED]")
    assert leaked.last_error == expected_text
    assert leaked_attempt.error == expected_text
    assert unrelated.last_error == "SMTP timeout at 12:30"
    assert successful_attempt.error is None

    assert _run_cleanup_script(dsn, "--apply")["rows"] == {
        "outbox_messages.last_error": 0,
        "delivery_attempts.error": 0,
    }
