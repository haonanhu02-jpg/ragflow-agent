"""Phase 06 online pipeline through real Elasticsearch and PostgreSQL Trace."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from elasticsearch import AsyncElasticsearch
from pydantic import SecretStr
from sqlalchemy import text
from tests.fakes.minimum_rag import KeywordEmbedding
from tests.fakes.retrieval import FakeReranker, StubQueryTransformProvider

from ragflow_agent.config import DatabaseSettings, SearchSettings
from ragflow_agent.infrastructure.database import create_database_engine, create_session_factory
from ragflow_agent.knowledge.application.query import (
    OnlineRetrievalProfile,
    OnlineRetrievalService,
    SafeRetrievalTraceRecorder,
)
from ragflow_agent.knowledge.application.query.preprocess import QueryPreprocessor
from ragflow_agent.knowledge.application.query.trace import LoggingRetrievalTraceMetrics
from ragflow_agent.knowledge.application.query.transforms import QueryVariantBuilder
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, Visibility
from ragflow_agent.knowledge.domain.chunk import ChunkMetadata
from ragflow_agent.knowledge.domain.retrieval import (
    EmbeddingMetadata,
    IndexRecord,
    IndexVersion,
    IndexVersionStatus,
    RetrievalQuery,
)
from ragflow_agent.knowledge.infrastructure.database import SqlAlchemyRetrievalTraceStore
from ragflow_agent.knowledge.infrastructure.search import ElasticsearchSearchAdapter
from ragflow_agent.shared.ports.time import SystemClock


def _environment() -> tuple[str, str]:
    database = os.environ.get("RAGFLOW_AGENT_TEST_DATABASE_URL")
    elasticsearch = os.environ.get("RAGFLOW_AGENT_TEST_ELASTICSEARCH_URL")
    if not database or not elasticsearch:
        pytest.skip("Phase 06 PostgreSQL and Elasticsearch settings are not configured")
    return database, elasticsearch


@pytest.mark.asyncio
async def test_real_online_retrieval_persists_minimized_trace() -> None:
    database_url, elasticsearch_url = _environment()
    suffix = uuid4().hex
    embedding = KeywordEmbedding(dimensions=16)
    index_name = f"ragflow-agent-phase06-e2e-{suffix}"
    client = AsyncElasticsearch(elasticsearch_url, verify_certs=False)
    search = ElasticsearchSearchAdapter(
        SearchSettings(
            url=SecretStr(elasticsearch_url),
            index_name=index_name,
            verify_certs=False,
        ),
        embedding=embedding,
        embedding_model_id=embedding.model_id,
        embedding_dimensions=embedding.dimensions,
        client=client,
    )
    engine = create_database_engine(DatabaseSettings(url=SecretStr(database_url)))
    sessions = create_session_factory(engine)
    trace_store = SqlAlchemyRetrievalTraceStore(sessions)
    context = AuthorizationContext(
        tenant_id=f"tenant-{suffix}",
        actor_id="owner-a",
        request_id=f"request-{suffix}",
    )
    version = IndexVersion(
        id=f"index-{suffix}",
        tenant_id=context.tenant_id,
        knowledge_base_id=f"kb-{suffix}",
        embedding=EmbeddingMetadata(
            model_id=embedding.model_id,
            dimensions=embedding.dimensions,
            normalized=True,
        ),
        status=IndexVersionStatus.BUILDING,
        created_at=datetime.now(UTC),
    )
    content = "traction controller alarm reset relay inspection"
    record = IndexRecord(
        index_version_id=version.id,
        tenant_id=context.tenant_id,
        knowledge_base_id=version.knowledge_base_id,
        owner_id=context.actor_id,
        visibility=Visibility.PRIVATE,
        document_id=f"doc-{suffix}",
        document_version_id=f"version-{suffix}",
        chunk_id=f"chunk-{suffix}",
        content=content,
        media_type="text/plain",
        created_at=datetime.now(UTC),
        embedding=embedding.vector(content),
        metadata=ChunkMetadata(language="en", page_start=1, page_end=1),
    )
    trace_id = f"trace-{suffix}"
    service = OnlineRetrievalService(
        search=search,
        reranker=FakeReranker({record.chunk_id: 0.95}),
        variants=QueryVariantBuilder(
            StubQueryTransformProvider(),
            model_id="deepseek-chat",
            rewrite_enabled=False,
            translation_enabled=False,
            keyword_expansion_enabled=False,
            max_variants=4,
        ),
        preprocessor=QueryPreprocessor(max_characters=1000),
        trace_recorder=SafeRetrievalTraceRecorder(
            trace_store,
            LoggingRetrievalTraceMetrics(),
        ),
        clock=SystemClock(),
        profile=OnlineRetrievalProfile(
            candidate_top_k=10,
            rerank_candidate_count=5,
            final_top_k=3,
            provider_ids=("embedding:fake", "reranker:fake"),
        ),
    )
    try:
        await search.ensure_index()
        await search.upsert(context, version, (record,))
        await search.activate(context, version)
        result = await service.retrieve(
            context,
            RetrievalQuery(
                tenant_id=context.tenant_id,
                text="controller reset",
                knowledge_base_ids=(version.knowledge_base_id,),
                index_version_ids=(version.id,),
                top_k=10,
                top_n=3,
                trace_id=trace_id,
                request_id=context.request_id,
            ),
        )

        assert result.candidates[0].chunk_id == record.chunk_id
        assert result.candidates[0].score.full_text_rank == 1
        assert result.candidates[0].score.vector_rank == 1
        persisted = await trace_store.get(context, trace_id)
        assert persisted is not None
        assert persisted.original_query is None
        assert persisted.candidates[0].selected is True
        assert persisted.candidates[0].fusion_rank == 1
        assert persisted.candidates[0].rerank_rank == 1
        assert persisted.candidates[0].rerank_score == pytest.approx(0.95)
        assert persisted.candidates[0].final_rank == 1
    finally:
        await client.indices.delete(index=index_name, ignore_unavailable=True)
        async with sessions() as session:
            await session.execute(
                text("delete from knowledge_retrieval_traces where trace_id=:trace_id"),
                {"trace_id": trace_id},
            )
            await session.commit()
        await search.close()
        await engine.dispose()
