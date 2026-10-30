"""Remove Telegram bot tokens from stored outbox delivery errors.

The worker used to store httpx error text, which contains the request URL and
therefore the bot token, in outbox_messages.last_error and delivery_attempts.error.

Dry run by default: reports how many rows would change. --apply updates them.
Safe to repeat. Prints row counts only, never the stored values. Run it after
every worker has been restarted on the fixed code.

Required environment: DATABASE_URL. Self-contained: needs only asyncpg and does
not import backend application code.

    python scripts/ops/redact_telegram_tokens.py
    python scripts/ops/redact_telegram_tokens.py --apply
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os

import asyncpg

# Same expression as TELEGRAM_TOKEN_PATTERN in backend/app/services/outbox_service.py;
# valid both for Python and for PostgreSQL regular expressions.
TOKEN_PATTERN = r"""(?<=api\.telegram\.org/bot)[^/\s'"]+|\d{5,}:[A-Za-z0-9_-]{20,}"""
REDACTED = "[REDACTED]"
COLUMNS = (("outbox_messages", "last_error"), ("delivery_attempts", "error"))


def asyncpg_dsn(value: str) -> str:
    return value.replace("postgresql+asyncpg://", "postgresql://", 1)


async def redact(dsn: str, *, apply: bool) -> dict[str, int]:
    rows: dict[str, int] = {}
    connection = await asyncpg.connect(dsn)
    try:
        async with connection.transaction():
            for table, column in COLUMNS:
                redacted = f"regexp_replace({column}, $1, $2, 'g')"
                where = f"{redacted} <> {column}"
                if apply:
                    status = await connection.execute(
                        f"UPDATE {table} SET {column} = {redacted} WHERE {where}",
                        TOKEN_PATTERN,
                        REDACTED,
                    )
                    rows[f"{table}.{column}"] = int(status.rsplit(" ", 1)[1])
                else:
                    rows[f"{table}.{column}"] = await connection.fetchval(
                        f"SELECT count(*) FROM {table} WHERE {where}",
                        TOKEN_PATTERN,
                        REDACTED,
                    )
    finally:
        await connection.close()
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--apply", action="store_true", help="update the rows instead of counting them"
    )
    args = parser.parse_args()
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        parser.error("DATABASE_URL is required")
    rows = asyncio.run(redact(asyncpg_dsn(database_url), apply=args.apply))
    print(json.dumps({"applied": args.apply, "rows": rows}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
