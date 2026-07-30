"""Executable contracts for every Phase 03 capability port."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, Visibility
from ragflow_agent.knowledge.domain.chunk import (
    BlockKind,
    ChunkMetadata,
    ChunkRecord,
    ParsedBlock,
    ParsedDocument,
)
from ragflow_agent.knowledge.domain.ingestion import (
    IngestionEnvelope,
    IngestionStage,
    IngestionTask,
)
from ragflow_agent.knowledge.domain.retrieval import (
    Citation,
    EmbeddingMetadata,
    IndexRecord,
    IndexVersion,
    IndexVersionStatus,
    RetrievalCandidate,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStage,
    RetrievalTrace,
    RetrievalTraceEvent,
    ScoreBreakdown,
)
from ragflow_agent.knowledge.ports.chunking import ChunkerPort, ChunkingRequest
from ragflow_agent.knowledge.ports.embedding import (
    EmbeddingInput,
    EmbeddingPort,
    EmbeddingRequest,
)
from ragflow_agent.knowledge.ports.parsing import ParseRequest, ParserPort
from ragflow_agent.knowledge.ports.queue import IngestionQueuePort
from ragflow_agent.knowledge.ports.search import (
    RerankerPort,
    RerankRequest,
    RetrieverPort,
    SearchIndexPort,
)
from ragflow_agent.knowledge.ports.storage import (
    ObjectStoragePort,
    StorageWriteRequest,
)
from ragflow_agent.knowledge.ports.trace import (
    KnowledgeTraceEvent,
    KnowledgeTraceKind,
    KnowledgeTracePort,
)
from tests.fakes.knowledge import (
    DeterministicEmbedding,
    FixtureChunker,
    FixtureParser,
    FixtureRetriever,
    IdentityReranker,
    MemoryIngestionQueue,
    MemoryKnowledgeTrace,
    MemoryObjectStorage,
    MemorySearchIndex,
)

NOW = datetime(2026, 7, 30, 8, 0, tzinfo=UTC)
CONTEXT = AuthorizationContext(
    tenant_id="tenant-a",
    actor_id="owner-a",
    request_id="request-1",
)


async def _content(payload: bytes) -> AsyncIterator[bytes]:
    midpoint = len(payload) // 2
    yield payload[:midpoint]
    yield payload[midpoint:]


def _parsed_document() -> ParsedDocument:
    return ParsedDocument(
        id="parsed-1",
        tenant_id="tenant-a",
        knowledge_base_id="kb-1",
        document_id="document-1",
        document_version_id="version-1",
        parser_name="fixture",
        parser_version="1",
        parsed_at=NOW,
        blocks=(
            ParsedBlock(
                id="block-1",
                kind=BlockKind.TEXT,
                order=0,
                text="Open the breaker.",
            ),
        ),
    )


def _chunk() -> ChunkRecord:
    return ChunkRecord(
        id="chunk-1",
        tenant_id="tenant-a",
        knowledge_base_id="kb-1",
        document_id="document-1",
        document_version_id="version-1",
        parsed_document_id="parsed-1",
        sequence=0,
        content="Open the breaker.",
        source_block_ids=("block-1",),
        metadata=ChunkMetadata(page_start=1, page_end=1),
    )


def _query_result() -> RetrievalResult:
    query = RetrievalQuery(
        tenant_id="tenant-a",
        text="breaker",
        knowledge_base_ids=("kb-1",),
        trace_id="trace-1",
    )
    citation = Citation(
        tenant_id="tenant-a",
        knowledge_base_id="kb-1",
        document_id="document-1",
        document_version_id="version-1",
        chunk_id="chunk-1",
        quote="Open the breaker.",
    )
    candidate = RetrievalCandidate(
        tenant_id="tenant-a",
        knowledge_base_id="kb-1",
        document_id="document-1",
        document_version_id="version-1",
        chunk_id="chunk-1",
        content="Open the breaker.",
        score=ScoreBreakdown(final_score=1),
        citation=citation,
    )
    trace = RetrievalTrace(
        trace_id="trace-1",
        tenant_id="tenant-a",
        original_query="breaker",
        authorization_applied=True,
        events=(
            RetrievalTraceEvent(
                sequence=0,
                stage=RetrievalStage.SELECT,
                elapsed_ms=1,
                candidate_count=1,
            ),
        ),
    )
    return RetrievalResult(query=query, candidates=(candidate,), trace=trace)


@pytest.mark.asyncio
async def test_storage_port_streams_and_verifies_tenant_namespaced_object() -> None:
    adapter: ObjectStoragePort = MemoryObjectStorage()
    payload = b"source document"
    request = StorageWriteRequest(
        tenant_id="tenant-a",
        object_key="tenants/tenant-a/kb-1/document-1/version-1/source",
        media_type="text/plain",
        size_bytes=len(payload),
        checksum_sha256=sha256(payload).hexdigest(),
        trace_id="trace-1",
    )

    stored = await adapter.put(CONTEXT, request, _content(payload))
    restored = b"".join([chunk async for chunk in adapter.read(CONTEXT, stored)])
    await adapter.delete(CONTEXT, stored)

    assert restored == payload


@pytest.mark.asyncio
async def test_parser_and_chunker_ports_return_normalized_contracts() -> None:
    parsed = _parsed_document()
    parser: ParserPort = FixtureParser(parsed)
    chunker: ChunkerPort = FixtureChunker((_chunk(),))

    actual = await parser.parse(
        ParseRequest(
            tenant_id="tenant-a",
            knowledge_base_id="kb-1",
            document_id="document-1",
            document_version_id="version-1",
            object_key="tenants/tenant-a/source",
            media_type="text/plain",
            trace_id="trace-1",
        )
    )
    chunks = await chunker.chunk(
        CONTEXT,
        ChunkingRequest(
            parsed_document=actual,
            strategy_id="fixture",
            strategy_version="1",
            trace_id="trace-1",
        ),
    )

    assert chunks[0].source_block_ids == ("block-1",)


@pytest.mark.asyncio
async def test_embedding_and_search_index_ports_keep_version_compatibility() -> None:
    embedding: EmbeddingPort = DeterministicEmbedding(dimensions=3)
    request = EmbeddingRequest(
        tenant_id="tenant-a",
        model_id="fixture-embedding",
        inputs=(EmbeddingInput(id="chunk-1", text="Open the breaker."),),
        trace_id="trace-1",
    )
    result = await embedding.embed(CONTEXT, request)
    version = IndexVersion(
        id="index-v1",
        tenant_id="tenant-a",
        knowledge_base_id="kb-1",
        embedding=EmbeddingMetadata(
            model_id=result.model_id,
            dimensions=result.dimensions,
            normalized=result.normalized,
        ),
        status=IndexVersionStatus.BUILDING,
        created_at=NOW,
    )
    record = IndexRecord(
        index_version_id=version.id,
        tenant_id="tenant-a",
        knowledge_base_id="kb-1",
        owner_id="owner-a",
        visibility=Visibility.PRIVATE,
        document_id="document-1",
        document_version_id="version-1",
        chunk_id="chunk-1",
        content="Open the breaker.",
        media_type="text/plain",
        created_at=NOW,
        embedding=result.vectors[0].values,
        metadata=ChunkMetadata(page_start=1, page_end=1),
    )
    index: SearchIndexPort = MemorySearchIndex()

    await index.upsert(CONTEXT, version, (record,))
    await index.activate(CONTEXT, version)
    await index.delete(
        CONTEXT,
        index_version_id=version.id,
        chunk_ids=("chunk-1",),
    )


@pytest.mark.asyncio
async def test_retriever_and_reranker_ports_keep_structured_candidates() -> None:
    result = _query_result()
    retriever: RetrieverPort = FixtureRetriever(result)
    reranker: RerankerPort = IdentityReranker()

    retrieved = await retriever.retrieve(CONTEXT, result.query)
    reranked = await reranker.rerank(
        CONTEXT,
        RerankRequest(query=result.query, candidates=retrieved.candidates),
    )

    assert reranked == result.candidates


@pytest.mark.asyncio
async def test_queue_and_trace_ports_carry_tenant_and_correlation() -> None:
    task = IngestionTask(
        id="task-1",
        tenant_id="tenant-a",
        job_id="job-1",
        document_version_id="version-1",
        stage=IngestionStage.PARSE,
        idempotency_key="job-1:parse",
        trace_id="trace-1",
        created_at=NOW,
        updated_at=NOW,
    )
    envelope = IngestionEnvelope.from_task(
        task,
        message_id="message-1",
        created_at=NOW,
    )
    queue: IngestionQueuePort = MemoryIngestionQueue()
    trace: KnowledgeTracePort = MemoryKnowledgeTrace()

    receipt = await queue.publish(CONTEXT, envelope)
    await trace.record(
        KnowledgeTraceEvent(
            trace_id="trace-1",
            request_id="request-1",
            tenant_id="tenant-a",
            actor_id="owner-a",
            kind=KnowledgeTraceKind.INGESTION,
            action="queued",
            resource_type="ingestion_task",
            resource_id="task-1",
            occurred_at=NOW,
        )
    )

    assert receipt.message_id == "message-1"
