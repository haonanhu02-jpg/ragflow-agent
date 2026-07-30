"""Structured JSON logging with correlation fields and sensitive-data redaction."""

import json
import logging
import re
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TextIO

from ragflow_agent.observability.context import current_trace_context
from ragflow_agent.shared.errors import AppError

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "database_url",
        "password",
        "secret",
        "secret_key",
        "token",
    }
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|authorization|password|secret(?:_key)?|token)\b"
    r"(\s*[=:]\s*)([^\s,;]+)"
)
_URL_CREDENTIALS = re.compile(r"(://)[^:@/\s]+:[^@/\s]+@")
_STANDARD_LOG_RECORD_KEYS = frozenset(logging.makeLogRecord({}).__dict__)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return normalized in _SENSITIVE_KEYS or normalized.endswith(("_password", "_secret", "_token"))


def _redact_message(message: str) -> str:
    redacted = _SECRET_ASSIGNMENT.sub(r"\1\2<redacted>", message)
    return _URL_CREDENTIALS.sub(r"\1<redacted>@", redacted)


def _redact(value: object, *, key: str | None = None) -> object:
    if key is not None and _is_sensitive_key(key):
        return "<redacted>"
    if isinstance(value, Mapping):
        return {str(item_key): _redact(item, key=str(item_key)) for item_key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return _redact_message(value)
    return value


class RedactingJsonFormatter(logging.Formatter):
    """Emit one JSON object per record."""

    def __init__(self, *, service_name: str) -> None:
        super().__init__()
        self._service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        context = current_trace_context()
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": self._service_name,
            "component": record.name,
            "message": _redact_message(record.getMessage()),
        }
        if context is not None:
            for field_name in ("trace_id", "tenant_id", "request_id", "job_id", "run_id"):
                field_value = getattr(context, field_name)
                if field_value is not None:
                    payload[field_name] = field_value

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_LOG_RECORD_KEYS and not key.startswith("_")
        }
        if extras:
            payload["data"] = _redact(extras)

        if isinstance(record.exc_info, tuple) and isinstance(record.exc_info[1], AppError):
            payload["error_code"] = record.exc_info[1].error_code

        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


def configure_logging(
    *,
    service_name: str,
    level: str = "INFO",
    stream: TextIO | None = None,
) -> logging.Logger:
    """Configure and return the project logger without mutating the root logger."""
    logger = logging.getLogger("ragflow_agent")
    logger.handlers.clear()
    logger.setLevel(level)
    logger.propagate = False

    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(RedactingJsonFormatter(service_name=service_name))
    logger.addHandler(handler)
    return logger


def get_logger(component: str) -> logging.Logger:
    """Return a child logger under the project namespace."""
    return logging.getLogger(f"ragflow_agent.{component}")
