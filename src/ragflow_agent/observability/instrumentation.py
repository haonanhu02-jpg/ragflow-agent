"""Bounded component instrumentation shared by API and Worker operations."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter
from typing import Literal

from opentelemetry.trace import Tracer

from ragflow_agent.observability.metrics import OPERATION_DURATION, OPERATION_TOTAL

type ObservableComponent = Literal[
    "api",
    "job",
    "parser",
    "embedding",
    "search",
    "llm",
    "agent",
    "tool",
    "checkpoint",
    "advanced_build",
]


@contextmanager
def observe_operation(
    component: ObservableComponent,
    *,
    tracer: Tracer | None = None,
) -> Iterator[None]:
    """Measure a safe low-cardinality component operation and optional OTel span."""
    started = perf_counter()
    outcome = "succeeded"
    span = tracer.start_as_current_span(component) if tracer is not None else None
    if span is not None:
        span.__enter__()
    try:
        yield
    except Exception:
        outcome = "failed"
        if span is not None:
            span.__exit__(*__import__("sys").exc_info())
            span = None
        raise
    finally:
        if span is not None:
            span.__exit__(None, None, None)
        elapsed = perf_counter() - started
        OPERATION_TOTAL.labels(component, outcome).inc()
        OPERATION_DURATION.labels(component, outcome).observe(elapsed)
