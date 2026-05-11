"""Structured logging tests."""

import json
import logging

from req_tracker.config.logging import JsonLogFormatter


def test_json_log_formatter_includes_correlation_and_user_fields() -> None:
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="req_tracker.api.request",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="http_request",
        args=(),
        exc_info=None,
    )
    record.correlation_id = "corr_test"
    record.user_id = "user@example.com"
    record.method = "GET"
    record.path = "/api/v1/health"
    record.status_code = 200
    record.duration_ms = 1.25

    payload = json.loads(formatter.format(record))

    assert payload["message"] == "http_request"
    assert payload["correlation_id"] == "corr_test"
    assert payload["user_id"] == "user@example.com"
    assert payload["method"] == "GET"
    assert payload["path"] == "/api/v1/health"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 1.25
