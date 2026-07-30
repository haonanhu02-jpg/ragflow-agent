"""Context-local trace correlation shared by API, worker, and later Agent flows."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from uuid import uuid4

_TRACE_CONTEXT: ContextVar[TraceContext | None] = ContextVar("trace_context", default=None)


def new_correlation_id() -> str:
    """Return a random, opaque correlation identifier."""
    return uuid4().hex


@dataclass(frozen=True, slots=True)
class TraceContext:
    """Minimal correlation context safe to propagate across application layers."""

    trace_id: str
    service: str
    tenant_id: str | None = None
    request_id: str | None = None
    job_id: str | None = None
    run_id: str | None = None

    def __post_init__(self) -> None:
        if not self.trace_id:
            raise ValueError("trace_id must not be empty")
        if not self.service:
            raise ValueError("service must not be empty")

    @classmethod
    def create(
        cls,
        *,
        service: str,
        trace_id: str | None = None,
        tenant_id: str | None = None,
        request_id: str | None = None,
        job_id: str | None = None,
        run_id: str | None = None,
    ) -> TraceContext:
        """Create a context while generating any missing trace ID."""
        return cls(
            trace_id=trace_id or new_correlation_id(),
            service=service,
            tenant_id=tenant_id,
            request_id=request_id,
            job_id=job_id,
            run_id=run_id,
        )


def current_trace_context() -> TraceContext | None:
    """Return the context bound to the current execution context."""
    return _TRACE_CONTEXT.get()


@contextmanager
def use_trace_context(context: TraceContext) -> Iterator[TraceContext]:
    """Bind and reliably restore a trace context."""
    reset_handle = _TRACE_CONTEXT.set(context)
    try:
        yield context
    finally:
        _TRACE_CONTEXT.reset(reset_handle)
