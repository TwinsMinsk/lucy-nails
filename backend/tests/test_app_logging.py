"""Web request logging: no query strings, no client ids (audit M2, review 1)."""

import json
import logging
from uuid import uuid4

import pytest
from httpx import AsyncClient

from fastapi.staticfiles import StaticFiles
from starlette.routing import Mount

from app import main


class _Collector(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        # Attached to several loggers: a propagated record arrives more than once.
        if not any(seen is record for seen in self.records):
            self.records.append(record)


@pytest.fixture
def collected():
    """Capture every record that reaches any logger of the web process."""
    collector = _Collector()
    names = ["", "app", "app.main", "uvicorn", "uvicorn.access", "uvicorn.error", "httpx"]
    for name in names:
        logging.getLogger(name).addHandler(collector)
    yield collector
    for name in names:
        logging.getLogger(name).removeHandler(collector)


def test_app_logger_is_enabled_at_info_and_uvicorn_access_is_silenced():
    main.configure_app_logging()
    main.configure_app_logging()
    app_logger = logging.getLogger("app")
    assert app_logger.level == logging.INFO
    assert logging.getLogger("app.main").isEnabledFor(logging.INFO)
    ours = [h for h in app_logger.handlers if h.get_name() == main._APP_LOG_HANDLER_NAME]
    assert len(ours) <= 1
    access = logging.getLogger("uvicorn.access")
    assert access.disabled
    assert not access.isEnabledFor(logging.CRITICAL)
    assert logging.getLogger("httpx").level == logging.WARNING


def test_handler_is_added_when_root_logger_is_unconfigured(monkeypatch: pytest.MonkeyPatch):
    root = logging.getLogger()
    app_logger = logging.getLogger("app")
    monkeypatch.setattr(root, "handlers", [])
    monkeypatch.setattr(app_logger, "handlers", [])
    main.configure_app_logging()
    assert [h.get_name() for h in app_logger.handlers] == [main._APP_LOG_HANDLER_NAME]


def test_uvicorn_access_record_with_a_query_string_is_dropped(collected):
    main.silence_uvicorn_access_log()
    # The exact call Uvicorn's httptools/h11 protocol makes for every request.
    logging.getLogger("uvicorn.access").info(
        '%s - "%s %s HTTP/%s" %d',
        "127.0.0.1:5000",
        "GET",
        "/api/payments/orders/order%7Cx/status?token=secret",
        "1.1",
        200,
    )
    assert collected.records == []


def _messages(collector: _Collector) -> list[str]:
    return [record.getMessage() for record in collector.records]


@pytest.mark.asyncio
async def test_request_with_query_secrets_logs_none_of_them(client: AsyncClient, collected):
    secret_path = f"/api/admin/students/{uuid4()}"
    response = await client.get(
        f"{secret_path}?token=secret&email=a@b.c",
        headers={"X-Correlation-ID": "89991234567"},
    )
    assert response.status_code in {401, 403}
    await client.get("/api/payments/orders/order%7Cx/status?token=secret&email=a@b.c")

    messages = _messages(collected)
    assert messages, "the request log must be emitted"
    text = "\n".join(messages)
    assert "secret" not in text
    assert "a@b.c" not in text
    assert "89991234567" not in text
    assert secret_path not in text

    entries = [json.loads(message) for message in messages if '"http_request"' in message]
    first = entries[0]
    assert first["route"] == "/api/admin/students/{user_id}"
    assert set(first) == {"event", "correlation_id", "method", "route", "status", "duration_ms"}
    # The logged id is ours, never the client's header.
    assert first["correlation_id"] != "89991234567"
    assert len(first["correlation_id"]) == 36


@pytest.mark.asyncio
async def test_logged_correlation_id_matches_the_response_when_the_client_sent_none(
    client: AsyncClient, collected
):
    response = await client.get("/api/courses?email=a@b.c")
    entries = [json.loads(m) for m in _messages(collected) if '"http_request"' in m]
    assert entries[-1]["correlation_id"] == response.headers["X-Correlation-ID"]
    assert entries[-1]["route"] == "/api/courses"


def _formatted(collector: _Collector) -> str:
    formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
    return "\n".join(formatter.format(record) for record in collector.records)


@pytest.mark.asyncio
async def test_mounted_uploads_and_unknown_paths_are_logged_by_label_only(
    client: AsyncClient, collected, tmp_path
):
    """A file name may carry an email or a name; a 404 path is arbitrary text."""
    mount = Mount("/uploads", app=StaticFiles(directory=str(tmp_path)), name="uploads-test")
    main.app.router.routes.append(mount)
    try:
        missing = await client.get("/uploads/anna.petrova@example.com-passport.jpg")
        unknown = await client.get("/maria-ivanova@example.com/profile")
    finally:
        main.app.router.routes.remove(mount)

    assert missing.status_code == 404
    assert unknown.status_code == 404
    text = _formatted(collected)
    assert "anna.petrova" not in text
    assert "passport" not in text
    assert "maria-ivanova" not in text
    routes = [json.loads(m)["route"] for m in _messages(collected) if '"http_request"' in m]
    assert routes == ["/uploads/{path}", main.UNMATCHED_ROUTE]

LEAKED_EMAIL = "leak.person@example.com"


async def _failing_order_search():
    """A query that fails in the database driver with an email bound to it."""
    from sqlalchemy import text

    from app.core.database import engine as app_engine

    async with app_engine.connect() as connection:
        await connection.execute(text("SELECT CAST(:email AS INTEGER)"), {"email": LEAKED_EMAIL})


def test_application_engine_hides_bound_parameters():
    from app.core.database import engine as app_engine

    assert app_engine.sync_engine.hide_parameters is True


@pytest.mark.asyncio
async def test_database_failure_traceback_holds_no_query_values(client: AsyncClient, collected):
    main.install_safe_exception_filter()
    main.app.add_api_route("/api/__test_db_failure", _failing_order_search, methods=["GET"])
    try:
        with pytest.raises(Exception) as raised:
            await client.get("/api/__test_db_failure")
    finally:
        main.app.router.routes[:] = [
            route for route in main.app.router.routes
            if getattr(route, "path", None) != "/api/__test_db_failure"
        ]
        # Do not leave a pooled connection bound to this test's event loop
        # for later tests that use the application engine (/health).
        from app.core.database import engine as app_engine

        await app_engine.dispose()
    # What Uvicorn logs for an unhandled exception in the ASGI app.
    logging.getLogger("uvicorn.error").error(
        "Exception in ASGI application\n", exc_info=raised.value
    )

    formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
    app_records = [r for r in collected.records if r.name == "app.main" and r.levelno >= logging.ERROR]
    uvicorn_records = [r for r in collected.records if r.name == "uvicorn.error"]
    assert app_records and uvicorn_records
    for record in [*app_records, *uvicorn_records]:
        output = formatter.format(record)
        assert LEAKED_EMAIL not in output
        assert "leak.person" not in output
        assert "Traceback (most recent call last)" in output
        assert "_failing_order_search" in output
        assert type(raised.value).__qualname__ in output
    request_log = json.loads(app_records[0].getMessage().splitlines()[0])
    assert request_log["status"] == 500
    assert request_log["route"] == "/api/__test_db_failure"
    assert len(request_log["correlation_id"]) == 36