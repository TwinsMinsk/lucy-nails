"""Remove token-bearing links from already delivered outbox payloads.

Activation, password-reset and login emails used to keep their full link in
outbox_messages.payload after delivery, so a reader of the database or of a
fresh backup could use a link that was still valid. The worker now replaces
such links once a message is sent or dead-lettered; this one-off script does
the same for rows written before that change.

Only rows in status "sent" or "dead_letter" are touched: pending and retry
messages still need their link. Dry run by default: reports how many rows
would change. --apply updates them. Safe to repeat. Prints row counts only,
never the stored values. Run it after every worker has been restarted on the
fixed code.

Required environment: DATABASE_URL. Self-contained: needs only asyncpg and does
not import backend application code.

    python scripts/redact_outbox_links.py
    python scripts/redact_outbox_links.py --apply
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re

import asyncpg

# Same expression as SECRET_URL_PATTERN in backend/app/services/outbox_service.py.
SECRET_URL_PATTERN = re.compile(
    r"""https?://[^\s"'<>]*?[?&][^\s"'<>=&]*token=[^\s"'<>]*""",
    re.IGNORECASE,
)
REDACTED = "[REDACTED]"
FINISHED_STATUSES = ("sent", "dead_letter")


def asyncpg_dsn(value: str) -> str:
    return value.replace("postgresql+asyncpg://", "postgresql://", 1)


def redact_payload(value):
    if isinstance(value, str):
        return SECRET_URL_PATTERN.sub(REDACTED, value)
    if isinstance(value, dict):
        return {key: redact_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    return value


async def redact(dsn: str, *, apply: bool) -> dict[str, int]:
    connection = await asyncpg.connect(dsn)
    changed = 0
    try:
        async with connection.transaction():
            rows = await connection.fetch(
                """
                SELECT id, payload::text AS payload
                FROM outbox_messages
                WHERE status = ANY($1::text[]) AND payload::text ~* 'token='
                FOR UPDATE
                """,
                list(FINISHED_STATUSES),
            )
            for row in rows:
                payload = json.loads(row["payload"])
                redacted = redact_payload(payload)
                if redacted == payload:
                    continue
                changed += 1
                if apply:
                    await connection.execute(
                        "UPDATE outbox_messages SET payload = $1::json WHERE id = $2",
                        json.dumps(redacted, ensure_ascii=False),
                        row["id"],
                    )
    finally:
        await connection.close()
    return {"outbox_messages.payload": changed}


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
