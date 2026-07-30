"""Retrieval, citation, trace, and index schema tests."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ragflow_agent.knowledge.domain.authorization import Visibility
from ragflow_agent.knowledge.domain.chunk import ChunkMetadata
from ragflow_agent.knowledge.domain.retrieval import (
    Citation,
    EmbeddingMetadata,
    FilterOperator,
    IndexRecord,
    IndexVersion,
    IndexVersionStatus,
    MetadataField,
    MetadataFilter,
    RetrievalCandidate,
    RetrievalEmptyReason,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStage,
    RetrievalTrace,
    RetrievalTraceEvent,
    ScoreBreakdown,
)

NOW = datetime(2026, 7, 30, 8, 0, tzinfo=UTC)


def _query(**overrides: object) -> RetrievalQuery:
    values: dict[str, object] = {
        "tenant_id": "tenant-a",
        "text": "traction power alarm",
        "knowledge_base_ids": ("kb-1",),
        "top_k": 20,
        "top_n": 5,
        "trace_id": "trace-1",
    }
    values.update(overrides)
    return RetrievalQuery.model_validate(values)


def _trace(**overrides: object) -> RetrievalTrace:
    values: dict[str, object] = {
        "trace_id": "trace-1",
        "tenant_id": "tenant-a",
        "original_query": "traction power alarm",
        "authorization_applied": True,
        "events": (
            RetrievalTraceEvent(
                sequence=0,
                stage=RetrievalStage.AUTHORIZATION,
                elapsed_ms=1,
                candidate_count=1,
            ),
        ),
    }
    values.update(overrides)
    return RetrievalTrace.model_validate(values)


def _candidate(**overrides: object) -> RetrievalCandidate:
    scope: dict[str, object] = {
        "tenant_id": "tenant-a",
        "knowledge_base_id": "kb-1",
        "document_id": "document-1",
        "document_version_id": "version-1",
        "chunk_id": "chunk-1",
    }
    scope.update(overrides)
    citation = Citation(
        tenant_id=str(scope["tenant_id"]),
        knowledge_base_id=str(scope["knowledge_base_id"]),
        document_id=str(scope["document_id"]),
        document_version_id=str(scope["document_version_id"]),
        chunk_id=str(scope["chunk_id"]),
        quote="Open the breaker before inspection.",
        page_number=4,
    )
    return RetrievalCandidate.model_validate(
        {
            **scope,
            "content": "Open the breaker before inspection.",
            "score": ScoreBreakdown(final_score=0.9, vector_score=0.8),
            "citation": citation,
        }
    )


def test_query_has_portable_filters_and_top_n_not_above_top_k() -> None:
    query = _query(
        filters=(
            MetadataFilter(
                field=MetadataField.LANGUAGE,
                operator=FilterOperator.IN,
                value=("zh", "en"),
            ),
        )
    )

    assert query.filters[0].operator is FilterOperator.IN
    with pytest.raises(ValidationError):
        _query(top_k=5, top_n=6)
    with pytest.raises(ValidationError):
        MetadataFilter(
            field=MetadataField.LANGUAGE,
            operator=FilterOperator.IN,
            value="zh",
        )


def test_candidate_and_citation_scope_cannot_diverge() -> None:
    with pytest.raises(ValidationError):
        RetrievalCandidate(
            tenant_id="tenant-a",
            knowledge_base_id="kb-1",
            document_id="document-1",
            document_version_id="version-1",
            chunk_id="chunk-1",
            content="content",
            score=ScoreBreakdown(final_score=1),
            citation=Citation(
                tenant_id="tenant-b",
                knowledge_base_id="kb-1",
                document_id="document-1",
                document_version_id="version-1",
                chunk_id="chunk-1",
                quote="content",
            ),
        )


def test_result_rejects_cross_tenant_or_unrequested_candidates() -> None:
    with pytest.raises(ValidationError):
        RetrievalResult(
            query=_query(),
            candidates=(_candidate(tenant_id="tenant-b"),),
            trace=_trace(),
        )
    with pytest.raises(ValidationError):
        RetrievalResult(
            query=_query(),
            candidates=(_candidate(knowledge_base_id="kb-2"),),
            trace=_trace(),
        )


def test_empty_and_non_empty_results_have_explicit_semantics() -> None:
    result = RetrievalResult(
        query=_query(),
        candidates=(),
        trace=_trace(),
        empty_reason=RetrievalEmptyReason.NO_MATCH,
    )
    assert result.empty_reason is RetrievalEmptyReason.NO_MATCH

    non_empty = RetrievalResult(
        query=_query(),
        candidates=(_candidate(),),
        trace=_trace(),
    )
    assert non_empty.citations[0].chunk_id == "chunk-1"

    with pytest.raises(ValidationError):
        RetrievalResult(query=_query(), candidates=(), trace=_trace())


def test_trace_sequence_and_query_identity_are_stable() -> None:
    with pytest.raises(ValidationError):
        _trace(
            events=(
                RetrievalTraceEvent(
                    sequence=1,
                    stage=RetrievalStage.VECTOR,
                    elapsed_ms=1,
                    candidate_count=1,
                ),
                RetrievalTraceEvent(
                    sequence=0,
                    stage=RetrievalStage.SELECT,
                    elapsed_ms=1,
                    candidate_count=1,
                ),
            )
        )
    with pytest.raises(ValidationError):
        RetrievalResult(
            query=_query(),
            candidates=(_candidate(),),
            trace=_trace(trace_id="trace-other"),
        )


def test_index_contract_binds_embedding_and_record_to_version_scope() -> None:
    version = IndexVersion(
        id="index-v1",
        tenant_id="tenant-a",
        knowledge_base_id="kb-1",
        embedding=EmbeddingMetadata(
            model_id="embedding-1",
            dimensions=3,
            normalized=True,
        ),
        status=IndexVersionStatus.BUILDING,
        created_at=NOW,
    )
    record = IndexRecord(
        index_version_id=version.id,
        tenant_id=version.tenant_id,
        knowledge_base_id=version.knowledge_base_id,
        owner_id="owner-a",
        visibility=Visibility.PRIVATE,
        document_id="document-1",
        document_version_id="version-1",
        chunk_id="chunk-1",
        content="content",
        media_type="text/plain",
        created_at=NOW,
        embedding=(0.1, 0.2, 0.3),
        metadata=ChunkMetadata(page_start=1, page_end=1),
    )

    assert record.index_version_id == version.id
    assert len(record.embedding) == version.embedding.dimensions
