"""Transactional outbox delivery is idempotent and bounded."""

import pytest
from tests.fakes.knowledge import (
    FixedClock,
    MemoryIngestionQueue,
    MemoryKnowledgeStore,
    MemoryKnowledgeUnitOfWorkFactory,
    MemoryObjectStorage,
    SequenceIdGenerator,
)
from tests.fakes.lifecycle import NOW, context, seed_active_document

from ragflow_agent.knowledge.application.lifecycle.update import (
    DocumentUpdateService,
    UpdateDocumentCommand,
)
from ragflow_agent.knowledge.application.permission_service import DefaultPermissionChecker
from ragflow_agent.knowledge.domain.lifecycle import OutboxStatus
from ragflow_agent.knowledge.domain.retry import RetryPolicy
from ragflow_agent.worker.outbox import LifecycleOutboxDispatcher


@pytest.mark.asyncio
async def test_duplicate_dispatch_does_not_duplicate_queue_side_effect() -> None:
    store = MemoryKnowledgeStore()
    document, _version = seed_active_document(store)
    factory = MemoryKnowledgeUnitOfWorkFactory(store)
    await DocumentUpdateService(
        unit_of_work_factory=factory,
        storage=MemoryObjectStorage(),
        permission_checker=DefaultPermissionChecker(),
        id_generator=SequenceIdGenerator(["version-2", "operation-2"]),
        clock=FixedClock(NOW),
        max_upload_bytes=1024,
    ).update(
        UpdateDocumentCommand(
            context=context(),
            document_id=document.id,
            file_name="v2.md",
            media_type="text/markdown",
            content=b"new",
            idempotency_key="update-2",
            reason="new",
        )
    )
    queue = MemoryIngestionQueue()
    dispatcher = LifecycleOutboxDispatcher(
        unit_of_work_factory=factory,
        queue=queue,
        clock=FixedClock(NOW),
        retry_policy=RetryPolicy(max_attempts=2),
    )
    assert await dispatcher.dispatch_due(context()) == 1
    assert await dispatcher.dispatch_due(context()) == 0
    assert len(queue.envelopes) == 1
    event = next(iter(store.lifecycle_outbox.values()))
    assert event.status is OutboxStatus.PUBLISHED
