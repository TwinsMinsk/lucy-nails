import io
import tarfile
import tempfile
from pathlib import Path

import pytest

from app.core.config import settings
from app.services.uploads_archive_service import build_uploads_archive

EXPORT_URL = "/api/internal/backup/uploads.tar"
TOKEN = "b" * 32


@pytest.fixture
def uploads(tmp_path, monkeypatch):
    root = tmp_path / "uploads"
    (root / "certificates").mkdir(parents=True)
    (root / ".backup-source-marker").write_text("course-source", encoding="utf-8")
    (root / "banner.webp").write_bytes(b"banner")
    (root / "certificates" / "a.pdf").write_bytes(b"pdf")
    monkeypatch.setattr(settings, "UPLOAD_STORAGE_DIR", str(root))
    monkeypatch.setattr(settings, "BACKUP_EXPORT_TOKEN", TOKEN)
    monkeypatch.setattr(settings, "RAILWAY_VOLUME_ID", "")
    monkeypatch.setattr(settings, "RAILWAY_VOLUME_MOUNT_PATH", "")
    return root


def _exports_left():
    return list(Path(tempfile.gettempdir()).glob("uploads-export-*"))


@pytest.mark.asyncio
async def test_export_requires_configured_token(client, uploads, monkeypatch):
    assert (await client.get(EXPORT_URL)).status_code == 401
    wrong = await client.get(EXPORT_URL, headers={"X-Backup-Token": "x" * 32})
    assert wrong.status_code == 401
    monkeypatch.setattr(settings, "BACKUP_EXPORT_TOKEN", "short")
    short = await client.get(EXPORT_URL, headers={"X-Backup-Token": "short"})
    assert short.status_code == 503


@pytest.mark.asyncio
async def test_export_requires_upload_storage(client, uploads, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_STORAGE_DIR", "")
    response = await client.get(EXPORT_URL, headers={"X-Backup-Token": TOKEN})
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_export_returns_all_files_and_removes_temporary_archive(client, uploads):
    before = set(_exports_left())
    response = await client.get(EXPORT_URL, headers={"X-Backup-Token": TOKEN})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-tar"
    assert int(response.headers["content-length"]) == len(response.content)
    with tarfile.open(fileobj=io.BytesIO(response.content)) as bundle:
        assert sorted(bundle.getnames()) == [
            ".backup-source-marker",
            "banner.webp",
            "certificates/a.pdf",
        ]
        assert bundle.extractfile("certificates/a.pdf").read() == b"pdf"
    assert set(_exports_left()) == before


@pytest.mark.asyncio
async def test_export_failure_is_generic_and_leaves_no_archive(client, uploads, monkeypatch):
    before = set(_exports_left())
    monkeypatch.setattr(settings, "UPLOAD_STORAGE_DIR", str(uploads / "missing"))
    response = await client.get(EXPORT_URL, headers={"X-Backup-Token": TOKEN})
    assert response.status_code == 500
    assert "missing" not in response.text
    assert set(_exports_left()) == before


@pytest.mark.asyncio
async def test_export_is_rate_limited_because_each_call_rebuilds_the_archive(
    client, uploads
):
    statuses = [
        (await client.get(EXPORT_URL, headers={"X-Backup-Token": TOKEN})).status_code
        for _ in range(11)
    ]
    assert statuses == [200] * 10 + [429]


def _archive_members(archive: Path) -> dict[str, bytes]:
    try:
        with tarfile.open(archive) as bundle:
            return {
                member.name: bundle.extractfile(member).read()
                for member in bundle.getmembers()
            }
    finally:
        archive.unlink()


def test_archive_uses_railway_volume_id_as_source_marker(uploads, monkeypatch):
    monkeypatch.setattr(settings, "RAILWAY_VOLUME_ID", "volume-1")
    monkeypatch.setattr(settings, "RAILWAY_VOLUME_MOUNT_PATH", str(uploads.parent))
    members = _archive_members(build_uploads_archive(uploads))
    # The identity wins over a stale file, and the member appears only once.
    assert members[".backup-source-marker"] == b"volume-1"
    assert members["banner.webp"] == b"banner"


def test_archive_does_not_vouch_for_directory_outside_the_volume(
    uploads, tmp_path, monkeypatch
):
    # Upload dir silently off the volume: Railway's ID must not mark it as verified.
    (uploads / ".backup-source-marker").unlink()
    monkeypatch.setattr(settings, "RAILWAY_VOLUME_ID", "volume-1")
    monkeypatch.setattr(
        settings, "RAILWAY_VOLUME_MOUNT_PATH", str(tmp_path / "other-mount")
    )
    members = _archive_members(build_uploads_archive(uploads))
    assert ".backup-source-marker" not in members


def test_archive_keeps_marker_file_outside_railway(uploads):
    members = _archive_members(build_uploads_archive(uploads))
    assert members[".backup-source-marker"] == b"course-source"


def test_archive_refuses_symlinks_and_removes_partial_file(tmp_path, monkeypatch):
    before = set(_exports_left())
    real = tmp_path / "real.webp"
    real.write_bytes(b"x")
    link = tmp_path / "link.webp"
    monkeypatch.setattr(Path, "is_symlink", lambda self: self == link)
    link.write_bytes(b"x")
    with pytest.raises(RuntimeError, match="Symlinks"):
        build_uploads_archive(tmp_path)
    assert set(_exports_left()) == before
