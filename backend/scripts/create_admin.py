"""Create or promote the first production admin user.

Usage:
  ADMIN_EMAIL=owner@example.com ADMIN_PASSWORD='long-random-password' python scripts/create_admin.py

For an existing account the password is replaced, the token version is bumped
and every session is revoked in the same transaction, so earlier logins of that
account stop working.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import async_session_maker  # noqa: E402
from app.services.admin_bootstrap import ensure_admin_user  # noqa: E402


async def bootstrap_admin(email: str, password: str) -> str:
    """Create or promote the admin in one transaction; returns the stored email."""
    async with async_session_maker() as db:
        user = await ensure_admin_user(db, email, password)
        await db.commit()
    return user.email


async def main() -> int:
    email = os.getenv("ADMIN_EMAIL", "")
    password = os.getenv("ADMIN_PASSWORD", "")

    if not email or not password:
        print("ADMIN_EMAIL and ADMIN_PASSWORD are required.", file=sys.stderr)
        return 2

    stored_email = await bootstrap_admin(email, password)
    print(f"Admin user is ready: {stored_email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
