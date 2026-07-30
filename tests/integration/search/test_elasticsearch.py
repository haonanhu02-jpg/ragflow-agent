"""Real Elasticsearch BM25, KNN, RRF, version, and tenant behavior."""

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from elasticsearch import AsyncElasticsearch
from pydantic import SecretStr

from ragflow_agent.config import SearchSettings
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, Visibility
from ragflow_agent.knowledge.domain.chunk import ChunkMetadata
from ragflow_agent.knowledge.domain.retrieval import (
    EmbeddingMetadata,
    IndexRecord,
    IndexVersion,
    IndexVersionStatus,
    RetrievalEmptyReason,
    RetrievalQuery,
    RetrievalStage,
)
from ragflow_agent.knowledge.infrastructure.search import ElasticsearchSearchAdapter
from tests.fakes.minimum_rag import KeywordEmbedding


def _elasticsearch_url() -> str:
    value = os.environ.get("RAGFLOW_AGENT_TEST_ELASTICSEARCH_URL")
    if value is None:
        pytest.skip("RAGFLOW_AGENT_TEST_ELASTICSEARCH_URL is not configured")
    return value


@pytest.mark.asyncio
async def test_elasticsearch_full_text_vector_hybrid_and_tenant_filter() -> None:
    suffix = uuid4().hex
    embedding = KeywordEmbedding(dimensions=16)
    index_name = f"ragflow-agent-phase04-{suffix}"
    client = AsyncElasticsearch(_elasticsearch_url(), verify_certs=False)
    adapter = ElasticsearchSearchAdapter(
        SearchSettings(
            url=SecretStr(_elasticsearch_url()),
            index_name=index_name,
            verify_certs=False,
        ),
        embedding=embedding,
        embedding_model_id=embedding.model_id,
        embedding_dimensions=embedding.dimensions,
        client=client,
    )
    owner = AuthorizationContext(
        tenant_id=f"tenant-{suffix}",
        actor_id="owner-a",
        request_id=f"trace-{suffix}",
    )
    index_version = IndexVersion(
        id=f"index-{suffix}",
        tenant_id=owner.tenant_id,
        knowledge_base_id=f"kb-{suffix}",
        embedding=EmbeddingMetadata(
            model_id=embedding.model_id,
            dimensions=embedding.dimensions,
            normalized=True,
        ),
        status=IndexVersionStatus.BUILDING,
        created_at=datetime.now(UTC),
    )
    text = "alarm reset controller inspection relay"
    record = IndexRecord(
        index_version_id=index_version.id,
        tenant_id=owner.tenant_id,
        knowledge_base_id=index_version.knowledge_base_id,
        owner_id=owner.actor_id,
        visibility=Visibility.TENANT,
        document_id=f"doc-{suffix}",
        document_version_id=f"version-{suffix}",
        chunk_id=f"chunk-{suffix}",
        content=text,
        media_type="text/markdown",
        created_at=datetime.now(UTC),
        embedding=embedding.vector(text),
        metadata=ChunkMetadata(heading_path=("Recovery",), page_start=1, page_end=1),
    )
    query = RetrievalQuery(
        tenant_id=owner.tenant_id,
        text="controller reset",
        knowledge_base_ids=(index_version.knowledge_base_id,),
        top_k=5,
        top_n=3,
        trace_id=owner.request_id,
    )
    try:
        await adapter.ensure_index()
        await adapter.upsert(owner, index_version, (record,))
        await adapter.activate(owner, index_version)

        full_text = await adapter.retrieve_full_text(owner, query)
        vector = await adapter.retrieve_vector(owner, query)
        hybrid = await adapter.retrieve(owner, query)

        assert full_text[0].chunk_id == record.chunk_id
        assert vector[0].chunk_id == record.chunk_id
        assert hybrid.candidates[0].chunk_id == record.chunk_id
        assert {event.stage for event in hybrid.trace.events} >= {
            RetrievalStage.FULL_TEXT,
            RetrievalStage.VECTOR,
            RetrievalStage.FUSION,
        }
        assert hybrid.citations[0].document_version_id == record.document_version_id

        other = AuthorizationContext(
            tenant_id=f"other-{suffix}",
            actor_id="owner-b",
            request_id=f"other-trace-{suffix}",
        )
        denied = await adapter.retrieve(
            other,
            query.model_copy(
                update={"tenant_id": other.tenant_id, "trace_id": other.request_id}
            ),
        )
        assert denied.candidates == ()
        assert denied.empty_reason is RetrievalEmptyReason.NO_MATCH
    finally:
        await client.indices.delete(
            index=index_name,
            ignore_unavailable=True,
        )
        await adapter.close()
