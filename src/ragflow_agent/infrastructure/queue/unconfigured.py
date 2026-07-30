"""Explicitly unavailable queue adapter."""

from ragflow_agent.infrastructure.errors import InfrastructureNotConfiguredError
from ragflow_agent.shared.ports.queue import QueueMessage


class UnconfiguredQueue:
    """Fail-fast queue used until bootstrap receives a concrete adapter."""

    async def open(self) -> None:
        raise InfrastructureNotConfiguredError("queue")

    async def close(self) -> None:
        return None

    async def is_ready(self) -> bool:
        return False

    async def receive(self, *, wait_seconds: float) -> QueueMessage | None:
        del wait_seconds
        raise InfrastructureNotConfiguredError("queue")

    async def acknowledge(self, message: QueueMessage) -> None:
        del message
        raise InfrastructureNotConfiguredError("queue")

    async def reject(self, message: QueueMessage, *, requeue: bool) -> None:
        del message, requeue
        raise InfrastructureNotConfiguredError("queue")
