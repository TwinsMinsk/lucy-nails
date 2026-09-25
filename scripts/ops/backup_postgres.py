"""Create a compressed PostgreSQL backup and optionally upload it to S3.

Required environment: DATABASE_URL. Optional: BACKUP_DIR, BACKUP_S3_URI,
BACKUP_RETENTION_DAYS, BACKUP_S3_SSE (AES256 or aws:kms), BACKUP_S3_KMS_KEY_ID,
TELEGRAM_BOT_TOKEN and TELEGRAM_OWNER_CHAT_ID for failure alerts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


def postgres_cli_url(value: str) -> str:
    return value.replace("postgresql+asyncpg://", "postgresql://", 1)


def notify_failure(message: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_OWNER_CHAT_ID", "").strip()
    if not token or not chat_id:
        return
    payload = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": f"⚠️ Backup Lucy Nails failed: {message[:1000]}"}
    ).encode()
    try:
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/sendMessage", payload, timeout=10
        ).read()
    except Exception:
        pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def upload_to_s3(path: Path, destination: str) -> None:
    aws = shutil.which("aws")
    if not aws:
        raise RuntimeError("aws CLI is required when BACKUP_S3_URI is configured")
    target = f"{destination.rstrip('/')}/{path.name}"
    command = [aws]
    endpoint = os.getenv("BACKUP_S3_ENDPOINT", "").strip()
    if endpoint:
        command.extend(["--endpoint-url", endpoint])
    command.extend(["s3", "cp", str(path), target])
    sse = os.getenv("BACKUP_S3_SSE", "AES256").strip()
    if sse:
        command.extend(["--sse", sse])
    kms_key = os.getenv("BACKUP_S3_KMS_KEY_ID", "").strip()
    if kms_key:
        command.extend(["--sse-kms-key-id", kms_key])
    subprocess.run(command, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=os.getenv("BACKUP_DIR", "backups"))
    args = parser.parse_args()
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        parser.error("DATABASE_URL is required")
    pg_dump = shutil.which("pg_dump")
    if not pg_dump:
        parser.error("pg_dump is not installed or not in PATH")

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    final_path = output_dir / f"lucy-nails-{timestamp}.dump"
    partial_path = output_dir / f".{final_path.name}.partial"

    try:
        subprocess.run(
            [
                pg_dump,
                "--format=custom",
                "--compress=9",
                "--no-owner",
                "--no-privileges",
                "--file",
                str(partial_path),
                postgres_cli_url(database_url),
            ],
            check=True,
        )
        partial_path.replace(final_path)
        checksum = sha256(final_path)
        checksum_path = final_path.with_suffix(final_path.suffix + ".sha256")
        checksum_path.write_text(f"{checksum}  {final_path.name}\n", encoding="ascii")

        s3_uri = os.getenv("BACKUP_S3_URI", "").strip()
        if s3_uri:
            upload_to_s3(final_path, s3_uri)
            upload_to_s3(checksum_path, s3_uri)

        retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "14"))
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        for candidate in output_dir.glob("lucy-nails-*.dump*"):
            modified = datetime.fromtimestamp(candidate.stat().st_mtime, timezone.utc)
            if modified < cutoff:
                candidate.unlink()

        print(
            json.dumps(
                {
                    "status": "ok",
                    "path": str(final_path),
                    "sha256": checksum,
                    "uploaded": bool(s3_uri),
                }
            )
        )
        return 0
    except Exception as exc:
        partial_path.unlink(missing_ok=True)
        notify_failure(str(exc))
        print(json.dumps({"status": "error", "detail": str(exc)[:1000]}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
