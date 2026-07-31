"""Update/reparse registration keeps the old active version available."""

import pytest
from tests.fakes.knowledge import (
    FixedClock,
    MemoryKnowledgeStore,
    MemoryKnowledgeUnitOfWorkFactory,
    MemoryObjectStorage,
    SequenceIdGenerator,
)
from tests.fakes.lifecycle import NOW, context, seed_active_document

from ragflow_agent.knowledge.application.lifecycle.update import (
    DocumentUpdateService,
    ReparseDocumentCommand,
    UpdateDocumentCommand,
)
from ragflow_agent.knowledge.application.permission_service import DefaultPermissionChecker
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.domain.lifecycle import LifecycleOperationKind


@pytest.mark.asyncio
async def test_update_and_reparse_create_immutable_candidate_versions() -> None:
    store = MemoryKnowledgeStore()
    document, old_version = seed_active_document(store)
    service = DocumentUpdateService(
        unit_of_work_factory=MemoryKnowledgeUnitOfWorkFactory(store),
        storage=MemoryObjectStorage(),
        permission_checker=DefaultPermissionChecker(),
        id_generator=SequenceIdGenerator(["version-2", "operation-2", "version-3", "operation-3"]),
        clock=FixedClock(NOW),
        max_upload_bytes=1024,
    )
    updated = await service.update(
        UpdateDocumentCommand(
            context=context(),
            document_id=document.id,
            file_name="manual-v2.md",
            media_type="text/markdown",
            content=b"new manual",
            idempotency_key="update-2",
            reason="source changed",
        )
    )
    duplicate = await service.update(
        UpdateDocumentCommand(
            context=context(),
            document_id=document.id,
            file_name="manual-v2.md",
            media_type="text/markdown",
            content=b"new manual",
            idempotency_key="update-2",
            reason="source changed",
        )
    )
    reparsed = await service.reparse(
        ReparseDocumentCommand(
            context=context(),
            document_id=document.id,
            idempotency_key="reparse-3",
            reason="parser upgraded",
        )
    )
    assert store.documents[document.id].current_version_id == old_version.id
    assert updated.operation.kind is LifecycleOperationKind.UPDATE
    assert reparsed.operation.kind is LifecycleOperationKind.REPARSE
    assert reparsed.operation.version_id != old_version.id
    assert (
        store.document_versions[reparsed.operation.version_id].object_key == old_version.object_key
    )
    assert duplicate.duplicate
    assert len(store.lifecycle_operations) == 2
    assert len(store.lifecycle_outbox) == 2


@pytest.mark.asyncio
async def test_idempotency_key_rejects_a_different_update_without_writing_an_object() -> None:
    store = MemoryKnowledgeStore()
    document, _old_version = seed_active_document(store)
    storage = MemoryObjectStorage()
    service = DocumentUpdateService(
        unit_of_work_factory=MemoryKnowledgeUnitOfWorkFactory(store),
        storage=storage,
        permission_checker=DefaultPermissionChecker(),
        id_generator=SequenceIdGenerator(["version-2", "operation-2"]),
        clock=FixedClock(NOW),
        max_upload_bytes=1024,
    )
    original = UpdateDocumentCommand(
        context=context(),
        document_id=document.id,
        file_name="manual-v2.md",
        media_type="text/markdown",
        content=b"new manual",
        idempotency_key="update-2",
        reason="source changed",
    )
    await service.update(original)

    with pytest.raises(KnowledgeConflictError, match="idempotency key"):
        await service.update(original.model_copy(update={"content": b"different content"}))

    assert len(storage.objects) == 1
