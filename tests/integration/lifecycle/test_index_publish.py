"""Version publication is CAS-protected and rollback remains auditable."""

import pytest
from tests.fakes.knowledge import (
    FixedClock,
    MemoryKnowledgeStore,
    MemoryKnowledgeUnitOfWorkFactory,
    MemoryObjectStorage,
    MemorySearchIndex,
    SequenceIdGenerator,
)
from tests.fakes.lifecycle import NOW, context, seed_active_document, seed_index

from ragflow_agent.knowledge.application.lifecycle.publish import DocumentVersionPublisher
from ragflow_agent.knowledge.application.lifecycle.rebuild import IndexRebuildService
from ragflow_agent.knowledge.application.lifecycle.update import (
    DocumentUpdateService,
    UpdateDocumentCommand,
)
from ragflow_agent.knowledge.application.permission_service import DefaultPermissionChecker
from ragflow_agent.knowledge.domain.document import (
    DocumentVersionStatus,
    transition_document_version,
)
from ragflow_agent.knowledge.domain.errors import (
    KnowledgeAuthorizationError,
    KnowledgeConflictError,
)
from ragflow_agent.knowledge.domain.lifecycle import IndexGeneration, LifecycleOperationStatus


@pytest.mark.asyncio
async def test_publish_then_rollback_selects_exactly_one_version() -> None:
    store = MemoryKnowledgeStore()
    document, old_version = seed_active_document(store)
    factory = MemoryKnowledgeUnitOfWorkFactory(store)
    search = MemorySearchIndex()
    seed_index(search, old_version, chunk_id="old-chunk")
    submitted = await DocumentUpdateService(
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
            reason="new source",
        )
    )
    candidate = transition_document_version(
        store.document_versions[submitted.operation.version_id],
        DocumentVersionStatus.INGESTING,
        changed_at=NOW,
    )
    store.document_versions[candidate.id] = candidate
    seed_index(search, candidate, chunk_id="new-chunk")
    publisher = DocumentVersionPublisher(
        unit_of_work_factory=factory,
        search=search,
        clock=FixedClock(NOW),
        id_generator=SequenceIdGenerator(["rollback-op"]),
        permission_checker=DefaultPermissionChecker(),
    )
    published = await publisher.complete_ingestion(
        context(), operation_id=submitted.operation.id, index_version_id="idx_version-2"
    )
    assert published.status is LifecycleOperationStatus.SUCCEEDED
    assert store.documents[document.id].current_version_id == "version-2"
    assert store.document_versions[old_version.id].status is DocumentVersionStatus.SUPERSEDED

    with pytest.raises(KnowledgeAuthorizationError):
        await publisher.rollback(
            context().model_copy(update={"actor_id": "intruder"}),
            document_id=document.id,
            target_version_id=old_version.id,
            idempotency_key="unauthorized-rollback",
            reason="not owner",
        )

    rolled_back = await publisher.rollback(
        context(),
        document_id=document.id,
        target_version_id=old_version.id,
        idempotency_key="rollback-1",
        reason="operator rollback",
    )
    assert rolled_back.status is LifecycleOperationStatus.SUCCEEDED
    assert store.documents[document.id].current_version_id == old_version.id
    assert len(store.lifecycle_operations) == 2


@pytest.mark.asyncio
async def test_delayed_operation_cannot_overwrite_newer_revision() -> None:
    store = MemoryKnowledgeStore()
    document, _old = seed_active_document(store)
    factory = MemoryKnowledgeUnitOfWorkFactory(store)
    search = MemorySearchIndex()
    submitted = await DocumentUpdateService(
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
    candidate = transition_document_version(
        store.document_versions["version-2"],
        DocumentVersionStatus.INGESTING,
        changed_at=NOW,
    )
    store.document_versions[candidate.id] = candidate
    seed_index(search, candidate)
    store.documents[document.id] = document.model_copy(update={"revision": 1})
    publisher = DocumentVersionPublisher(
        unit_of_work_factory=factory,
        search=search,
        clock=FixedClock(NOW),
        id_generator=SequenceIdGenerator([]),
        permission_checker=DefaultPermissionChecker(),
    )
    with pytest.raises(KnowledgeConflictError, match="stale"):
        await publisher.complete_ingestion(
            context(), operation_id=submitted.operation.id, index_version_id="idx_version-2"
        )
    assert store.documents[document.id].current_version_id == "version-1"


@pytest.mark.asyncio
async def test_generation_validation_prevents_alias_switch_on_partial_build() -> None:
    search = MemorySearchIndex()
    generation = IndexGeneration(
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        generation=2,
        physical_index="ragflow-agent-chunks-generation-2",
        read_alias="ragflow-agent-chunks-read",
        write_alias="ragflow-agent-chunks-write",
        fencing_token=2,
        expected_chunks=1,
        mapping_version="2",
        created_at=NOW,
    )
    with pytest.raises(KnowledgeConflictError, match="validation"):
        await IndexRebuildService(search).build_and_publish(
            context(), generation, (), expected_current=None
        )
    assert await search.resolve_alias(context(), alias=generation.read_alias) is None
