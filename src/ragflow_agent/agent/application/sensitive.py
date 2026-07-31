"""Content-minimization helpers for checkpoint, Tool, memory, and trace boundaries."""

from __future__ import annotations

import re

from ragflow_agent.agent.domain.errors import AgentToolError

_SECRET_VALUE = re.compile(
    r"(?i)\b(password|passwd|api[_ -]?key|access[_ -]?token|authorization|private[_ -]?key)"
    r"\s*[:=]\s*([^\s,;]+)"
)
_SECRET_KEYS = frozenset(
    {"password", "passwd", "api_key", "apikey", "access_token", "authorization", "private_key"}
)


def redact_secret_like_text(value: str) -> str:
    return _SECRET_VALUE.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


def reject_secret_arguments(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).strip().lower() in _SECRET_KEYS:
                raise AgentToolError(
                    "credentials cannot be supplied through Tool arguments",
                    error_code="tool_secret_argument",
                    status_code=403,
                )
            reject_secret_arguments(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            reject_secret_arguments(child)
    elif isinstance(value, str) and redact_secret_like_text(value) != value:
        raise AgentToolError(
            "credentials cannot be supplied through Tool arguments",
            error_code="tool_secret_argument",
            status_code=403,
        )
