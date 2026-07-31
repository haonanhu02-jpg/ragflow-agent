"""Real Elasticsearch Phase 06 filters, channels, ranks, and role ACL."""

from __future__ import annotations

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
    FilterOperator,
    IndexRecord,
    IndexVersion,
    IndexVersionStatus,
    MetadataField,
    MetadataFilter,
    RetrievalQuery,
)
from ragflow_agent.knowledge.infrastructure.search import ElasticsearchSearchAdapter
from tests.fakes.minimum_rag import KeywordEmbedding


def _elasticsearch_url() -> str:
    value = os.environ.get("RAGFLOW_AGENT_TEST_ELASTICSEARCH_URL")
    if value is None:
        pytest.skip("RAGFLOW_AGENT_TEST_ELASTICSEARCH_URL is not configured")
    return value


@pytest.mark.asyncio
async def test_real_channels_enforce_role_user_scope_status_and_metadata() -> None:
    suffix = uuid4().hex
    embedding = KeywordEmbedding(dimensions=16)
    index_name = f"ragflow-agent-phase06-{suffix}"
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
        request_id=f"request-{suffix}",
    )
    role_reader = AuthorizationContext(
        tenant_id=owner.tenant_id,
        actor_id="reader-a",
        request_id=f"reader-{suffix}",
        roles=("maintenance",),
    )
    version = IndexVersion(
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

    def record(chunk_id: str, *, deleted: bool = False) -> IndexRecord:
        content = f"controller reset maintenance {chunk_id}"
        return IndexRecord(
            index_version_id=version.id,
            tenant_id=owner.tenant_id,
            knowledge_base_id=version.knowledge_base_id,
            owner_id=owner.actor_id,
            visibility=Visibility.PRIVATE,
            allowed_roles=("maintenance",),
            document_enabled=True,
            document_deleted=deleted,
            document_id=f"doc-{chunk_id}",
            document_version_id=f"version-{chunk_id}",
            chunk_id=chunk_id,
            content=content,
            media_type="text/markdown",
            created_at=datetime.now(UTC),
            embedding=embedding.vector(content),
            metadata=ChunkMetadata(language="en", page_start=1, page_end=1),
        )

    query = RetrievalQuery(
        tenant_id=owner.tenant_id,
        text="controller reset",
        knowledge_base_ids=(version.knowledge_base_id,),
        index_version_ids=(version.id,),
        filters=(
            MetadataFilter(
                field=MetadataField.LANGUAGE,
                operator=FilterOperator.EQUALS,
                value="en",
            ),
        ),
        top_k=10,
        top_n=3,
        trace_id=f"trace-{suffix}",
    )
    try:
        await adapter.ensure_index()
        await adapter.upsert(owner, version, (record("allowed"), record("deleted", deleted=True)))
        await adapter.activate(owner, version)

        text_candidates = await adapter.retrieve_full_text(role_reader, query)
        vector_candidates = await adapter.retrieve_vector(role_reader, query)
        denied = await adapter.retrieve_full_text(
            role_reader.model_copy(update={"roles": ()}), query
        )

        assert [item.chunk_id for item in text_candidates] == ["allowed"]
        assert [item.chunk_id for item in vector_candidates] == ["allowed"]
        assert text_candidates[0].score.full_text_rank == 1
        assert vector_candidates[0].score.vector_rank == 1
        assert denied == ()
    finally:
        await client.indices.delete(index=index_name, ignore_unavailable=True)
        await adapter.close()
