"""Create a compressed PostgreSQL backup and optionally upload it to S3.

Required environment: DATABASE_URL. Optional: BACKUP_DIR, BACKUP_S3_URI,
BACKUP_RETENTION_DAYS, BACKUP_S3_SSE (AES256 or aws:kms), BACKUP_S3_KMS_KEY_ID,
TELEGRAM_BOT_TOKEN and TELEGRAM_OWNER_CHAT_ID for failure alerts,
BACKUP_HEARTBEAT_URL for a dead man's switch pinged after each complete run.
Uploaded files come from a mounted BACKUP_UPLOADS_DIR or, when the volume belongs
to another service, from BACKUP_UPLOADS_URL with BACKUP_UPLOADS_TOKEN.
BACKUP_REQUIRE_UPLOADS=true requires one of those and BACKUP_UPLOADS_MARKER.
The latter must match the source root's .backup-source-marker UTF-8 contents;
on Railway the backend export fills that member with the volume's RAILWAY_VOLUME_ID.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


def postgres_cli_url(value: str) -> str:
    return value.replace("postgresql+asyncpg://", "postgresql://", 1)


def log_warning(detail: str) -> None:
    print(json.dumps({"status": "warning", "detail": detail}), file=sys.stderr)


def notify_failure(message: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_OWNER_CHAT_ID", "").strip()
    if not token or not chat_id:
        log_warning("Failure alert is not configured")
        return
    payload = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": f"⚠️ Backup Lucy Smirnova failed: {message[:1000]}"}
    ).encode()
    try:
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/sendMessage", payload, timeout=10
        ).read()
    except Exception as exc:
        log_warning(f"Failure alert was not delivered: {type(exc).__name__}")


def ping_heartbeat() -> None:
    url = os.getenv("BACKUP_HEARTBEAT_URL", "").strip()
    if not url:
        return
    try:
        urllib.request.urlopen(url, timeout=10).read()
    except Exception as exc:
        log_warning(f"Heartbeat ping failed: {type(exc).__name__}")


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
    if sse not in {"AES256", "aws:kms"}:
        raise RuntimeError("Encrypted S3 backups require AES256 or aws:kms")
    command.extend(["--sse", sse])
    kms_key = os.getenv("BACKUP_S3_KMS_KEY_ID", "").strip()
    if kms_key:
        command.extend(["--sse-kms-key-id", kms_key])
    subprocess.run(command, check=True)


def verify_uploads_source(uploads: Path, expected_marker: str | None) -> None:
    if not uploads.is_dir():
        raise RuntimeError("Backup upload directory is missing")
    if expected_marker:
        marker = uploads / ".backup-source-marker"
        if marker.is_symlink() or not marker.is_file():
            raise RuntimeError("Backup upload source marker is missing or unsafe")
        if marker.read_text(encoding="utf-8").strip() != expected_marker:
            raise RuntimeError("Backup upload source marker does not match")


def uploads_url_is_safe(url: str) -> bool:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme == "https":
        return True
    host = parts.hostname or ""
    return parts.scheme == "http" and (
        host.endswith(".railway.internal") or host in {"localhost", "127.0.0.1", "::1"}
    )


def fetch_uploads(url: str, token: str, directory: Path) -> Path:
    archive = directory / "uploads-export.tar"
    request = urllib.request.Request(url, headers={"X-Backup-Token": token})
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            declared = response.headers.get("Content-Length")
            with archive.open("wb") as target:
                shutil.copyfileobj(response, target)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Uploads export returned HTTP {exc.code}") from None
    except urllib.error.URLError:
        raise RuntimeError("Uploads export is unreachable") from None
    if declared is None or archive.stat().st_size != int(declared):
        raise RuntimeError("Uploads export was truncated")

    uploads = directory / "uploads-export"
    uploads.mkdir()
    root = uploads.resolve()
    with tarfile.open(archive, "r") as bundle:
        for member in bundle:
            target = (uploads / member.name).resolve()
            if (
                not member.isfile()
                or not target.is_relative_to(root)
                or target.exists()
            ):
                raise RuntimeError("Unsafe uploads export member")
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.extractfile(member) as source, target.open("wb") as stream:
                shutil.copyfileobj(source, stream)
    return uploads


def bundle_uploads(
    database: Path,
    uploads: Path,
    destination: Path,
    *,
    source_marker: str | None = None,
) -> dict:
    verify_uploads_source(uploads, source_marker)
    summary = {"file_count": 0, "source_marker": source_marker}
    manifest = {"database.dump": sha256(database)}
    with tarfile.open(destination, "w") as archive:
        archive.add(database, arcname="database.dump", recursive=False)
        for path in sorted(uploads.rglob("*")):
            if path.is_symlink():
                raise RuntimeError("Symlinks are not supported in upload backups")
            if path.is_file():
                relative = f"uploads/{path.relative_to(uploads).as_posix()}"
                manifest[relative] = sha256(path)
                if path.relative_to(uploads).as_posix() != ".backup-source-marker":
                    summary["file_count"] += 1
                archive.add(path, arcname=relative, recursive=False)
        body = json.dumps({"version": 1, "files": manifest, "uploads": summary}).encode(
            "utf-8"
        )
        import io

        entry = tarfile.TarInfo("manifest.json")
        entry.size = len(body)
        archive.addfile(entry, io.BytesIO(body))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=os.getenv("BACKUP_DIR", "backups"))
    parser.add_argument("--uploads-dir", default=os.getenv("BACKUP_UPLOADS_DIR", ""))
    args = parser.parse_args()

    def config_error(message: str) -> None:
        # parser.error exits immediately, so the owner must be told first.
        notify_failure(f"configuration error: {message}")
        parser.error(message)

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        config_error("DATABASE_URL is required")
    pg_dump = shutil.which("pg_dump")
    if not pg_dump:
        config_error("pg_dump is not installed or not in PATH")
    require_uploads = os.getenv("BACKUP_REQUIRE_UPLOADS", "false").lower() == "true"
    source_marker = os.getenv("BACKUP_UPLOADS_MARKER", "").strip() or None
    uploads_url = os.getenv("BACKUP_UPLOADS_URL", "").strip()
    uploads_token = os.getenv("BACKUP_UPLOADS_TOKEN", "").strip()
    has_uploads_source = bool(args.uploads_dir or uploads_url)
    if args.uploads_dir and uploads_url:
        config_error("Set either BACKUP_UPLOADS_DIR or BACKUP_UPLOADS_URL, not both")
    if uploads_url and not uploads_url_is_safe(uploads_url):
        config_error("BACKUP_UPLOADS_URL must use https, http only for a private host")
    if uploads_url and not uploads_token:
        config_error("BACKUP_UPLOADS_TOKEN is required with BACKUP_UPLOADS_URL")
    if require_uploads and not has_uploads_source:
        config_error(
            "BACKUP_UPLOADS_DIR or BACKUP_UPLOADS_URL is required for a complete backup"
        )
    if require_uploads and not source_marker:
        config_error("BACKUP_UPLOADS_MARKER is required for a verified upload source")
    if source_marker and not has_uploads_source:
        config_error(
            "BACKUP_UPLOADS_DIR or BACKUP_UPLOADS_URL is required "
            "when a source marker is configured"
        )
    if args.uploads_dir:
        try:
            verify_uploads_source(Path(args.uploads_dir).resolve(), source_marker)
        except (OSError, UnicodeError, RuntimeError) as exc:
            config_error(str(exc))
    s3_uri = os.getenv("BACKUP_S3_URI", "").strip()
    if os.getenv("BACKUP_REQUIRE_S3", "false").lower() == "true" and not s3_uri:
        config_error("BACKUP_S3_URI is required for external backups")
    if s3_uri and not s3_uri.startswith("s3://"):
        config_error("BACKUP_S3_URI must be an s3:// destination")

    output_dir = Path(args.output_dir).resolve()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    final_path = (
        output_dir / f"lucy-nails-{timestamp}{'.tar' if has_uploads_source else '.dump'}"
    )
    partial_path = output_dir / f".{final_path.name}.partial"

    uploads_summary = None
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="lucy-backup-") as temporary:
            dump_path = Path(temporary) / "database.dump"
            subprocess.run(
                [
                    pg_dump,
                    "--format=custom",
                    "--compress=9",
                    "--no-owner",
                    "--no-privileges",
                    "--file",
                    str(dump_path),
                    postgres_cli_url(database_url),
                ],
                check=True,
            )
            if has_uploads_source:
                # Fetched after pg_dump, so every file the dump references is included.
                uploads_source = (
                    Path(args.uploads_dir).resolve()
                    if args.uploads_dir
                    else fetch_uploads(uploads_url, uploads_token, Path(temporary))
                )
                uploads_summary = bundle_uploads(
                    dump_path,
                    uploads_source,
                    partial_path,
                    source_marker=source_marker,
                )
            else:
                shutil.copyfile(dump_path, partial_path)
        partial_path.replace(final_path)
        checksum = sha256(final_path)
        checksum_path = final_path.with_suffix(final_path.suffix + ".sha256")
        checksum_path.write_text(f"{checksum}  {final_path.name}\n", encoding="ascii")

        if s3_uri:
            upload_to_s3(final_path, s3_uri)
            upload_to_s3(checksum_path, s3_uri)

        retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "14"))
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        for candidate in output_dir.glob("lucy-nails-*"):
            if not candidate.is_file() or not candidate.name.endswith(
                (".dump", ".tar", ".sha256")
            ):
                continue
            modified = datetime.fromtimestamp(candidate.stat().st_mtime, timezone.utc)
            if modified < cutoff:
                candidate.unlink()

        ping_heartbeat()
        print(
            json.dumps(
                {
                    "status": "ok",
                    "path": str(final_path),
                    "sha256": checksum,
                    "uploaded": bool(s3_uri),
                    "includes_uploads": has_uploads_source,
                    "uploads": uploads_summary,
                }
            )
        )
        return 0
    except Exception as exc:
        # Cleanup must not stop the alert: an unusable output path raises here too.
        try:
            partial_path.unlink(missing_ok=True)
        except OSError:
            pass
        # Only this script's RuntimeErrors are safe to quote: a CalledProcessError
        # message contains the pg_dump command line with the database password.
        reason = str(exc) if type(exc) is RuntimeError else type(exc).__name__
        detail = f"Backup failed: {reason}"
        notify_failure(detail)
        print(json.dumps({"status": "error", "detail": detail}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
