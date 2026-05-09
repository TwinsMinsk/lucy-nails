"""
Create or upgrade an admin user in the database referenced by DATABASE_URL.

Connects directly via asyncpg and writes a bcrypt-hashed password compatible
with the backend's passlib[bcrypt] verifier. Self-contained: does not import
backend application code, so it can be run in any minimal Python environment.

Local prerequisites:
    pip install asyncpg bcrypt

Production (Railway injects DATABASE_URL of the linked service):
    railway run -s Backend python scripts/railway/create_admin.py <email> <password>

Local (.env at repo root must contain DATABASE_URL):
    PYTHONPATH=backend python scripts/railway/create_admin.py <email> <password>
"""

from __future__ import annotations

import asyncio
import getpass
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import asyncpg
import bcrypt


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _normalize_dsn(url: str) -> str:
    """Convert SQLAlchemy-style URL to plain libpq form expected by asyncpg."""
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + url[len("postgresql+asyncpg://") :]
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def _load_dotenv_if_missing() -> None:
    """Best-effort: load DATABASE_URL from repo .env when not already in env."""
    if os.environ.get("DATABASE_URL"):
        return
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key == "DATABASE_URL" and value:
            os.environ["DATABASE_URL"] = value
            return


async def upsert_admin(email: str, password: str) -> None:
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        print("ERROR: DATABASE_URL is not set", file=sys.stderr)
        sys.exit(2)

    dsn = _normalize_dsn(raw)
    password_hash = _hash_password(password)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    conn = await asyncpg.connect(dsn)
    try:
        existing = await conn.fetchrow("SELECT id, role FROM users WHERE email = $1", email)
        if existing:
            await conn.execute(
                "UPDATE users SET password_hash = $1, role = 'admin', updated_at = $2 "
                "WHERE email = $3",
                password_hash,
                now,
                email,
            )
            print(f"[OK] Updated existing user to admin: {email} (id={existing['id']})")
        else:
            new_id = uuid.uuid4()
            await conn.execute(
                "INSERT INTO users (id, email, password_hash, role, created_at, updated_at) "
                "VALUES ($1, $2, $3, 'admin', $4, $4)",
                new_id,
                email,
                password_hash,
                now,
            )
            print(f"[OK] Created admin: {email} (id={new_id})")
    finally:
        await conn.close()


def _read_password(argv_password: str | None) -> str:
    if argv_password:
        return argv_password
    pw = getpass.getpass("Password: ")
    if not pw:
        print("ERROR: empty password", file=sys.stderr)
        sys.exit(1)
    confirm = getpass.getpass("Confirm:  ")
    if pw != confirm:
        print("ERROR: passwords do not match", file=sys.stderr)
        sys.exit(1)
    return pw


def main() -> None:
    _load_dotenv_if_missing()
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: create_admin.py <email> [<password>]", file=sys.stderr)
        sys.exit(1)
    email = sys.argv[1].strip().lower()
    password = _read_password(sys.argv[2] if len(sys.argv) == 3 else None)
    asyncio.run(upsert_admin(email, password))


if __name__ == "__main__":
    main()
