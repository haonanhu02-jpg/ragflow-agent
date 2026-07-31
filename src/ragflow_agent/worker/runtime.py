"""Lifecycle-only ingestion worker.

No ingestion task, parser, embedding, or indexing behavior belongs in Phase 01.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import datetime
from enum import StrEnum

from ragflow_agent.config import WorkerSettings
from ragflow_agent.shared import AppError
from ragflow_agent.shared.ports import Clock, QueuePort, SystemClock

type HeartbeatSink = Callable[[datetime], Awaitable[None]]


class WorkerState(StrEnum):
    """Observable worker lifecycle states."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"


async def _discard_heartbeat(recorded_at: datetime) -> None:
    del recorded_at


class IngestionWorker:
    """Queue-connected process shell with cancellation-safe shutdown."""

    def __init__(
        self,
        *,
        queue: QueuePort,
        settings: WorkerSettings,
        clock: Clock | None = None,
        heartbeat_sink: HeartbeatSink = _discard_heartbeat,
    ) -> None:
        self.queue = queue
        self._settings = settings
        self._clock = clock or SystemClock()
        self._heartbeat_sink = heartbeat_sink
        self._stop_requested = asyncio.Event()
        self._running = asyncio.Event()
        self.state = WorkerState.STOPPED
        self.last_heartbeat_at: datetime | None = None

    @property
    def is_running(self) -> bool:
        return self.state is WorkerState.RUNNING

    async def wait_until_running(self) -> None:
        await self._running.wait()

    def request_stop(self) -> None:
        """Stop new polling and let active lifecycle work exit safely."""
        self._stop_requested.set()

    async def run(self) -> None:
        """Open the queue, run empty polling and heartbeat loops, then close."""
        if self.state is not WorkerState.STOPPED:
            raise RuntimeError("worker can only run from the stopped state")

        self._stop_requested.clear()
        self._running.clear()
        self.state = WorkerState.STARTING
        opened = False
        try:
            await self.queue.open()
            opened = True
            self.state = WorkerState.RUNNING
            self._running.set()
            async with asyncio.TaskGroup() as tasks:
                tasks.create_task(self._poll_until_stopped())
                tasks.create_task(self._heartbeat_until_stopped())
        finally:
            self.state = WorkerState.STOPPING
            if opened:
                await self.queue.close()
            self._running.clear()
            self.state = WorkerState.STOPPED

    async def _poll_until_stopped(self) -> None:
        while not self._stop_requested.is_set():
            message = await self.queue.receive(wait_seconds=self._settings.poll_interval_seconds)
            if message is not None:
                raise AppError(
                    "Phase 01 worker received an unsupported task",
                    error_code="ingestion_not_implemented",
                    status_code=503,
                    details={"message_id": message.message_id},
                )
            await self._wait_for_stop(self._settings.poll_interval_seconds)

    async def _heartbeat_until_stopped(self) -> None:
        while not self._stop_requested.is_set():
            recorded_at = self._clock.now()
            self.last_heartbeat_at = recorded_at
            await self._heartbeat_sink(recorded_at)
            await self._wait_for_stop(self._settings.heartbeat_interval_seconds)

    async def _wait_for_stop(self, timeout_seconds: float) -> None:
        with suppress(TimeoutError):
            await asyncio.wait_for(self._stop_requested.wait(), timeout=timeout_seconds)
