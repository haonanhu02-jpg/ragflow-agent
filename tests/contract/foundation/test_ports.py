"""Contract tests for Phase 01 infrastructure boundaries."""

from datetime import UTC

import pytest

from ragflow_agent.infrastructure.errors import InfrastructureNotConfiguredError
from ragflow_agent.infrastructure.models import UnconfiguredModel
from ragflow_agent.infrastructure.object_store import UnconfiguredObjectStore
from ragflow_agent.infrastructure.queue import DevelopmentIdleQueue, UnconfiguredQueue
from ragflow_agent.infrastructure.search import UnconfiguredSearch
from ragflow_agent.shared import AppError
from ragflow_agent.shared.ports import (
    Clock,
    IdGenerator,
    LifecyclePort,
    ModelPort,
    ObjectStorePort,
    QueueMessage,
    QueuePort,
    SearchPort,
    SystemClock,
    Uuid4Generator,
)
from tests.fakes.foundation import FakeQueue


@pytest.mark.asyncio
async def test_fake_queue_obeys_lifecycle_and_settlement_contract() -> None:
    message = QueueMessage(message_id="message-1", body=b"opaque")
    queue = FakeQueue([message])

    assert isinstance(queue, QueuePort)
    assert not await queue.is_ready()
    await queue.open()
    assert await queue.is_ready()
    assert await queue.receive(wait_seconds=0) == message
    await queue.acknowledge(message)
    await queue.reject(message, requeue=True)
    assert queue.acknowledged == ["message-1"]
    assert queue.rejected == [("message-1", True)]
    assert await queue.receive(wait_seconds=0) == message
    await queue.close()
    assert not await queue.is_ready()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("adapter", "protocol"),
    [
        (UnconfiguredQueue(), QueuePort),
        (UnconfiguredObjectStore(), ObjectStorePort),
        (UnconfiguredSearch(), SearchPort),
        (UnconfiguredModel(), ModelPort),
    ],
)
async def test_unconfigured_adapters_never_report_false_success(
    adapter: LifecyclePort,
    protocol: type[LifecyclePort],
) -> None:
    assert isinstance(adapter, protocol)
    assert not await adapter.is_ready()
    with pytest.raises(InfrastructureNotConfiguredError):
        await adapter.open()
    await adapter.close()


def test_clock_and_identifier_are_provider_neutral() -> None:
    clock: Clock = SystemClock()
    generator: IdGenerator = Uuid4Generator()

    assert clock.now().tzinfo is UTC
    assert generator.new_id() != generator.new_id()


@pytest.mark.asyncio
async def test_development_idle_queue_cannot_claim_task_settlement() -> None:
    queue = DevelopmentIdleQueue()
    message = QueueMessage(message_id="unsupported", body=b"unsupported")
    await queue.open()

    assert await queue.is_ready()
    assert await queue.receive(wait_seconds=0) is None
    with pytest.raises(InfrastructureNotConfiguredError):
        await UnconfiguredQueue().open()
    with pytest.raises(AppError) as acknowledge_error:
        await queue.acknowledge(message)
    assert getattr(acknowledge_error.value, "error_code", None) == "ingestion_not_implemented"

    await queue.close()
    assert not await queue.is_ready()
