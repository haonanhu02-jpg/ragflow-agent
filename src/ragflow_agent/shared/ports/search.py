"""Search lifecycle boundary; retrieval semantics arrive in Phase 03."""

from typing import Protocol, runtime_checkable

from ragflow_agent.shared.ports.lifecycle import LifecyclePort


@runtime_checkable
class SearchPort(LifecyclePort, Protocol):
    """Marker protocol preventing direct search client use in application code."""
