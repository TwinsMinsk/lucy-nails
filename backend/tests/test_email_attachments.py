import base64

import httpx
import pytest

from app.services.email_service import (
    EMAIL_ATTACHMENT_TIMEOUT_SECONDS,
    EMAIL_TIMEOUT_SECONDS,
    EmailAttachment,
    EmailService,
)


class _StubResponse:
    status_code = 200
    text = "{}"


def test_build_mime_message_without_attachments_keeps_current_structure():
    msg = EmailService._build_mime_message(
        "Lucy Nails <noreply@example.com>",
        "student@example.com",
        "Subject",
        "<p>Hi</p>",
    )
    assert msg.get_content_type() == "multipart/alternative"
    parts = msg.get_payload()
    assert len(parts) == 1
    assert parts[0].get_content_type() == "text/html"
    assert parts[0].get_payload(decode=True).decode("utf-8") == "<p>Hi</p>"


def test_build_mime_message_with_attachment_produces_mixed_with_pdf_part():
    pdf_bytes = b"%PDF-1.4 fake pdf content"
    attachment = EmailAttachment(filename="Lucy-Nails-Certificate-LN-0001.pdf", content=pdf_bytes)

    msg = EmailService._build_mime_message(
        "Lucy Nails <noreply@example.com>",
        "student@example.com",
        "Subject",
        "<p>Hi</p>",
        [attachment],
    )

    assert msg.get_content_type() == "multipart/mixed"
    parts = msg.get_payload()
    assert len(parts) == 2

    alternative_part, pdf_part = parts
    assert alternative_part.get_content_type() == "multipart/alternative"
    assert alternative_part.get_payload()[0].get_content_type() == "text/html"

    assert pdf_part.get_content_type() == "application/pdf"
    assert pdf_part.get_filename() == "Lucy-Nails-Certificate-LN-0001.pdf"
    assert "attachment" in pdf_part.get("Content-Disposition", "")
    assert pdf_part.get_payload(decode=True) == pdf_bytes


def test_build_certificate_html_escapes_all_interpolated_values():
    html = EmailService._build_certificate_html(
        student_name="Анна <script>",
        course_title='Курс & "кавычки"',
        certificate_number="LN-0007",
        verify_url="https://example.com/verify/LN-0007",
    )

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "Курс &amp;" in html
    assert "&quot;кавычки&quot;" in html
    assert 'href="https://example.com/verify/LN-0007"' in html


@pytest.mark.asyncio
async def test_send_via_resend_attachment_payload_and_timeout(monkeypatch):
    captured: dict = {}

    class _FakeAsyncClient:
        def __init__(self, timeout=None):
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return _StubResponse()

    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    pdf_bytes = b"%PDF-1.4 fake pdf content"
    attachment = EmailAttachment(filename="Lucy-Nails-Certificate-LN-0007.pdf", content=pdf_bytes)

    await EmailService._send_via_resend(
        "Lucy Nails <noreply@example.com>",
        "student@example.com",
        "Subject",
        "<p>Hi</p>",
        [attachment],
    )

    assert captured["timeout"] == EMAIL_ATTACHMENT_TIMEOUT_SECONDS
    attachments_payload = captured["json"]["attachments"]
    assert len(attachments_payload) == 1
    assert attachments_payload[0]["filename"] == "Lucy-Nails-Certificate-LN-0007.pdf"
    assert base64.b64decode(attachments_payload[0]["content"]) == pdf_bytes

    captured.clear()
    await EmailService._send_via_resend(
        "Lucy Nails <noreply@example.com>",
        "student@example.com",
        "Subject",
        "<p>Hi</p>",
        None,
    )

    assert captured["timeout"] == EMAIL_TIMEOUT_SECONDS
    assert "attachments" not in captured["json"]


@pytest.mark.asyncio
async def test_send_certificate_composes_subject_and_attachment(monkeypatch):
    captured: dict = {}

    async def fake_send(email, subject, html, attachments=None):
        captured["email"] = email
        captured["subject"] = subject
        captured["html"] = html
        captured["attachments"] = attachments

    monkeypatch.setattr(EmailService, "_send", fake_send)

    pdf_bytes = b"%PDF-1.4 fake pdf content"
    await EmailService.send_certificate(
        "student@example.com",
        "Анна Иванова",
        "Базовый маникюр",
        "LN-0007",
        "https://example.com/verify/LN-0007",
        pdf_bytes,
    )

    assert captured["email"] == "student@example.com"
    assert captured["subject"] == "🎓 Ваш сертификат — Lucy Nails Academy"
    assert len(captured["attachments"]) == 1
    attachment = captured["attachments"][0]
    assert attachment.filename == "Lucy-Nails-Certificate-LN-0007.pdf"
    assert attachment.content == pdf_bytes
