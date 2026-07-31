"""Eight-format upload-to-index vertical slice with real parser logic."""

from datetime import UTC, datetime

import pytest
from tests.fakes.knowledge import (
    FixedClock,
    MemoryIngestionQueue,
    MemoryKnowledgeStore,
    MemoryKnowledgeUnitOfWorkFactory,
    MemoryObjectStorage,
    SequenceIdGenerator,
)
from tests.fakes.minimum_rag import KeywordEmbedding, MemoryHybridSearch
from tests.fakes.parsing import StaticOcrEngine, generated_format_samples

from ragflow_agent.config import IngestionSettings
from ragflow_agent.knowledge.application.chunker_registry import ChunkerRegistry
from ragflow_agent.knowledge.application.ingestion import IngestionPipeline, IngestionProfile
from ragflow_agent.knowledge.application.knowledge_service import (
    CreateKnowledgeBaseCommand,
    KnowledgeService,
)
from ragflow_agent.knowledge.application.parser_registry import ParserRegistry
from ragflow_agent.knowledge.application.permission_service import DefaultPermissionChecker
from ragflow_agent.knowledge.application.upload import UploadDocumentCommand, UploadService
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, Visibility
from ragflow_agent.knowledge.domain.ingestion import IngestionStatus
from ragflow_agent.knowledge.infrastructure.chunking import GeneralChunker, ScenarioChunker
from ragflow_agent.knowledge.infrastructure.parsers import build_default_binary_parsers
from ragflow_agent.knowledge.infrastructure.trace import LoggingKnowledgeTrace

NOW = datetime(2026, 7, 31, tzinfo=UTC)


@pytest.mark.asyncio
async def test_all_formats_complete_upload_parse_chunk_embed_index_pipeline() -> None:
    samples = generated_format_samples()
    identifiers = ["kb-a"]
    for index in range(len(samples)):
        identifiers.extend((f"doc-{index}", f"version-{index}"))
    ids = SequenceIdGenerator(identifiers)
    store = MemoryKnowledgeStore()
    factory = MemoryKnowledgeUnitOfWorkFactory(store)
    storage = MemoryObjectStorage()
    queue = MemoryIngestionQueue()
    clock = FixedClock(NOW)
    context = AuthorizationContext(
        tenant_id="tenant-a",
        actor_id="owner-a",
        request_id="trace-upload",
    )
    permission = DefaultPermissionChecker()
    knowledge = KnowledgeService(
        unit_of_work_factory=factory,
        permission_checker=permission,
        id_generator=ids,
        clock=clock,
        trace=LoggingKnowledgeTrace(),
    )
    knowledge_base = await knowledge.create_knowledge_base(
        CreateKnowledgeBaseCommand(
            context=context,
            name="Multi-format maintenance",
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
        max_upload_bytes=10 * 1024 * 1024,
    )
    settings = IngestionSettings(
        chunk_max_tokens=64,
        chunk_overlap_tokens=8,
    )
    parser = ParserRegistry(
        parsers=build_default_binary_parsers(settings, ocr=StaticOcrEngine()),
        storage=storage,
        unit_of_work_factory=factory,
        clock=clock,
        max_bytes=settings.max_upload_bytes,
        timeout_seconds=settings.parser_timeout_seconds,
        ocr_language="eng",
    )
    chunker = ChunkerRegistry(
        chunkers=(
            GeneralChunker(max_tokens=64, overlap_tokens=8),
            *(
                ScenarioChunker(
                    strategy_id=strategy,
                    max_tokens=64,
                    overlap_tokens=8,
                )
                for strategy in (
                    "paper",
                    "book",
                    "manual",
                    "laws",
                    "qa",
                    "table",
                    "resume",
                    "picture",
                )
            ),
        )
    )
    embedding = KeywordEmbedding(dimensions=32)
    search = MemoryHybridSearch(embedding)
    pipeline = IngestionPipeline(
        unit_of_work_factory=factory,
        parser=parser,
        chunker=chunker,
        embedding=embedding,
        search=search,
        clock=clock,
        profile=IngestionProfile(
            chunk_strategy_id="auto",
            chunk_strategy_version="auto",
            chunk_max_tokens=64,
            embedding_model_id=embedding.model_id,
        ),
        max_attempts=3,
    )

    for index, sample in enumerate(samples):
        submitted = await upload.submit(
            UploadDocumentCommand(
                context=context.model_copy(
                    update={"request_id": f"trace-upload-{index}"}
                ),
                knowledge_base_id=knowledge_base.id,
                file_name=sample.name,
                media_type=sample.media_type,
                content=sample.payload,
                idempotency_key=f"upload-{index}",
            )
        )
        envelope = queue.envelopes[index]
        completed = await pipeline.handle(envelope)
        assert completed.status is IngestionStatus.SUCCEEDED
        records = [
            record
            for record in search.records.values()
            if record.document_version_id == submitted.job.document_version_id
        ]
        assert records, sample.name
        assert all(record.metadata.parser_name is not None for record in records)
        assert all(record.metadata.chunk_strategy_id is not None for record in records)
        assert all(record.tenant_id == context.tenant_id for record in records)

    assert len(store.documents) == len(samples)
