"""Model lifecycle boundary; invocation protocols arrive in Phase 02."""

from typing import Protocol, runtime_checkable

from ragflow_agent.shared.ports.lifecycle import LifecyclePort


@runtime_checkable
class ModelPort(LifecyclePort, Protocol):
    """Marker protocol preventing direct model SDK use in application code."""
