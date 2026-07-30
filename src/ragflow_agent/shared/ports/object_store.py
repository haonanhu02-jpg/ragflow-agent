"""Object-store lifecycle boundary; object semantics arrive in Phase 03."""

from typing import Protocol, runtime_checkable

from ragflow_agent.shared.ports.lifecycle import LifecyclePort


@runtime_checkable
class ObjectStorePort(LifecyclePort, Protocol):
    """Marker protocol preventing direct S3 client use in application code."""
