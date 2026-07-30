"""Tests for trace-context lifecycle."""

from ragflow_agent.observability import (
    TraceContext,
    current_trace_context,
    new_correlation_id,
    use_trace_context,
)


def test_generated_ids_are_opaque_and_unique() -> None:
    first = new_correlation_id()
    second = new_correlation_id()

    assert len(first) == 32
    assert first != second


def test_context_is_bound_and_restored() -> None:
    context = TraceContext.create(
        service="ragflow-agent-api",
        trace_id="trace-1",
        request_id="request-1",
    )

    assert current_trace_context() is None
    with use_trace_context(context):
        assert current_trace_context() == context
    assert current_trace_context() is None
