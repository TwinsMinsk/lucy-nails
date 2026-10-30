"""Archive the uploads directory for the external backup job."""

from __future__ import annotations

import io
import os
import tarfile
import tempfile
from pathlib import Path

from app.core.config import settings

SOURCE_MARKER = ".backup-source-marker"


def _volume_identity(source: Path) -> str | None:
    """Railway's volume ID, but only if `source` really lies on that volume."""
    if not settings.RAILWAY_VOLUME_ID or not settings.RAILWAY_VOLUME_MOUNT_PATH:
        return None
    mount = Path(settings.RAILWAY_VOLUME_MOUNT_PATH).resolve()
    return settings.RAILWAY_VOLUME_ID if source.resolve().is_relative_to(mount) else None


def build_uploads_archive(source: Path) -> Path:
    """Write every uploaded file to a temporary tar; the caller removes it.

    On Railway the source marker is the volume ID instead of a file: a recreated
    volume gets a new ID, so the backup job refuses it without any write to the volume.
    """
    if not source.is_dir():
        raise RuntimeError("Upload storage directory is missing")
    identity = _volume_identity(source)
    descriptor, name = tempfile.mkstemp(prefix="uploads-export-", suffix=".tar")
    archive = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            with tarfile.open(fileobj=stream, mode="w") as bundle:
                for path in sorted(source.rglob("*")):
                    if path.is_symlink():
                        raise RuntimeError("Symlinks are not supported in upload exports")
                    relative = path.relative_to(source).as_posix()
                    if path.is_file() and not (identity and relative == SOURCE_MARKER):
                        bundle.add(path, arcname=relative, recursive=False)
                if identity:
                    body = identity.encode("utf-8")
                    entry = tarfile.TarInfo(SOURCE_MARKER)
                    entry.size = len(body)
                    bundle.addfile(entry, io.BytesIO(body))
    except BaseException:
        archive.unlink(missing_ok=True)
        raise
    return archive
