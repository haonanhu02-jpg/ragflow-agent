"""Tests for structured logs and redaction."""

import io
import json
import logging

from ragflow_agent.observability import (
    TraceContext,
    configure_logging,
    get_logger,
    use_trace_context,
)


def test_json_log_contains_correlation_fields() -> None:
    stream = io.StringIO()
    configure_logging(service_name="ragflow-agent-api", stream=stream)
    logger = get_logger("test")
    context = TraceContext.create(
        service="ragflow-agent-api",
        trace_id="trace-1",
        tenant_id="tenant-1",
        request_id="request-1",
    )

    with use_trace_context(context):
        logger.info("ready", extra={"operation": "health", "outcome": "ok"})

    payload = json.loads(stream.getvalue())
    assert payload["service"] == "ragflow-agent-api"
    assert payload["trace_id"] == "trace-1"
    assert payload["tenant_id"] == "tenant-1"
    assert payload["request_id"] == "request-1"
    assert payload["data"] == {"operation": "health", "outcome": "ok"}


def test_sensitive_values_are_redacted_from_message_and_data() -> None:
    stream = io.StringIO()
    configure_logging(service_name="ragflow-agent-api", stream=stream)
    logger = get_logger("security")

    logger.warning(
        "password=plain-text postgresql://user:db-secret@localhost/app",
        extra={
            "api_key": "provider-secret",
            "nested": {"authorization": "Bearer token-value"},
        },
    )

    rendered = stream.getvalue()
    assert "plain-text" not in rendered
    assert "db-secret" not in rendered
    assert "provider-secret" not in rendered
    assert "token-value" not in rendered
    assert rendered.count("<redacted>") >= 3


def test_project_logger_does_not_propagate_to_root() -> None:
    logger = configure_logging(service_name="ragflow-agent-api")

    assert logger.propagate is False
    assert logger.level == logging.INFO
