"""
Create or upgrade an admin user in the database referenced by DATABASE_URL.

Thin wrapper around backend/scripts/create_admin.py, i.e. the shared
ensure_admin_user operation: for an existing account it replaces the password,
bumps the token version and revokes every session in the same transaction, and
assigns the owner role when RBAC is seeded. It imports the backend application,
so it runs in the backend environment (requirements.lock) with the backend
settings; the password must be at least 12 characters.

Production (Railway injects the Backend service variables, DATABASE_URL included):
    railway run -s Backend python scripts/railway/create_admin.py <email> [<password>]

Local (DATABASE_URL from the environment or the repository .env):
    python scripts/railway/create_admin.py <email> [<password>]

Without <password> the script prompts for it twice.
"""

from __future__ import annotations

import asyncio
import getpass
import importlib.util
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"


def _load_backend_bootstrap():
    sys.path.insert(0, str(BACKEND_DIR))
    spec = importlib.util.spec_from_file_location(
        "backend_create_admin", BACKEND_DIR / "scripts" / "create_admin.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.bootstrap_admin


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
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: create_admin.py <email> [<password>]", file=sys.stderr)
        sys.exit(1)
    email = sys.argv[1].strip().lower()
    password = _read_password(sys.argv[2] if len(sys.argv) == 3 else None)
    bootstrap_admin = _load_backend_bootstrap()
    try:
        stored_email = asyncio.run(bootstrap_admin(email, password))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"[OK] Admin user is ready: {stored_email}; earlier sessions of this account were revoked")


if __name__ == "__main__":
    main()
