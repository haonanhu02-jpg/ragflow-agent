"""Explicitly unavailable model adapter."""

from ragflow_agent.infrastructure.errors import InfrastructureNotConfiguredError


class UnconfiguredModel:
    """Keep model-provider selection outside Phase 01."""

    async def open(self) -> None:
        raise InfrastructureNotConfiguredError("model")

    async def close(self) -> None:
        return None

    async def is_ready(self) -> bool:
        return False
