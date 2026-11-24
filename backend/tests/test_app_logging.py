"""The web entry point emits the INFO request log (audit M2)."""

import json
import logging

import pytest
from httpx import AsyncClient

from app import main


class _Collector(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_app_logger_is_enabled_at_info_without_touching_uvicorn():
    uvicorn_access_handlers = list(logging.getLogger("uvicorn.access").handlers)
    main.configure_app_logging()
    main.configure_app_logging()
    app_logger = logging.getLogger("app")
    assert app_logger.level == logging.INFO
    assert logging.getLogger("app.main").isEnabledFor(logging.INFO)
    # Idempotent: never more than one handler of ours.
    ours = [h for h in app_logger.handlers if h.get_name() == main._APP_LOG_HANDLER_NAME]
    assert len(ours) <= 1
    assert logging.getLogger("uvicorn.access").handlers == uvicorn_access_handlers
    assert logging.getLogger("httpx").level == logging.WARNING


def test_handler_is_added_when_root_logger_is_unconfigured(monkeypatch: pytest.MonkeyPatch):
    root = logging.getLogger()
    app_logger = logging.getLogger("app")
    monkeypatch.setattr(root, "handlers", [])
    monkeypatch.setattr(app_logger, "handlers", [])
    main.configure_app_logging()
    assert [h.get_name() for h in app_logger.handlers] == [main._APP_LOG_HANDLER_NAME]
    assert app_logger.handlers[0].level <= logging.INFO


@pytest.mark.asyncio
async def test_request_log_has_correlation_id_and_no_query_or_body(client: AsyncClient):
    collector = _Collector()
    logging.getLogger("app.main").addHandler(collector)
    try:
        response = await client.post(
            "/api/auth/login?token=secret-query-token",
            json={"email": "nobody@example.com", "password": "secret-password-1"},
            headers={"X-Correlation-ID": "log-test-1"},
        )
    finally:
        logging.getLogger("app.main").removeHandler(collector)

    assert response.status_code in {401, 422}
    entries = [
        json.loads(record.getMessage())
        for record in collector.records
        if record.levelno == logging.INFO and "http_request" in record.getMessage()
    ]
    assert entries and entries[-1]["correlation_id"] == "log-test-1"
    assert entries[-1]["path"] == "/api/auth/login"
    text = " ".join(record.getMessage() for record in collector.records)
    assert "secret-query-token" not in text
    assert "secret-password-1" not in text
    assert "nobody@example.com" not in text
