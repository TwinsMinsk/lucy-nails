import io
import tarfile

import pytest

from scripts.ops.backup_postgres import bundle_uploads
from scripts.ops.restore_postgres import unpack_bundle


def test_bundle_preserves_database_and_uploaded_files(tmp_path):
    database = tmp_path / "source.dump"
    database.write_bytes(b"sample dump")
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / "image.webp").write_bytes(b"sample upload")
    archive = tmp_path / "backup.tar"
    bundle_uploads(database, uploads, archive)
    restored = tmp_path / "restored"
    restored.mkdir()
    assert unpack_bundle(archive, restored).read_bytes() == database.read_bytes()
    assert (restored / "uploads/image.webp").read_bytes() == b"sample upload"


@pytest.mark.parametrize("name", ["../escape", "/absolute", "uploads/../../escape"])
def test_bundle_rejects_path_escape(tmp_path, name):
    archive = tmp_path / "bad.tar"
    with tarfile.open(archive, "w") as bundle:
        entry = tarfile.TarInfo(name)
        entry.size = 1
        bundle.addfile(entry, io.BytesIO(b"x"))
    with pytest.raises(RuntimeError, match="Unsafe backup member"):
        unpack_bundle(archive, tmp_path / "restored")


def test_restore_refuses_nonempty_database_before_any_archive_work(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from scripts.ops import restore_postgres as restore

    monkeypatch.setattr(
        "sys.argv",
        [
            "restore",
            "s3://backup/archive.tar",
            "--database-url",
            "postgresql://localhost/restore_test",
            "--confirm-database",
            "restore_test",
            "--uploads-dir",
            str(tmp_path / "uploads"),
        ],
    )
    monkeypatch.setattr(restore.shutil, "which", lambda name: name)
    run = Mock(return_value=SimpleNamespace(returncode=0, stdout="t\n"))
    monkeypatch.setattr(restore.subprocess, "run", run)
    download = Mock(side_effect=AssertionError("download must not start"))
    unpack = Mock(side_effect=AssertionError("extraction must not start"))
    monkeypatch.setattr(restore, "download_s3", download)
    monkeypatch.setattr(restore, "unpack_bundle", unpack)
    with pytest.raises(RuntimeError, match="must be empty"):
        restore.main()
    assert run.call_count == 1
    assert run.call_args.args[0][0] == "psql"
    download.assert_not_called()
    unpack.assert_not_called()
    assert not (tmp_path / "uploads").exists()


@pytest.mark.parametrize("marker", [None, "different-source"])
def test_required_upload_backup_rejects_missing_or_wrong_source_marker(
    tmp_path, monkeypatch, marker
):
    from unittest.mock import Mock
    from scripts.ops import backup_postgres as backup

    uploads = tmp_path / "uploads"
    uploads.mkdir()
    if marker is not None:
        (uploads / ".backup-source-marker").write_text(marker, encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "backup",
            "--output-dir",
            str(tmp_path / "backups"),
            "--uploads-dir",
            str(uploads),
        ],
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/backup_test")
    monkeypatch.setenv("BACKUP_REQUIRE_UPLOADS", "true")
    monkeypatch.setenv("BACKUP_UPLOADS_MARKER", "expected-source")
    monkeypatch.setenv("BACKUP_REQUIRE_S3", "false")
    monkeypatch.setenv("BACKUP_S3_URI", "")
    monkeypatch.setattr(backup.shutil, "which", lambda name: name)
    run = Mock()
    monkeypatch.setattr(backup.subprocess, "run", run)
    with pytest.raises(SystemExit) as exc:
        backup.main()
    assert exc.value.code == 2
    run.assert_not_called()
    assert not (tmp_path / "backups").exists()


def test_verified_empty_upload_source_is_valid_and_recorded(tmp_path):
    import json

    database = tmp_path / "database.dump"
    database.write_bytes(b"dump")
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / ".backup-source-marker").write_text("course-source\n", encoding="utf-8")
    archive = tmp_path / "backup.tar"
    summary = bundle_uploads(database, uploads, archive, source_marker="course-source")
    with tarfile.open(archive) as bundle:
        manifest = json.load(bundle.extractfile("manifest.json"))
    assert summary == {"file_count": 0, "source_marker": "course-source"}
    assert manifest["uploads"] == summary
    assert "uploads/.backup-source-marker" in manifest["files"]


@pytest.mark.parametrize("result_code,output", [(1, ""), (0, "unexpected")])
def test_restore_fails_closed_when_empty_target_cannot_be_proven(
    tmp_path, monkeypatch, result_code, output
):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from scripts.ops import restore_postgres as restore

    monkeypatch.setattr(
        "sys.argv",
        [
            "restore",
            str(tmp_path / "missing.dump"),
            "--database-url",
            "postgresql://localhost/restore_test",
            "--confirm-database",
            "restore_test",
        ],
    )
    monkeypatch.setattr(restore.shutil, "which", lambda name: name)
    run = Mock(return_value=SimpleNamespace(returncode=result_code, stdout=output))
    monkeypatch.setattr(restore.subprocess, "run", run)
    with pytest.raises(RuntimeError):
        restore.main()
    assert run.call_count == 1
    assert run.call_args.args[0][0] == "psql"


def test_restore_into_empty_database_does_not_clean_existing_objects(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from scripts.ops import restore_postgres as restore
    from scripts.ops.backup_postgres import sha256

    archive = tmp_path / "backup.dump"
    archive.write_bytes(b"dump")
    archive.with_suffix(".dump.sha256").write_text(
        f"{sha256(archive)}  backup.dump\n", encoding="ascii"
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "restore",
            str(archive),
            "--database-url",
            "postgresql://localhost/restore_test",
            "--confirm-database",
            "restore_test",
        ],
    )
    monkeypatch.setattr(restore.shutil, "which", lambda name: name)
    run = Mock(return_value=SimpleNamespace(returncode=0, stdout="f\n"))
    monkeypatch.setattr(restore.subprocess, "run", run)
    assert restore.main() == 0
    assert [call.args[0][0] for call in run.call_args_list] == ["psql", "pg_restore"]
    command = run.call_args.args[0]
    assert "--clean" not in command and "--if-exists" not in command
    assert "--exit-on-error" in command


@pytest.mark.parametrize(
    "target,confirmation", [("restore_test", "wrong"), ("production", "production")]
)
def test_restore_keeps_database_confirmation_and_production_guard(
    monkeypatch, target, confirmation
):
    from unittest.mock import Mock
    from scripts.ops import restore_postgres as restore

    monkeypatch.setattr(
        "sys.argv",
        [
            "restore",
            "backup.dump",
            "--database-url",
            f"postgresql://localhost/{target}",
            "--confirm-database",
            confirmation,
        ],
    )
    run = Mock()
    monkeypatch.setattr(restore.subprocess, "run", run)
    with pytest.raises(SystemExit) as exc:
        restore.main()
    assert exc.value.code == 2
    run.assert_not_called()


def test_required_upload_backup_requires_marker_configuration(tmp_path, monkeypatch):
    from unittest.mock import Mock
    from scripts.ops import backup_postgres as backup

    uploads = tmp_path / "uploads"
    uploads.mkdir()
    monkeypatch.setattr("sys.argv", ["backup", "--uploads-dir", str(uploads)])
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/backup_test")
    monkeypatch.setenv("BACKUP_REQUIRE_UPLOADS", "true")
    monkeypatch.delenv("BACKUP_UPLOADS_MARKER", raising=False)
    monkeypatch.setattr(backup.shutil, "which", lambda name: name)
    run = Mock()
    monkeypatch.setattr(backup.subprocess, "run", run)
    with pytest.raises(SystemExit) as exc:
        backup.main()
    assert exc.value.code == 2
    run.assert_not_called()


@pytest.mark.asyncio
async def test_restore_preflight_detects_schema_and_nonrelational_objects():
    import asyncpg
    from uuid import uuid4
    from app.core.config import settings
    from scripts.ops import restore_postgres as restore
    from urllib.parse import urlsplit, urlunsplit

    url = restore.postgres_cli_url(settings.DATABASE_URL)
    database = f"restore_preflight_{uuid4().hex}"
    admin = await asyncpg.connect(url)
    await admin.execute(f'CREATE DATABASE "{database}"')
    parsed = urlsplit(url)
    connection = None
    try:
        connection = await asyncpg.connect(
            urlunsplit(parsed._replace(path=f"/{database}"))
        )
        assert await connection.fetchval(restore.NONEMPTY_DATABASE_SQL) is False
        for statement in (
            "CREATE SCHEMA preflight_custom",
            "CREATE FUNCTION public.preflight_function() RETURNS integer LANGUAGE sql AS 'SELECT 1'",
            "CREATE TYPE public.preflight_enum AS ENUM ('value')",
            "CREATE COLLATION public.preflight_collation (provider=libc, locale='C')",
            "CREATE OPERATOR public.=== (FUNCTION=pg_catalog.int4eq, LEFTARG=integer, RIGHTARG=integer)",
            "CREATE PUBLICATION preflight_publication",
            "CREATE FOREIGN DATA WRAPPER preflight_wrapper",
            "CREATE EXTENSION hstore SCHEMA pg_catalog",
        ):
            transaction = connection.transaction()
            await transaction.start()
            try:
                await connection.execute(statement)
                assert (
                    await connection.fetchval(restore.NONEMPTY_DATABASE_SQL) is True
                ), statement
            finally:
                await transaction.rollback()
            assert await connection.fetchval(restore.NONEMPTY_DATABASE_SQL) is False
    finally:
        if connection is not None:
            await connection.close()
        await admin.execute(f'DROP DATABASE "{database}"')
        await admin.close()
