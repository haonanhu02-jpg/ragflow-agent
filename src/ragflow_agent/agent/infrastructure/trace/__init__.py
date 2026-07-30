"""Trace sink implementations."""

from ragflow_agent.agent.infrastructure.trace.memory import (
    FailingTraceSink,
    InMemoryTraceSink,
)

__all__ = ["FailingTraceSink", "InMemoryTraceSink"]
