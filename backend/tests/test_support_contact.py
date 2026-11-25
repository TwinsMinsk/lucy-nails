"""Customer-facing support contact: emails link to the support bot once it answers."""

import pytest

from app.core.config import settings
from app.services.email_service import EmailService, support_telegram_url


@pytest.fixture
def sent_emails(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    sent: list[str] = []

    async def capture(_email: str, _subject: str, html: str, *args, **kwargs) -> None:
        sent.append(html)

    monkeypatch.setattr(EmailService, "_send", capture)
    return sent


@pytest.mark.asyncio
async def test_expiry_email_links_to_the_support_bot_once_the_help_desk_is_on(
    monkeypatch: pytest.MonkeyPatch, sent_emails: list[str]
):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "@lucynails_bot")
    monkeypatch.setattr(settings, "TELEGRAM_HELPDESK_CHAT_ID", -1001234567890)

    assert support_telegram_url() == "https://t.me/lucynails_bot"
    await EmailService.send_access_expired("student@example.com", "Курс")
    assert 'href="https://t.me/lucynails_bot"' in sent_emails[0]
    assert "Если это ошибка или нужна помощь, напишите нам в" in sent_emails[0]


@pytest.mark.asyncio
async def test_expiry_email_keeps_the_previous_contact_until_the_help_desk_is_set_up(
    monkeypatch: pytest.MonkeyPatch, sent_emails: list[str]
):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "lucynails_bot")
    monkeypatch.setattr(settings, "TELEGRAM_HELPDESK_CHAT_ID", None)

    assert support_telegram_url() == "https://t.me/lucysmirnova_nails"
    await EmailService.send_access_expired("student@example.com", "Курс")
    assert 'href="https://t.me/lucysmirnova_nails"' in sent_emails[0]


def test_support_link_falls_back_to_the_previous_contact_without_a_bot(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "")
    monkeypatch.setattr(settings, "TELEGRAM_HELPDESK_CHAT_ID", -1001234567890)

    assert support_telegram_url() == "https://t.me/lucysmirnova_nails"
