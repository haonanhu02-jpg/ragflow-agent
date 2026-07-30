"""Tests for stable application errors."""

import pytest

from ragflow_agent.shared import AppError


def test_error_payload_and_trace_binding() -> None:
    error = AppError(
        "invalid input",
        error_code="invalid_input",
        status_code=422,
        details={"field": "name"},
    )

    error.with_trace_id("trace-123")

    assert error.to_dict() == {
        "error_code": "invalid_input",
        "message": "invalid input",
        "trace_id": "trace-123",
        "details": {"field": "name"},
    }


def test_existing_trace_id_is_not_replaced() -> None:
    error = AppError("failed", trace_id="first")

    error.with_trace_id("second")

    assert error.trace_id == "first"


@pytest.mark.parametrize("status_code", [399, 600])
def test_invalid_error_status_is_rejected(status_code: int) -> None:
    with pytest.raises(ValueError, match="HTTP error"):
        AppError("failed", status_code=status_code)
