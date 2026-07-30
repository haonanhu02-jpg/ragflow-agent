"""Deterministic adapters used only by foundation tests."""

from collections import deque

from ragflow_agent.shared.ports.queue import QueueMessage


class FakeQueue:
    """Controllable in-memory queue without claimed delivery guarantees."""

    def __init__(self, messages: list[QueueMessage] | None = None) -> None:
        self._messages = deque(messages or [])
        self.opened = False
        self.acknowledged: list[str] = []
        self.rejected: list[tuple[str, bool]] = []

    async def open(self) -> None:
        self.opened = True

    async def close(self) -> None:
        self.opened = False

    async def is_ready(self) -> bool:
        return self.opened

    async def receive(self, *, wait_seconds: float) -> QueueMessage | None:
        del wait_seconds
        return self._messages.popleft() if self._messages else None

    async def acknowledge(self, message: QueueMessage) -> None:
        self.acknowledged.append(message.message_id)

    async def reject(self, message: QueueMessage, *, requeue: bool) -> None:
        self.rejected.append((message.message_id, requeue))
        if requeue:
            self._messages.appendleft(message)
