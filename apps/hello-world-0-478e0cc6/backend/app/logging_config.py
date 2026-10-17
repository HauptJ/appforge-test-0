"""Structured JSON logging with request IDs and credential redaction."""
from __future__ import annotations

import json
import logging
import re
import sys
from contextvars import ContextVar
from typing import Any

# Request ID is set by middleware per request and read by the log formatter.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# Keys whose values must never be logged.
_REDACT_KEYS = {
    "authorization",
    "cookie",
    "set-cookie",
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "x-vault-token",
}

# Patterns for sensitive values that might appear inside log messages.
_PATTERNS = [
    (re.compile(r"(?i)(authorization\s*[:=]\s*)([^\s,;]+)"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(password\s*[:=]\s*)([^\s,;]+)"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(token\s*[:=]\s*)([^\s,;]+)"), r"\1[REDACTED]"),
    # 13-19 digit sequences (card-number shaped).
    (re.compile(r"\b\d{13,19}\b"), "[REDACTED-NUM]"),
    # US SSN shaped.
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED-SSN]"),
]


def _redact_text(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _redact_mapping(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: ("[REDACTED]" if k.lower() in _REDACT_KEYS else _redact_mapping(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact_mapping(v) for v in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


class JsonFormatter(logging.Formatter):
    """Minimal JSON formatter; no third-party dependency."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": _redact_text(record.getMessage()),
            "request_id": request_id_var.get(),
        }
        # Attach structured extras set via `logger.info("...", extra={"extra": {...}})`.
        extra = getattr(record, "extra", None)
        if isinstance(extra, dict):
            payload["extra"] = _redact_mapping(extra)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Install the JSON formatter on the root logger."""
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)
    # Quiet uvicorn's default access logger (we log our own request lines).
    logging.getLogger("uvicorn.access").handlers = [handler]
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("uvicorn.error").handlers = [handler]
    logging.getLogger("uvicorn.error").propagate = False
