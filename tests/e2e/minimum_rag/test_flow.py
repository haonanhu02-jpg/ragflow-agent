"""Upload → Worker → hybrid retrieval → cited answer vertical slice."""

from datetime import UTC, datetime

import pytest

from ragflow_agent.knowledge.application.fixed_rag import FixedRagRequest, FixedRagService
from ragflow_agent.knowledge.application.ingestion import IngestionPipeline, IngestionProfile
from ragflow_agent.knowledge.application.knowledge_service import (
    CreateKnowledgeBaseCommand,
    KnowledgeQueryService,
    KnowledgeService,
)
from ragflow_agent.knowledge.application.permission_service import DefaultPermissionChecker
from ragflow_agent.knowledge.application.upload import UploadDocumentCommand, UploadService
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, Visibility
from ragflow_agent.knowledge.domain.ingestion import IngestionStatus
from ragflow_agent.knowledge.infrastructure.chunking import GeneralChunker
from ragflow_agent.knowledge.infrastructure.parsers import BasicObjectParser
from tests.fakes.knowledge import (
    FixedClock,
    MemoryIngestionQueue,
    MemoryKnowledgeStore,
    MemoryKnowledgeTrace,
    MemoryKnowledgeUnitOfWorkFactory,
    MemoryObjectStorage,
    SequenceIdGenerator,
)
from tests.fakes.minimum_rag import KeywordEmbedding, MemoryHybridSearch, StubChatProvider

NOW = datetime(2026, 7, 30, tzinfo=UTC)


@pytest.mark.asyncio
async def test_minimum_rag_vertical_slice_and_tenant_isolation() -> None:
    store = MemoryKnowledgeStore()
    factory = MemoryKnowledgeUnitOfWorkFactory(store)
    storage = MemoryObjectStorage()
    queue = MemoryIngestionQueue()
    trace = MemoryKnowledgeTrace()
    ids = SequenceIdGenerator(["kb-a", "doc-a", "version-a"])
    clock = FixedClock(NOW)
    permission = DefaultPermissionChecker()
    embedding = KeywordEmbedding(dimensions=16)
    search = MemoryHybridSearch(embedding)
    chat = StubChatProvider()
    owner = AuthorizationContext(
        tenant_id="tenant-a",
        actor_id="owner-a",
        request_id="trace-upload",
    )
    knowledge = KnowledgeService(
        unit_of_work_factory=factory,
        permission_checker=permission,
        id_generator=ids,
        clock=clock,
        trace=trace,
    )
    kb = await knowledge.create_knowledge_base(
        CreateKnowledgeBaseCommand(
            context=owner,
            name="Maintenance",
            visibility=Visibility.TENANT,
        )
    )
    upload = UploadService(
        knowledge_service=knowledge,
        unit_of_work_factory=factory,
        storage=storage,
        queue=queue,
        id_generator=ids,
        clock=clock,
        max_upload_bytes=4096,
    )
    submitted = await upload.submit(
        UploadDocumentCommand(
            context=owner,
            knowledge_base_id=kb.id,
            file_name="manual.md",
            media_type="text/markdown",
            content="# Alarm Recovery\n\n故障 复位 检查 控制器 继电器".encode(),
            idempotency_key="upload-1",
        )
    )
    assert submitted.job.status is IngestionStatus.PENDING
    assert len(queue.envelopes) == 1

    parser = BasicObjectParser(
        storage=storage,
        unit_of_work_factory=factory,
        clock=clock,
        max_bytes=4096,
    )
    pipeline = IngestionPipeline(
        unit_of_work_factory=factory,
        parser=parser,
        chunker=GeneralChunker(max_tokens=8, overlap_tokens=2),
        embedding=embedding,
        search=search,
        clock=clock,
        profile=IngestionProfile(
            chunk_strategy_id="general",
            chunk_strategy_version="1",
            chunk_max_tokens=8,
            embedding_model_id=embedding.model_id,
        ),
        max_attempts=3,
    )
    completed = await pipeline.handle(queue.envelopes[0])
    assert completed.status is IngestionStatus.SUCCEEDED
    assert store.documents["doc-a"].current_version_id == "version-a"

    query_service = KnowledgeQueryService(
        unit_of_work_factory=factory,
        permission_checker=permission,
        retriever=search,
    )
    fixed = FixedRagService(
        query_service=query_service,
        chat_provider=chat,
        chat_model_id=chat.model_id,
    )
    answer = await fixed.answer(
        FixedRagRequest(
            context=owner.model_copy(update={"request_id": "trace-query"}),
            question="复位 检查",
            knowledge_base_ids=(kb.id,),
        )
    )

    assert "[1]" in answer.answer
    assert len(answer.citations) >= 1
    assert answer.citations[0].document_version_id == "version-a"
    assert answer.retrieval_trace.authorization_applied

    other_tenant = AuthorizationContext(
        tenant_id="tenant-b",
        actor_id="owner-b",
        request_id="trace-denied",
    )
    with pytest.raises(Exception) as denied:
        await fixed.answer(
            FixedRagRequest(
                context=other_tenant,
                question="复位 检查",
                knowledge_base_ids=(kb.id,),
            )
        )
    assert getattr(denied.value, "status_code", None) in {403, 404}
