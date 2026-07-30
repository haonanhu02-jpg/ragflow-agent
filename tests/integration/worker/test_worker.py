"""Independent worker lifecycle tests."""

import asyncio
from datetime import UTC, datetime

import pytest

from ragflow_agent.config import WorkerSettings
from ragflow_agent.shared import AppError
from ragflow_agent.shared.ports import QueueMessage
from ragflow_agent.worker import IngestionWorker, WorkerState
from tests.fakes.foundation import FakeQueue


@pytest.mark.asyncio
async def test_worker_heartbeats_and_stops_gracefully() -> None:
    queue = FakeQueue()
    heartbeats: list[datetime] = []

    async def record_heartbeat(recorded_at: datetime) -> None:
        heartbeats.append(recorded_at)

    worker = IngestionWorker(
        queue=queue,
        settings=WorkerSettings(
            poll_interval_seconds=0.01,
            heartbeat_interval_seconds=0.01,
        ),
        heartbeat_sink=record_heartbeat,
    )
    run_task = asyncio.create_task(worker.run())
    await asyncio.wait_for(worker.wait_until_running(), timeout=1)
    await asyncio.sleep(0.03)

    assert worker.is_running
    assert worker.last_heartbeat_at is not None
    assert worker.last_heartbeat_at.tzinfo is UTC
    assert heartbeats

    worker.request_stop()
    await asyncio.wait_for(run_task, timeout=1)

    assert worker.state is WorkerState.STOPPED
    assert not queue.opened


@pytest.mark.asyncio
async def test_worker_closes_queue_when_cancelled() -> None:
    queue = FakeQueue()
    worker = IngestionWorker(
        queue=queue,
        settings=WorkerSettings(poll_interval_seconds=0.1),
    )
    run_task = asyncio.create_task(worker.run())
    await asyncio.wait_for(worker.wait_until_running(), timeout=1)

    run_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await run_task

    assert worker.state is WorkerState.STOPPED
    assert not queue.opened


@pytest.mark.asyncio
async def test_worker_does_not_process_phase_two_or_rag_tasks() -> None:
    message = QueueMessage(message_id="future-task", body=b"not-yet-supported")
    queue = FakeQueue([message])
    worker = IngestionWorker(
        queue=queue,
        settings=WorkerSettings(poll_interval_seconds=0.01),
    )

    with pytest.raises(ExceptionGroup) as raised:
        await worker.run()

    errors = list(raised.value.exceptions)
    assert len(errors) == 1
    assert isinstance(errors[0], AppError)
    assert errors[0].error_code == "ingestion_not_implemented"
    assert queue.acknowledged == []
    assert queue.rejected == []
    assert worker.state is WorkerState.STOPPED
