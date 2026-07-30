"""Queue boundary needed by the Phase 01 worker shell."""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ragflow_agent.shared.ports.lifecycle import LifecyclePort


@dataclass(frozen=True, slots=True)
class QueueMessage:
    """Opaque transport message; ingestion payload semantics are deferred."""

    message_id: str
    body: bytes
    attributes: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class QueuePort(LifecyclePort, Protocol):
    """Minimal polling and settlement surface.

    Delivery guarantees, retry policy, and dead-letter behavior remain
    undecided and must not be inferred from this foundation contract.
    """

    async def receive(self, *, wait_seconds: float) -> QueueMessage | None: ...

    async def acknowledge(self, message: QueueMessage) -> None: ...

    async def reject(self, message: QueueMessage, *, requeue: bool) -> None: ...
