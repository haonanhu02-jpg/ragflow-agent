"""Explicitly unavailable object-store adapter."""

from ragflow_agent.infrastructure.errors import InfrastructureNotConfiguredError


class UnconfiguredObjectStore:
    """Fail rather than report a missing object store as usable."""

    async def open(self) -> None:
        raise InfrastructureNotConfiguredError("object_store")

    async def close(self) -> None:
        return None

    async def is_ready(self) -> bool:
        return False
