"""Persisted failure and retry behavior for the minimum Worker pipeline."""

from datetime import UTC, datetime

import pytest

from ragflow_agent.knowledge.application.ingestion import (
    IngestionPipeline,
    IngestionProfile,
    RetryableIngestionError,
)
from ragflow_agent.knowledge.application.knowledge_service import (
    CreateKnowledgeBaseCommand,
    KnowledgeService,
)
from ragflow_agent.knowledge.application.permission_service import DefaultPermissionChecker
from ragflow_agent.knowledge.application.upload import UploadDocumentCommand, UploadService
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, Visibility
from ragflow_agent.knowledge.domain.chunk import ParsedDocument
from ragflow_agent.knowledge.domain.document import DocumentVersionStatus
from ragflow_agent.knowledge.domain.ingestion import IngestionStage, IngestionStatus
from ragflow_agent.knowledge.infrastructure.chunking import GeneralChunker
from ragflow_agent.knowledge.ports.parsing import ParseRequest
from tests.fakes.knowledge import (
    FixedClock,
    MemoryIngestionQueue,
    MemoryKnowledgeStore,
    MemoryKnowledgeTrace,
    MemoryKnowledgeUnitOfWorkFactory,
    MemoryObjectStorage,
    SequenceIdGenerator,
)
from tests.fakes.minimum_rag import KeywordEmbedding, MemoryHybridSearch

NOW = datetime(2026, 7, 30, tzinfo=UTC)


class FailingParser:
    async def parse(self, request: ParseRequest) -> ParsedDocument:
        del request
        raise TimeoutError("fixture parser unavailable")


@pytest.mark.asyncio
async def test_retryable_failure_then_terminal_failure_is_persisted() -> None:
    store = MemoryKnowledgeStore()
    factory = MemoryKnowledgeUnitOfWorkFactory(store)
    ids = SequenceIdGenerator(["kb-a", "doc-a", "version-a"])
    clock = FixedClock(NOW)
    queue = MemoryIngestionQueue()
    context = AuthorizationContext(
        tenant_id="tenant-a",
        actor_id="owner-a",
        request_id="trace-a",
    )
    knowledge = KnowledgeService(
        unit_of_work_factory=factory,
        permission_checker=DefaultPermissionChecker(),
        id_generator=ids,
        clock=clock,
        trace=MemoryKnowledgeTrace(),
    )
    knowledge_base = await knowledge.create_knowledge_base(
        CreateKnowledgeBaseCommand(
            context=context,
            name="Maintenance",
            visibility=Visibility.TENANT,
        )
    )
    upload = UploadService(
        knowledge_service=knowledge,
        unit_of_work_factory=factory,
        storage=MemoryObjectStorage(),
        queue=queue,
        id_generator=ids,
        clock=clock,
        max_upload_bytes=1024,
    )
    submitted = await upload.submit(
        UploadDocumentCommand(
            context=context,
            knowledge_base_id=knowledge_base.id,
            file_name="manual.md",
            media_type="text/markdown",
            content=b"# Reset",
            idempotency_key="upload-1",
        )
    )
    embedding = KeywordEmbedding(dimensions=8)
    pipeline = IngestionPipeline(
        unit_of_work_factory=factory,
        parser=FailingParser(),
        chunker=GeneralChunker(max_tokens=16, overlap_tokens=2),
        embedding=embedding,
        search=MemoryHybridSearch(embedding),
        clock=clock,
        profile=IngestionProfile(
            chunk_strategy_id="general",
            chunk_strategy_version="1",
            chunk_max_tokens=16,
            embedding_model_id=embedding.model_id,
        ),
        max_attempts=2,
    )

    with pytest.raises(RetryableIngestionError):
        await pipeline.handle(queue.envelopes[0], delivery_attempt=1)

    assert store.ingestion_jobs[submitted.job.id].status is IngestionStatus.RUNNING
    parse_task = store.ingestion_tasks[f"{submitted.job.id}:{IngestionStage.PARSE.value}"]
    assert parse_task.status is IngestionStatus.FAILED
    assert parse_task.error is not None and parse_task.error.retryable

    with pytest.raises(TimeoutError, match="fixture parser unavailable"):
        await pipeline.handle(queue.envelopes[0], delivery_attempt=2)

    assert store.ingestion_jobs[submitted.job.id].status is IngestionStatus.FAILED
    assert (
        store.document_versions[submitted.job.document_version_id].status
        is DocumentVersionStatus.FAILED
    )
    parse_task = store.ingestion_tasks[f"{submitted.job.id}:{IngestionStage.PARSE.value}"]
    assert parse_task.attempt == 2
    assert parse_task.error is not None and not parse_task.error.retryable
