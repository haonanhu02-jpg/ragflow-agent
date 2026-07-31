"""Production wiring for the Phase 05 multi-format minimum RAG profile."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from ragflow_agent.config import AppSettings
from ragflow_agent.infrastructure.database import (
    create_database_engine,
    create_session_factory,
)
from ragflow_agent.knowledge.application.chunker_registry import ChunkerRegistry
from ragflow_agent.knowledge.application.fixed_rag import FixedRagService
from ragflow_agent.knowledge.application.ingestion import (
    IngestionPipeline,
    IngestionProfile,
)
from ragflow_agent.knowledge.application.knowledge_service import (
    KnowledgeQueryService,
    KnowledgeService,
)
from ragflow_agent.knowledge.application.lifecycle import (
    DocumentDeletionService,
    DocumentUpdateService,
    DocumentVersionPublisher,
    IndexRebuildService,
    LifecycleBatchService,
    LifecycleControlService,
    LifecycleReconciler,
)
from ragflow_agent.knowledge.application.parser_registry import ParserRegistry
from ragflow_agent.knowledge.application.permission_service import DefaultPermissionChecker
from ragflow_agent.knowledge.application.query import (
    OnlineRetrievalProfile,
    OnlineRetrievalService,
    RetrievalTraceAccessService,
    RetrievalTraceMaintenanceService,
    SafeRetrievalTraceRecorder,
)
from ragflow_agent.knowledge.application.query.preprocess import QueryPreprocessor
from ragflow_agent.knowledge.application.query.trace import LoggingRetrievalTraceMetrics
from ragflow_agent.knowledge.application.query.transforms import QueryVariantBuilder
from ragflow_agent.knowledge.application.upload import UploadService
from ragflow_agent.knowledge.infrastructure.chunking import GeneralChunker, ScenarioChunker
from ragflow_agent.knowledge.infrastructure.database import (
    SqlAlchemyKnowledgeUnitOfWorkFactory,
    SqlAlchemyRetrievalTraceStore,
)
from ragflow_agent.knowledge.infrastructure.models import (
    ChatQueryTransformProvider,
    build_chat_provider,
    build_embedding_adapter,
    build_reranker,
)
from ragflow_agent.knowledge.infrastructure.object_store import S3ObjectStorage
from ragflow_agent.knowledge.infrastructure.ocr import TesseractOcrEngine
from ragflow_agent.knowledge.infrastructure.parsers import build_default_binary_parsers
from ragflow_agent.knowledge.infrastructure.queue import ArqIngestionQueue
from ragflow_agent.knowledge.infrastructure.search import ElasticsearchSearchAdapter
from ragflow_agent.knowledge.infrastructure.trace import LoggingKnowledgeTrace
from ragflow_agent.shared.ports.identity import Uuid4Generator
from ragflow_agent.shared.ports.time import SystemClock
from ragflow_agent.worker.outbox import LifecycleOutboxDispatcher
from ragflow_agent.worker.retry import RetryPolicy


@dataclass(slots=True)
class MinimumRagRuntime:
    """Owned resources and application services shared by API or Worker."""

    engine: AsyncEngine
    storage: S3ObjectStorage
    queue: ArqIngestionQueue
    search: ElasticsearchSearchAdapter
    knowledge_service: KnowledgeService
    query_service: KnowledgeQueryService
    upload_service: UploadService
    ingestion_pipeline: IngestionPipeline
    fixed_rag_service: FixedRagService
    retrieval_trace_access: RetrievalTraceAccessService
    retrieval_trace_maintenance: RetrievalTraceMaintenanceService
    reranker: object
    document_updates: DocumentUpdateService
    document_deletions: DocumentDeletionService
    version_publisher: DocumentVersionPublisher
    index_rebuild: IndexRebuildService
    lifecycle_reconciler: LifecycleReconciler
    lifecycle_batches: LifecycleBatchService
    lifecycle_outbox: LifecycleOutboxDispatcher
    lifecycle_control: LifecycleControlService

    async def open(self, *, open_queue: bool = True) -> None:
        await self.storage.ensure_bucket()
        await self.search.ensure_index()
        if open_queue:
            await self.queue.open()

    async def close(self) -> None:
        await self.queue.close()
        await self.search.close()
        close_reranker = getattr(self.reranker, "close", None)
        if close_reranker is not None:
            await close_reranker()
        await self.engine.dispose()


def build_minimum_rag_runtime(settings: AppSettings) -> MinimumRagRuntime:
    """Construct adapters without opening network connections."""
    engine = create_database_engine(settings.database)
    sessions = create_session_factory(engine)
    unit_of_work_factory = SqlAlchemyKnowledgeUnitOfWorkFactory(sessions)
    permission_checker = DefaultPermissionChecker()
    id_generator = Uuid4Generator()
    clock = SystemClock()
    trace = LoggingKnowledgeTrace()
    storage = S3ObjectStorage(settings.object_store)
    queue = ArqIngestionQueue(settings.queue)
    embedding = build_embedding_adapter(settings.models)
    chat_provider = build_chat_provider(
        settings.models,
        timeout_seconds=settings.agentic_rag.model_timeout_seconds,
        max_completion_tokens=settings.agentic_rag.max_generated_tokens,
    )
    reranker = build_reranker(settings.models)
    search = ElasticsearchSearchAdapter(
        settings.search,
        embedding=embedding,
        embedding_model_id=settings.models.embedding_model,
        embedding_dimensions=settings.models.embedding_dimensions,
    )
    ocr = TesseractOcrEngine(command=settings.ingestion.tesseract_command)
    parser = ParserRegistry(
        parsers=build_default_binary_parsers(settings.ingestion, ocr=ocr),
        storage=storage,
        unit_of_work_factory=unit_of_work_factory,
        clock=clock,
        max_bytes=settings.ingestion.max_upload_bytes,
        timeout_seconds=settings.ingestion.parser_timeout_seconds,
        ocr_language=settings.ingestion.ocr_languages,
    )
    general_chunker = GeneralChunker(
        max_tokens=settings.ingestion.chunk_max_tokens,
        overlap_tokens=settings.ingestion.chunk_overlap_tokens,
    )
    chunker = ChunkerRegistry(
        chunkers=(
            general_chunker,
            *(
                ScenarioChunker(
                    strategy_id=strategy_id,
                    max_tokens=settings.ingestion.chunk_max_tokens,
                    overlap_tokens=settings.ingestion.chunk_overlap_tokens,
                )
                for strategy_id in (
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
    knowledge_service = KnowledgeService(
        unit_of_work_factory=unit_of_work_factory,
        permission_checker=permission_checker,
        id_generator=id_generator,
        clock=clock,
        trace=trace,
    )
    trace_store = SqlAlchemyRetrievalTraceStore(sessions)
    trace_metrics = LoggingRetrievalTraceMetrics()
    trace_recorder = SafeRetrievalTraceRecorder(trace_store, trace_metrics)
    online_retriever = OnlineRetrievalService(
        search=search,
        reranker=reranker,
        variants=QueryVariantBuilder(
            ChatQueryTransformProvider(chat_provider, model_id=settings.models.chat_model),
            model_id=settings.models.chat_model,
            rewrite_enabled=settings.retrieval.rewrite_enabled,
            translation_enabled=settings.retrieval.translation_enabled,
            keyword_expansion_enabled=settings.retrieval.keyword_expansion_enabled,
            max_variants=settings.retrieval.max_query_variants,
        ),
        preprocessor=QueryPreprocessor(max_characters=settings.retrieval.max_query_characters),
        trace_recorder=trace_recorder,
        clock=clock,
        profile=OnlineRetrievalProfile(
            config_version=settings.retrieval.config_version,
            rrf_k=settings.retrieval.rrf_k,
            candidate_top_k=settings.retrieval.candidate_top_k,
            rerank_candidate_count=settings.retrieval.rerank_candidate_count,
            final_top_k=settings.retrieval.final_top_k,
            fusion_threshold=settings.retrieval.fusion_threshold,
            fallback_threshold_floor=settings.retrieval.fallback_threshold_floor,
            max_fallback_attempts=settings.retrieval.max_fallback_attempts,
            fallback_candidate_multiplier=settings.retrieval.fallback_candidate_multiplier,
            per_document_limit=settings.retrieval.per_document_limit,
            reranker_timeout_seconds=settings.retrieval.reranker_timeout_seconds,
            trace_retention_days=settings.retrieval_trace.retention_days,
            provider_ids=(
                f"embedding:{settings.models.embedding_model}",
                f"reranker:{settings.models.reranker_model}",
                f"query:{settings.models.chat_model}",
            ),
        ),
    )
    query_service = KnowledgeQueryService(
        unit_of_work_factory=unit_of_work_factory,
        permission_checker=permission_checker,
        retriever=online_retriever,
    )
    upload_service = UploadService(
        knowledge_service=knowledge_service,
        unit_of_work_factory=unit_of_work_factory,
        storage=storage,
        queue=queue,
        id_generator=id_generator,
        clock=clock,
        max_upload_bytes=settings.ingestion.max_upload_bytes,
    )
    version_publisher = DocumentVersionPublisher(
        unit_of_work_factory=unit_of_work_factory,
        search=search,
        clock=clock,
        id_generator=id_generator,
        permission_checker=permission_checker,
        history_retention_days=settings.lifecycle.history_retention_days,
    )
    document_updates = DocumentUpdateService(
        unit_of_work_factory=unit_of_work_factory,
        storage=storage,
        permission_checker=permission_checker,
        id_generator=id_generator,
        clock=clock,
        max_upload_bytes=settings.ingestion.max_upload_bytes,
    )
    document_deletions = DocumentDeletionService(
        unit_of_work_factory=unit_of_work_factory,
        search=search,
        storage=storage,
        permission_checker=permission_checker,
        id_generator=id_generator,
        clock=clock,
        retention_days=settings.lifecycle.soft_delete_retention_days,
    )
    ingestion_pipeline = IngestionPipeline(
        unit_of_work_factory=unit_of_work_factory,
        parser=parser,
        chunker=chunker,
        embedding=embedding,
        search=search,
        clock=clock,
        profile=IngestionProfile(
            chunk_strategy_id="auto",
            chunk_strategy_version="auto",
            chunk_max_tokens=settings.ingestion.chunk_max_tokens,
            embedding_model_id=settings.models.embedding_model,
        ),
        max_attempts=settings.worker.max_tries,
        lifecycle_activation=version_publisher,
    )
    fixed_rag_service = FixedRagService(
        query_service=query_service,
        chat_provider=chat_provider,
        chat_model_id=settings.models.chat_model,
        id_generator=id_generator,
    )
    retrieval_trace_access = RetrievalTraceAccessService(
        trace_store,
        detailed_roles=settings.retrieval_trace.detailed_roles,
    )
    retrieval_trace_maintenance = RetrievalTraceMaintenanceService(trace_store)
    lifecycle_reconciler = LifecycleReconciler(
        unit_of_work_factory=unit_of_work_factory,
        search=search,
        storage=storage,
        clock=clock,
        limit=settings.lifecycle.reconcile_batch_size,
    )
    lifecycle_batches = LifecycleBatchService(
        unit_of_work_factory=unit_of_work_factory,
        id_generator=id_generator,
        clock=clock,
        max_concurrency=settings.lifecycle.batch_concurrency,
    )
    lifecycle_outbox = LifecycleOutboxDispatcher(
        unit_of_work_factory=unit_of_work_factory,
        queue=queue,
        clock=clock,
        document_purger=document_deletions,
        retry_policy=RetryPolicy(
            max_attempts=settings.lifecycle.max_attempts,
            concurrency_attempts=settings.lifecycle.concurrency_attempts,
            base_seconds=settings.lifecycle.retry_base_seconds,
            max_seconds=settings.lifecycle.retry_max_seconds,
        ),
    )
    lifecycle_control = LifecycleControlService(
        unit_of_work_factory=unit_of_work_factory,
        permission_checker=permission_checker,
        clock=clock,
    )
    return MinimumRagRuntime(
        engine=engine,
        storage=storage,
        queue=queue,
        search=search,
        knowledge_service=knowledge_service,
        query_service=query_service,
        upload_service=upload_service,
        ingestion_pipeline=ingestion_pipeline,
        fixed_rag_service=fixed_rag_service,
        retrieval_trace_access=retrieval_trace_access,
        retrieval_trace_maintenance=retrieval_trace_maintenance,
        reranker=reranker,
        document_updates=document_updates,
        document_deletions=document_deletions,
        version_publisher=version_publisher,
        index_rebuild=IndexRebuildService(search),
        lifecycle_reconciler=lifecycle_reconciler,
        lifecycle_batches=lifecycle_batches,
        lifecycle_outbox=lifecycle_outbox,
        lifecycle_control=lifecycle_control,
    )
