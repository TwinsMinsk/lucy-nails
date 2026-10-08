from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import email_service


@pytest.mark.asyncio
@pytest.mark.parametrize("start_tls", [True, False])
async def test_smtp_transport_uses_configured_starttls(monkeypatch, start_tls):
    config = SimpleNamespace(
        SMTP_HOST="mailpit.railway.internal",
        SMTP_PORT=1025,
        SMTP_USER="sink-user",
        SMTP_PASSWORD="sink-password",
        SMTP_START_TLS=start_tls,
    )
    monkeypatch.setattr(email_service, "settings", config)
    send = AsyncMock()
    monkeypatch.setattr(email_service.aiosmtplib, "send", send)
    await email_service.EmailService._send_via_smtp(
        "sender@example.com", "student@example.com", "Subject", "<p>Body</p>"
    )
    send.assert_awaited_once()
    assert send.call_args.kwargs["start_tls"] is start_tls
    assert send.call_args.kwargs["hostname"] == config.SMTP_HOST
    assert send.call_args.kwargs["port"] == config.SMTP_PORT
    assert send.call_args.kwargs["username"] == config.SMTP_USER
    assert send.call_args.kwargs["password"] == config.SMTP_PASSWORD
    assert send.call_args.kwargs["timeout"] == email_service.EMAIL_TIMEOUT_SECONDS
