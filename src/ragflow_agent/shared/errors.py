"""Stable application errors independent of transport frameworks."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

DEFAULT_ERROR_CODE: Final = "internal_error"


class AppError(Exception):
    """Base error with a stable code and optional trace correlation."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = DEFAULT_ERROR_CODE,
        status_code: int = 500,
        trace_id: str | None = None,
        details: Mapping[str, object] | None = None,
    ) -> None:
        if not error_code:
            raise ValueError("error_code must not be empty")
        if not 400 <= status_code <= 599:
            raise ValueError("status_code must be an HTTP error status")
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.trace_id = trace_id
        self.details = dict(details or {})

    def with_trace_id(self, trace_id: str) -> AppError:
        """Attach a trace ID without replacing an existing correlation ID."""
        if not self.trace_id:
            self.trace_id = trace_id
        return self

    def to_dict(self) -> dict[str, object]:
        """Return a transport-neutral error payload."""
        payload: dict[str, object] = {
            "error_code": self.error_code,
            "message": self.message,
        }
        if self.trace_id is not None:
            payload["trace_id"] = self.trace_id
        if self.details:
            payload["details"] = self.details
        return payload
