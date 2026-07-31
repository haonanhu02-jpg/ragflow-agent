"""Batch status is reconstructed from tenant-scoped child operations."""

import pytest
from tests.fakes.knowledge import (
    FixedClock,
    MemoryKnowledgeStore,
    MemoryKnowledgeUnitOfWorkFactory,
    SequenceIdGenerator,
)
from tests.fakes.lifecycle import NOW, context

from ragflow_agent.knowledge.application.lifecycle.batch import LifecycleBatchService
from ragflow_agent.knowledge.domain.errors import (
    KnowledgeAuthorizationError,
    KnowledgeConflictError,
)
from ragflow_agent.knowledge.domain.lifecycle import (
    FailureClass,
    LifecycleBatchStatus,
    LifecycleError,
    LifecycleOperation,
    LifecycleOperationKind,
    LifecycleOperationStatus,
)


def _operation(identifier: str, status: LifecycleOperationStatus) -> LifecycleOperation:
    error = (
        LifecycleError(
            classification=FailureClass.PERMANENT,
            code="invalid",
            message="invalid file",
            retryable=False,
        )
        if status in {LifecycleOperationStatus.FAILED, LifecycleOperationStatus.DEAD_LETTER}
        else None
    )
    return LifecycleOperation(
        id=identifier,
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        document_id=f"doc-{identifier}",
        version_id=f"version-{identifier}",
        kind=LifecycleOperationKind.REPARSE,
        idempotency_key=f"key-{identifier}",
        actor_id="owner-a",
        reason="batch",
        request_id="request-a",
        status=status,
        expected_document_revision=0,
        fencing_token=1,
        error=error,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.mark.asyncio
async def test_partial_batch_and_duplicate_request_are_deterministic() -> None:
    store = MemoryKnowledgeStore()
    store.lifecycle_operations["one"] = _operation("one", LifecycleOperationStatus.SUCCEEDED)
    store.lifecycle_operations["two"] = _operation("two", LifecycleOperationStatus.DEAD_LETTER)
    service = LifecycleBatchService(
        unit_of_work_factory=MemoryKnowledgeUnitOfWorkFactory(store),
        id_generator=SequenceIdGenerator(["batch-a"]),
        clock=FixedClock(NOW),
        max_concurrency=2,
    )
    batch = await service.create(
        context(),
        knowledge_base_id="kb-a",
        kind=LifecycleOperationKind.REPARSE,
        operation_ids=("one", "two"),
        idempotency_key="batch-key",
        concurrency=99,
    )
    duplicate = await service.create(
        context(),
        knowledge_base_id="kb-a",
        kind=LifecycleOperationKind.REPARSE,
        operation_ids=("one", "two"),
        idempotency_key="batch-key",
        concurrency=99,
    )
    refreshed = await service.refresh(context(), batch.id)
    assert duplicate.id == batch.id
    assert batch.concurrency == 2
    assert refreshed.status is LifecycleBatchStatus.PARTIAL_SUCCESS
    assert (refreshed.succeeded, refreshed.failed) == (1, 1)

    with pytest.raises(KnowledgeConflictError, match="different batch"):
        await service.create(
            context(),
            knowledge_base_id="kb-a",
            kind=LifecycleOperationKind.REPARSE,
            operation_ids=("one",),
            idempotency_key="batch-key",
        )
    with pytest.raises(KnowledgeAuthorizationError):
        await service.refresh(
            context().model_copy(update={"actor_id": "intruder"}),
            batch.id,
        )


@pytest.mark.asyncio
async def test_batch_rejects_cross_knowledge_base_child() -> None:
    store = MemoryKnowledgeStore()
    store.lifecycle_operations["one"] = _operation(
        "one", LifecycleOperationStatus.PENDING
    ).model_copy(update={"knowledge_base_id": "kb-b"})
    service = LifecycleBatchService(
        unit_of_work_factory=MemoryKnowledgeUnitOfWorkFactory(store),
        id_generator=SequenceIdGenerator(["batch-a"]),
        clock=FixedClock(NOW),
    )
    with pytest.raises(KnowledgeConflictError, match="scope"):
        await service.create(
            context(),
            knowledge_base_id="kb-a",
            kind=LifecycleOperationKind.REPARSE,
            operation_ids=("one",),
            idempotency_key="batch-key",
        )
