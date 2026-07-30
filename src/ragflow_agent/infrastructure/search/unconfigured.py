"""Explicitly unavailable search adapter."""

from ragflow_agent.infrastructure.errors import InfrastructureNotConfiguredError


class UnconfiguredSearch:
    """Keep the search backend decision visibly unresolved."""

    async def open(self) -> None:
        raise InfrastructureNotConfiguredError("search")

    async def close(self) -> None:
        return None

    async def is_ready(self) -> bool:
        return False
