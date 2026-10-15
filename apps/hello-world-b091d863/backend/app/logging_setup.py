"""Structured JSON logging with redaction and a per-request ID."""

from __future__ import annotations

import json
import logging
import re
import sys
import uuid
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

REDACT_KEYS = {
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "authorization", "cookie", "set-cookie", "x-csrf-token",
    "client_secret", "role_id", "secret_id", "session",
    "ssn", "card", "card_number", "pan",
}

# Patterns for values that look like PII/credentials
_PATTERNS = [
    (re.compile(r"\b\d{13,19}\b"), "[REDACTED-CARD]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED-SSN]"),
    (re.compile(r"Bearer\s+[A-Za-z0-9\._\-]+", re.IGNORECASE), "Bearer [REDACTED]"),
]


def _redact_value(v: object) -> object:
    if isinstance(v, str):
        s = v
        for pat, repl in _PATTERNS:
            s = pat.sub(repl, s)
        return s
    if isinstance(v, dict):
        return {k: ("[REDACTED]" if k.lower() in REDACT_KEYS else _redact_value(val)) for k, val in v.items()}
    if isinstance(v, list):
        return [_redact_value(x) for x in v]
    return v


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": _redact_value(record.getMessage()),
            "request_id": request_id_var.get(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        extras = getattr(record, "extra_fields", None)
        if isinstance(extras, dict):
            payload.update(_redact_value(extras))  # type: ignore[arg-type]
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    # Quiet overly chatty access logs; our middleware emits one line per request.
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = False


def new_request_id() -> str:
    return uuid.uuid4().hex
