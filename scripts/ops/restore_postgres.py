"""Restore a pg_dump custom archive into an explicitly confirmed database."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import tempfile
import urllib.parse
from pathlib import Path


def postgres_cli_url(value: str) -> str:
    return value.replace("postgresql+asyncpg://", "postgresql://", 1)


def database_name(value: str) -> str:
    return urllib.parse.unquote(urllib.parse.urlparse(postgres_cli_url(value)).path.lstrip("/"))


def verify_checksum(path: Path) -> None:
    checksum_path = path.with_suffix(path.suffix + ".sha256")
    if not checksum_path.exists():
        raise RuntimeError(f"Checksum file not found: {checksum_path}")
    expected = checksum_path.read_text(encoding="ascii").split()[0]
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != expected:
        raise RuntimeError("Backup checksum mismatch")


def download_s3(source: str, directory: Path) -> Path:
    aws = shutil.which("aws")
    if not aws:
        raise RuntimeError("aws CLI is required for an s3:// source")
    target = directory / Path(source).name
    command = [aws]
    endpoint = os.getenv("BACKUP_S3_ENDPOINT", "").strip()
    if endpoint:
        command.extend(["--endpoint-url", endpoint])
    subprocess.run([*command, "s3", "cp", source, str(target)], check=True)
    subprocess.run(
        [*command, "s3", "cp", f"{source}.sha256", f"{target}.sha256"],
        check=True,
    )
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Local .dump path or s3:// URI")
    parser.add_argument("--database-url", default=os.getenv("RESTORE_DATABASE_URL", ""))
    parser.add_argument("--confirm-database", required=True)
    parser.add_argument("--allow-production", action="store_true")
    args = parser.parse_args()
    if not args.database_url:
        parser.error("--database-url or RESTORE_DATABASE_URL is required")
    target_name = database_name(args.database_url)
    if args.confirm_database != target_name:
        parser.error("--confirm-database must exactly match the target database name")
    safe_markers = ("test", "restore", "drill", "staging")
    if not args.allow_production and not any(marker in target_name.lower() for marker in safe_markers):
        parser.error("target does not look like a restore/test database; use --allow-production explicitly")
    pg_restore = shutil.which("pg_restore")
    if not pg_restore:
        parser.error("pg_restore is not installed or not in PATH")

    with tempfile.TemporaryDirectory(prefix="lucy-restore-") as temp:
        archive = (
            download_s3(args.source, Path(temp))
            if args.source.startswith("s3://")
            else Path(args.source).resolve()
        )
        if not archive.is_file():
            parser.error(f"backup not found: {archive}")
        verify_checksum(archive)
        subprocess.run(
            [
                pg_restore,
                "--clean",
                "--if-exists",
                "--exit-on-error",
                "--no-owner",
                "--no-privileges",
                "--dbname",
                postgres_cli_url(args.database_url),
                str(archive),
            ],
            check=True,
        )
    print(f"Restore completed into explicitly confirmed database: {target_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
