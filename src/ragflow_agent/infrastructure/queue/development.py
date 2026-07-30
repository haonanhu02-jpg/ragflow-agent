"""Explicitly disabled task source for the Phase 01 development container."""

import asyncio

from ragflow_agent.shared import AppError
from ragflow_agent.shared.ports import QueueMessage


class DevelopmentIdleQueue:
    """Keep the Worker process alive without claiming task support.

    This adapter is accepted only by the explicit ``--development-idle`` CLI
    mode. It never produces, acknowledges, or rejects a task.
    """

    def __init__(self) -> None:
        self._opened = False

    async def open(self) -> None:
        self._opened = True

    async def close(self) -> None:
        self._opened = False

    async def is_ready(self) -> bool:
        return self._opened

    async def receive(self, *, wait_seconds: float) -> QueueMessage | None:
        if not self._opened:
            raise RuntimeError("development idle queue is closed")
        await asyncio.sleep(wait_seconds)
        return None

    async def acknowledge(self, message: QueueMessage) -> None:
        del message
        raise AppError(
            "development idle queue cannot acknowledge tasks",
            error_code="ingestion_not_implemented",
            status_code=503,
        )

    async def reject(self, message: QueueMessage, *, requeue: bool) -> None:
        del message, requeue
        raise AppError(
            "development idle queue cannot reject tasks",
            error_code="ingestion_not_implemented",
            status_code=503,
        )
