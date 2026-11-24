"""Customer-facing support contact: emails link to the support bot."""

import pytest

from app.core.config import settings
from app.services.email_service import EmailService, support_telegram_url


@pytest.mark.asyncio
async def test_expiry_email_links_to_the_support_bot(monkeypatch: pytest.MonkeyPatch):
    sent: list[str] = []

    async def capture(_email: str, _subject: str, html: str, *args, **kwargs) -> None:
        sent.append(html)

    monkeypatch.setattr(EmailService, "_send", capture)
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "@lucynails_bot")
    assert support_telegram_url() == "https://t.me/lucynails_bot"
    await EmailService.send_access_expired("student@example.com", "Курс")
    assert 'href="https://t.me/lucynails_bot"' in sent[0]
    assert "Если это ошибка или нужна помощь, напишите нам в" in sent[0]


def test_support_link_falls_back_to_the_previous_contact(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "")

    assert support_telegram_url() == "https://t.me/lucysmirnova_nails"
