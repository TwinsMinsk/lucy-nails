"""Manage the support bot's Telegram webhook: ``set``, ``info``, ``delete``.

Reads TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET and BACKEND_URL the same way
the backend does (environment, then .env files). Never prints the bot token
or the webhook secret.

    python backend/scripts/telegram_webhook.py set
    python backend/scripts/telegram_webhook.py info
    python backend/scripts/telegram_webhook.py delete

``set`` points Telegram at {BACKEND_URL}/api/telegram/webhook with the secret,
subscribes only to the update types the handler uses and keeps updates that
are already waiting. By default Telegram delivers one update at a time, so a
customer's messages reach the operators in the order they were written.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Run as a plain script: make the backend package importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import TELEGRAM_WEBHOOK_SECRET_PATTERN, settings  # noqa: E402
from app.services.outbox_service import (  # noqa: E402
    TelegramApiError,
    call_telegram_api,
    redact_telegram_token,
)
from app.services.telegram_helpdesk_service import ALLOWED_UPDATES  # noqa: E402

WEBHOOK_PATH = "/api/telegram/webhook"
INFO_FIELDS = (
    "url",
    "pending_update_count",
    "last_error_date",
    "last_error_message",
    "last_synchronization_error_date",
    "max_connections",
    "allowed_updates",
    "ip_address",
)


class ConfigurationError(RuntimeError):
    pass


def webhook_url() -> str:
    return f"{settings.BACKEND_URL.rstrip('/')}{WEBHOOK_PATH}"


def _safe(text: str) -> str:
    secret = settings.TELEGRAM_WEBHOOK_SECRET
    if secret:
        text = text.replace(secret, "[REDACTED]")
    return redact_telegram_token(text)


async def set_webhook(max_connections: int) -> dict:
    secret = settings.TELEGRAM_WEBHOOK_SECRET
    if not TELEGRAM_WEBHOOK_SECRET_PATTERN.fullmatch(secret):
        raise ConfigurationError(
            "TELEGRAM_WEBHOOK_SECRET must be 32-256 characters of A-Z a-z 0-9 _ -"
        )
    url = webhook_url()
    if not url.startswith("https://"):
        raise ConfigurationError("BACKEND_URL must be a public https:// address")
    await call_telegram_api(
        "setWebhook",
        {
            "url": url,
            "secret_token": secret,
            "allowed_updates": list(ALLOWED_UPDATES),
            "drop_pending_updates": False,
            "max_connections": max_connections,
        },
    )
    return {
        "status": "webhook set",
        "url": url,
        "allowed_updates": list(ALLOWED_UPDATES),
        "max_connections": max_connections,
    }


async def webhook_info() -> dict:
    result = await call_telegram_api("getWebhookInfo", {})
    if not isinstance(result, dict):
        return {}
    return {key: result[key] for key in INFO_FIELDS if key in result}


async def delete_webhook() -> dict:
    await call_telegram_api("deleteWebhook", {"drop_pending_updates": False})
    return {"status": "webhook deleted"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    set_parser = commands.add_parser("set", help="point Telegram at the backend webhook")
    set_parser.add_argument(
        "--max-connections",
        type=int,
        default=1,
        choices=range(1, 101),
        metavar="1-100",
        help="simultaneous deliveries (default 1 keeps each chat in order)",
    )
    commands.add_parser("info", help="show the current webhook state")
    commands.add_parser("delete", help="remove the webhook (polling works again)")
    args = parser.parse_args(argv)

    if not settings.TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN is not set", file=sys.stderr)
        return 2
    try:
        if args.command == "set":
            outcome = asyncio.run(set_webhook(args.max_connections))
        elif args.command == "info":
            outcome = asyncio.run(webhook_info())
        else:
            outcome = asyncio.run(delete_webhook())
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except TelegramApiError as exc:
        print(_safe(str(exc)), file=sys.stderr)
        return 1
    print(_safe(json.dumps(outcome, ensure_ascii=False, indent=2)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
