"""Archive the uploads directory for the external backup job."""

from __future__ import annotations

import os
import tarfile
import tempfile
from pathlib import Path


def build_uploads_archive(source: Path) -> Path:
    """Write every uploaded file to a temporary tar; the caller removes it."""
    if not source.is_dir():
        raise RuntimeError("Upload storage directory is missing")
    descriptor, name = tempfile.mkstemp(prefix="uploads-export-", suffix=".tar")
    archive = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            with tarfile.open(fileobj=stream, mode="w") as bundle:
                for path in sorted(source.rglob("*")):
                    if path.is_symlink():
                        raise RuntimeError("Symlinks are not supported in upload exports")
                    if path.is_file():
                        bundle.add(
                            path,
                            arcname=path.relative_to(source).as_posix(),
                            recursive=False,
                        )
    except BaseException:
        archive.unlink(missing_ok=True)
        raise
    return archive
