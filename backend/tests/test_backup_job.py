import io
import json
import subprocess
import tarfile
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import Mock

import pytest

from scripts.ops import backup_postgres as backup

BOT_TOKEN = "123456:alert-token-must-not-leak"


@pytest.fixture
def alerts(monkeypatch):
    """Capture Telegram alerts sent by the job instead of calling the API."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    monkeypatch.setenv("TELEGRAM_OWNER_CHAT_ID", "42")
    sent = []

    def fake_urlopen(url, data=None, timeout=None):
        sent.append(urllib.parse.parse_qs(data.decode())["text"][0])
        return io.BytesIO(b"{}")

    monkeypatch.setattr(backup.urllib.request, "urlopen", fake_urlopen)
    return sent


@pytest.fixture
def job_env(monkeypatch, tmp_path):
    for name in (
        "BACKUP_REQUIRE_S3",
        "BACKUP_REQUIRE_UPLOADS",
        "BACKUP_S3_URI",
        "BACKUP_UPLOADS_DIR",
        "BACKUP_UPLOADS_MARKER",
        "BACKUP_UPLOADS_TOKEN",
        "BACKUP_UPLOADS_URL",
        "BACKUP_HEARTBEAT_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:db-secret@db/nails")
    monkeypatch.setattr("sys.argv", ["backup", "--output-dir", str(tmp_path / "out")])
    monkeypatch.setattr(backup.shutil, "which", lambda name: name)


@pytest.mark.parametrize(
    "environment,expected",
    [
        ({"DATABASE_URL": ""}, "DATABASE_URL"),
        ({"BACKUP_REQUIRE_S3": "true"}, "BACKUP_S3_URI"),
        ({"BACKUP_S3_URI": "https://bucket"}, "s3://"),
        ({"BACKUP_REQUIRE_UPLOADS": "true"}, "BACKUP_UPLOADS_"),
        ({"BACKUP_UPLOADS_MARKER": "source"}, "BACKUP_UPLOADS_"),
        ({"BACKUP_UPLOADS_URL": "https://api.test/uploads.tar"}, "TOKEN"),
        (
            {"BACKUP_UPLOADS_URL": "file:///etc/passwd", "BACKUP_UPLOADS_TOKEN": "t"},
            "http",
        ),
    ],
)
def test_configuration_error_reaches_the_owner(
    monkeypatch, alerts, job_env, environment, expected
):
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(SystemExit) as exc:
        backup.main()
    assert exc.value.code == 2
    assert len(alerts) == 1
    assert expected in alerts[0]


def test_missing_pg_dump_reaches_the_owner(monkeypatch, alerts, job_env):
    monkeypatch.setattr(backup.shutil, "which", lambda name: None)
    with pytest.raises(SystemExit):
        backup.main()
    assert len(alerts) == 1
    assert "pg_dump" in alerts[0]


def test_unwritable_output_dir_reaches_the_owner(monkeypatch, alerts, job_env, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("not a directory")
    monkeypatch.setattr(
        "sys.argv", ["backup", "--output-dir", str(blocker / "nested")]
    )
    assert backup.main() == 1
    assert len(alerts) == 1


def test_command_failure_alert_hides_the_database_url(monkeypatch, alerts, job_env):
    error = subprocess.CalledProcessError(
        1, ["pg_dump", "postgresql://user:db-secret@db/nails"]
    )
    monkeypatch.setattr(backup.subprocess, "run", Mock(side_effect=error))
    assert backup.main() == 1
    assert len(alerts) == 1
    assert "CalledProcessError" in alerts[0]
    assert "db-secret" not in alerts[0]


def test_job_failure_alert_explains_its_own_errors(monkeypatch, alerts, job_env, tmp_path):
    _complete_run(monkeypatch, tmp_path)
    monkeypatch.setenv("BACKUP_UPLOADS_DIR", str(tmp_path))
    monkeypatch.setattr(
        backup,
        "bundle_uploads",
        Mock(side_effect=RuntimeError("Backup upload source marker does not match")),
    )
    assert backup.main() == 1
    assert "source marker does not match" in alerts[0]


def test_undelivered_alert_is_logged_without_token(monkeypatch, capsys):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    monkeypatch.setenv("TELEGRAM_OWNER_CHAT_ID", "42")
    monkeypatch.setattr(
        backup.urllib.request, "urlopen", Mock(side_effect=OSError("network down"))
    )
    backup.notify_failure("boom")
    err = capsys.readouterr().err
    assert "OSError" in err
    assert BOT_TOKEN not in err


def test_missing_alert_channel_is_logged(monkeypatch, capsys):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_OWNER_CHAT_ID", raising=False)
    backup.notify_failure("boom")
    assert "not configured" in capsys.readouterr().err


class _ExportHandler(BaseHTTPRequestHandler):
    body = b""
    declared_length = None
    status = 200
    tokens: list = []

    def do_GET(self):
        type(self).tokens.append(self.headers.get("X-Backup-Token"))
        self.send_response(self.status)
        length = self.declared_length
        self.send_header("Content-Length", str(len(self.body) if length is None else length))
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *args):
        pass


@pytest.fixture
def export_server():
    handler = type(
        "Handler", (_ExportHandler,), {"tokens": [], "body": b"", "declared_length": None}
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield handler, f"http://127.0.0.1:{server.server_port}/uploads.tar"
    server.shutdown()
    server.server_close()
    thread.join()


def _tar(*members):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as bundle:
        for name, content in members:
            entry = tarfile.TarInfo(name)
            entry.size = len(content)
            bundle.addfile(entry, io.BytesIO(content))
    return stream.getvalue()


def test_fetch_uploads_extracts_export_with_token(export_server, tmp_path):
    handler, url = export_server
    handler.body = _tar(
        (".backup-source-marker", b"course-source"),
        ("certificates/a.pdf", b"pdf"),
    )
    uploads = backup.fetch_uploads(url, "export-token", tmp_path)
    assert handler.tokens == ["export-token"]
    assert (uploads / ".backup-source-marker").read_bytes() == b"course-source"
    assert (uploads / "certificates/a.pdf").read_bytes() == b"pdf"


def test_fetch_uploads_rejects_truncated_export(export_server, tmp_path):
    handler, url = export_server
    handler.body = _tar(("a.webp", b"content"))
    handler.declared_length = len(handler.body) + 10
    with pytest.raises(RuntimeError, match="truncated"):
        backup.fetch_uploads(url, "export-token", tmp_path)


def test_fetch_uploads_reports_http_status_without_token(export_server, tmp_path):
    handler, url = export_server
    handler.status = 401
    with pytest.raises(RuntimeError, match="HTTP 401") as exc:
        backup.fetch_uploads(url, "export-token", tmp_path)
    assert "export-token" not in str(exc.value)


@pytest.mark.parametrize("name", ["../escape", "/absolute", "a/../../escape"])
def test_fetch_uploads_rejects_path_escape(export_server, tmp_path, name):
    handler, url = export_server
    handler.body = _tar((name, b"x"))
    with pytest.raises(RuntimeError, match="Unsafe uploads export"):
        backup.fetch_uploads(url, "export-token", tmp_path)
    assert not (tmp_path / "escape").exists()


def test_fetch_uploads_rejects_links(export_server, tmp_path):
    handler, url = export_server
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as bundle:
        entry = tarfile.TarInfo("link")
        entry.type = tarfile.SYMTYPE
        entry.linkname = "/etc/passwd"
        bundle.addfile(entry)
    handler.body = stream.getvalue()
    with pytest.raises(RuntimeError, match="Unsafe uploads export"):
        backup.fetch_uploads(url, "export-token", tmp_path)


def _complete_run(monkeypatch, tmp_path):
    """Fake pg_dump and capture the JSON summary inputs of a successful run."""

    def fake_run(command, check):
        target = command[command.index("--file") + 1]
        with open(target, "wb") as stream:
            stream.write(b"dump")

    monkeypatch.setattr(backup.subprocess, "run", fake_run)
    monkeypatch.setattr(
        "sys.argv", ["backup", "--output-dir", str(tmp_path / "out")]
    )


def test_job_bundles_exported_uploads_and_checks_marker(
    monkeypatch, job_env, export_server, tmp_path, capsys
):
    handler, url = export_server
    handler.body = _tar((".backup-source-marker", b"course-source"), ("a.webp", b"img"))
    _complete_run(monkeypatch, tmp_path)
    monkeypatch.setenv("BACKUP_UPLOADS_URL", url)
    monkeypatch.setenv("BACKUP_UPLOADS_TOKEN", "export-token")
    monkeypatch.setenv("BACKUP_UPLOADS_MARKER", "course-source")
    monkeypatch.setenv("BACKUP_REQUIRE_UPLOADS", "true")
    assert backup.main() == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["includes_uploads"] is True
    assert summary["uploads"] == {"file_count": 1, "source_marker": "course-source"}
    assert summary["path"].endswith(".tar")
    with tarfile.open(summary["path"]) as bundle:
        names = bundle.getnames()
    assert {"database.dump", "uploads/a.webp", "manifest.json"} <= set(names)


def test_job_fails_when_export_comes_from_unmarked_volume(
    monkeypatch, alerts, job_env, tmp_path
):
    # A volume that was recreated empty must not produce a "successful" backup.
    uploads = tmp_path / "exported"
    uploads.mkdir()
    monkeypatch.setattr(backup, "fetch_uploads", lambda *args: uploads)
    _complete_run(monkeypatch, tmp_path)
    monkeypatch.setenv("BACKUP_UPLOADS_URL", "https://api.test/uploads.tar")
    monkeypatch.setenv("BACKUP_UPLOADS_TOKEN", "export-token")
    monkeypatch.setenv("BACKUP_UPLOADS_MARKER", "course-source")
    assert backup.main() == 1
    assert "marker" in alerts[0]
    assert not list((tmp_path / "out").glob("lucy-nails-*"))


def test_heartbeat_is_sent_only_after_success(monkeypatch, job_env, tmp_path):
    pings = []
    monkeypatch.setattr(
        backup.urllib.request,
        "urlopen",
        lambda url, data=None, timeout=None: pings.append(url) or io.BytesIO(b"OK"),
    )
    monkeypatch.setenv("BACKUP_HEARTBEAT_URL", "https://monitor.test/ping/1")
    _complete_run(monkeypatch, tmp_path)
    assert backup.main() == 0
    assert pings == ["https://monitor.test/ping/1"]

    pings.clear()
    monkeypatch.setattr(
        backup.subprocess,
        "run",
        Mock(side_effect=subprocess.CalledProcessError(1, ["pg_dump"])),
    )
    assert backup.main() == 1
    assert pings == []


def test_heartbeat_failure_does_not_fail_finished_backup(
    monkeypatch, job_env, tmp_path, capsys
):
    monkeypatch.setattr(
        backup.urllib.request, "urlopen", Mock(side_effect=OSError("monitor down"))
    )
    monkeypatch.setenv("BACKUP_HEARTBEAT_URL", "https://monitor.test/ping/secret-id")
    _complete_run(monkeypatch, tmp_path)
    assert backup.main() == 0
    captured = capsys.readouterr()
    assert "Heartbeat" in captured.err
    assert "secret-id" not in captured.err


def test_uploaded_copy_is_required_before_heartbeat(monkeypatch, job_env, tmp_path):
    pings = []
    monkeypatch.setattr(
        backup.urllib.request,
        "urlopen",
        lambda url, data=None, timeout=None: pings.append(url) or io.BytesIO(b"OK"),
    )
    monkeypatch.setenv("BACKUP_HEARTBEAT_URL", "https://monitor.test/ping/1")
    monkeypatch.setenv("BACKUP_S3_URI", "s3://bucket/prefix")
    monkeypatch.setattr(
        backup, "upload_to_s3", Mock(side_effect=RuntimeError("upload refused"))
    )
    _complete_run(monkeypatch, tmp_path)
    assert backup.main() == 1
    assert pings == []
