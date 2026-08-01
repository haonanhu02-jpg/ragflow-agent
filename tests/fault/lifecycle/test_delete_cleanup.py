"""Deletion stays fail-closed while cleanup is delayed or repeated."""

from collections.abc import AsyncIterator
from datetime import datetime, timedelta

import pytest
from tests.fakes.knowledge import (
    MemoryIngestionQueue,
    MemoryKnowledgeStore,
    MemoryKnowledgeUnitOfWorkFactory,
    MemoryObjectStorage,
    MemorySearchIndex,
    SequenceIdGenerator,
)
from tests.fakes.lifecycle import NOW, context, seed_active_document, seed_index

from ragflow_agent.knowledge.application.lifecycle.delete import DocumentDeletionService
from ragflow_agent.knowledge.application.permission_service import DefaultPermissionChecker
from ragflow_agent.knowledge.domain.document import DocumentStatus, DocumentVersionStatus
from ragflow_agent.knowledge.domain.lifecycle import OutboxStatus
from ragflow_agent.knowledge.domain.retry import RetryPolicy
from ragflow_agent.knowledge.ports.storage import StorageWriteRequest
from ragflow_agent.worker.outbox import LifecycleOutboxDispatcher


async def _bytes() -> AsyncIterator[bytes]:
    yield b"old-data"


class MutableClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


@pytest.mark.asyncio
async def test_soft_delete_is_immediate_and_physical_purge_is_idempotent() -> None:
    store = MemoryKnowledgeStore()
    document, version = seed_active_document(store)
    search = MemorySearchIndex()
    seed_index(search, version)
    storage = MemoryObjectStorage()
    stored = await storage.put(
        context(),
        StorageWriteRequest(
            tenant_id="tenant-a",
            object_key=version.object_key,
            media_type=version.media_type,
            size_bytes=8,
            checksum_sha256="edf084079261853e2a577d006d247d4a40e1d1549c52dd11ead17fdc258227e6",
            trace_id="request-a",
        ),
        _bytes(),
    )
    clock = MutableClock(NOW)
    service = DocumentDeletionService(
        unit_of_work_factory=MemoryKnowledgeUnitOfWorkFactory(store),
        search=search,
        storage=storage,
        permission_checker=DefaultPermissionChecker(),
        id_generator=SequenceIdGenerator(["delete-op", "restore-op", "delete-op-2", "purge-op"]),
        clock=clock,
        retention_days=30,
    )
    deletion = await service.request_delete(
        context(), document_id=document.id, idempotency_key="delete-1", reason="obsolete"
    )
    duplicate = await service.request_delete(
        context(), document_id=document.id, idempotency_key="delete-1", reason="obsolete"
    )
    assert duplicate.id == deletion.id
    assert store.documents[document.id].status is DocumentStatus.DELETE_PENDING
    assert store.documents[document.id].current_version_id is None
    assert await storage.exists(context(), stored)

    restored = await service.restore(
        context(),
        document_id=document.id,
        idempotency_key="restore-1",
        reason="operator recovery",
    )
    assert restored.status.value == "succeeded"
    assert store.documents[document.id].status is DocumentStatus.ACTIVE
    assert store.documents[document.id].current_version_id == version.id
    assert store.lifecycle_outbox[f"outbox:{deletion.id}"].status is OutboxStatus.CANCELLED

    deletion = await service.request_delete(
        context(), document_id=document.id, idempotency_key="delete-2", reason="obsolete"
    )
    clock.value = NOW + timedelta(days=31)

    dispatcher = LifecycleOutboxDispatcher(
        unit_of_work_factory=MemoryKnowledgeUnitOfWorkFactory(store),
        queue=MemoryIngestionQueue(),
        clock=clock,
        retry_policy=RetryPolicy(max_attempts=2),
        document_purger=service,
    )
    assert await dispatcher.dispatch_due(context()) == 1
    purged = next(
        operation
        for operation in store.lifecycle_operations.values()
        if operation.kind.value == "purge"
    )
    repeated = await service.purge(context(), document_id=document.id, reason="repeat")
    assert repeated.id == purged.id
    assert store.documents[document.id].status is DocumentStatus.DELETED
    assert store.document_versions[version.id].status is DocumentVersionStatus.DELETED
    assert not await storage.exists(context(), stored)
    cleanup = store.lifecycle_outbox[f"outbox:{deletion.id}"]
    assert cleanup.status is OutboxStatus.PUBLISHED
