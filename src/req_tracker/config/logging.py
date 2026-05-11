"""Logging setup."""

import json
import logging
from typing import Any

STRUCTURED_FIELDS = (
    "correlation_id",
    "trace_id",
    "span_id",
    "run_id",
    "step_id",
    "user_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
)


class JsonLogFormatter(logging.Formatter):
    """Format logs as compact JSON for ingestion by server log collectors."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in STRUCTURED_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def configure_logging(level: str = "INFO") -> None:
    """Configure process logging with a structured JSON formatter."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    if root.handlers:
        for handler in root.handlers:
            handler.setFormatter(JsonLogFormatter())
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root.addHandler(handler)
