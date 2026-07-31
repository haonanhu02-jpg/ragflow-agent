"""Online pipeline, finite fallback, error semantics, and trace security tests."""

from datetime import UTC, datetime, timedelta

import pytest
from tests.fakes.knowledge import FixedClock
from tests.fakes.retrieval import (
    FakeReranker,
    FakeSearchChannels,
    MemoryRetrievalTraceStore,
    StubQueryTransformProvider,
    retrieval_candidate,
)

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
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.errors import (
    KnowledgeAuthorizationError,
    KnowledgeRetrievalError,
)
from ragflow_agent.knowledge.domain.retrieval import (
    FilterGroupOperator,
    FilterOperator,
    MetadataField,
    MetadataFilter,
    MetadataFilterGroup,
    RetrievalEmptyReason,
    RetrievalQuery,
    RetrievalStage,
    RetrievalTraceStatus,
)

NOW = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)


def _context(*, tenant: str = "tenant-a", roles: tuple[str, ...] = ()) -> AuthorizationContext:
    return AuthorizationContext(
        tenant_id=tenant,
        actor_id="owner-a",
        request_id="request-a",
        roles=roles,
    )


def _query(**updates: object) -> RetrievalQuery:
    values: dict[str, object] = {
        "tenant_id": "tenant-a",
        "text": "reset controller",
        "knowledge_base_ids": ("kb-a",),
        "index_version_ids": ("index-a",),
        "top_k": 2,
        "top_n": 2,
        "trace_id": "trace-a",
        "request_id": "request-a",
    }
    values.update(updates)
    return RetrievalQuery.model_validate(values)


def _service(
    search: FakeSearchChannels,
    reranker: FakeReranker,
    store: MemoryRetrievalTraceStore,
    metrics: LoggingRetrievalTraceMetrics,
    *,
    max_fallback_attempts: int = 4,
    variants: QueryVariantBuilder | None = None,
) -> OnlineRetrievalService:
    return OnlineRetrievalService(
        search=search,
        reranker=reranker,
        variants=variants
        or QueryVariantBuilder(
            StubQueryTransformProvider(),
            model_id="deepseek-chat",
            rewrite_enabled=False,
            translation_enabled=False,
            keyword_expansion_enabled=False,
            max_variants=4,
        ),
        preprocessor=QueryPreprocessor(max_characters=1000),
        trace_recorder=SafeRetrievalTraceRecorder(store, metrics),
        clock=FixedClock(NOW),
        profile=OnlineRetrievalProfile(
            rrf_k=60,
            candidate_top_k=8,
            rerank_candidate_count=4,
            final_top_k=2,
            fusion_threshold=0,
            fallback_threshold_floor=0,
            max_fallback_attempts=max_fallback_attempts,
            fallback_candidate_multiplier=2,
            per_document_limit=2,
            reranker_timeout_seconds=0.1,
            trace_retention_days=30,
            provider_ids=("embedding:fake", "reranker:fake"),
        ),
    )


@pytest.mark.asyncio
async def test_scores_ranks_reranker_and_content_minimized_trace_are_recorded() -> None:
    search = FakeSearchChannels(
        full_text=(
            retrieval_candidate("a", full_text_score=10),
            retrieval_candidate("b", full_text_score=8),
        ),
        vector=(
            retrieval_candidate("b", vector_score=0.9),
            retrieval_candidate("c", vector_score=0.8),
        ),
    )
    store = MemoryRetrievalTraceStore()
    metrics = LoggingRetrievalTraceMetrics()
    result = await _service(
        search,
        FakeReranker({"a": 0.1, "b": 0.9, "c": 0.5}),
        store,
        metrics,
    ).retrieve(_context(), _query())

    assert [candidate.chunk_id for candidate in result.candidates] == ["b", "c"]
    assert result.candidates[0].score.full_text_rank == 2
    assert result.candidates[0].score.vector_rank == 1
    assert result.candidates[0].score.rerank_score == 0.9
    assert result.trace.status is RetrievalTraceStatus.SUCCESS
    persisted = store.traces[("tenant-a", "trace-a")]
    assert persisted.original_query is None
    assert persisted.query_digest
    assert persisted.candidates[0].chunk_id
    assert persisted.candidates[0].rerank_rank is not None
    assert persisted.candidates[0].rerank_score is not None
    assert persisted.candidates[0].final_rank is not None
    assert "evidence" not in persisted.model_dump_json()


@pytest.mark.asyncio
async def test_query_variant_kinds_are_traced_without_persisting_variant_text() -> None:
    variants = QueryVariantBuilder(
        StubQueryTransformProvider(
            {
                "rewrite": ("rewritten query",),
                "translate": ("translated query",),
                "keywords": ("expanded query",),
            }
        ),
        model_id="deepseek-chat",
        rewrite_enabled=True,
        translation_enabled=True,
        keyword_expansion_enabled=True,
        max_variants=6,
    )
    store = MemoryRetrievalTraceStore()
    result = await _service(
        FakeSearchChannels(full_text=(retrieval_candidate("a", full_text_score=5),)),
        FakeReranker({"a": 0.8}),
        store,
        LoggingRetrievalTraceMetrics(),
        variants=variants,
    ).retrieve(
        _context(),
        _query(history=("previous turn",), target_languages=("zh",)),
    )

    stages = {event.stage for event in result.trace.events}
    assert {RetrievalStage.REWRITE, RetrievalStage.TRANSLATE, RetrievalStage.EXPAND} <= stages
    persisted = store.traces[("tenant-a", "trace-a")]
    serialized = persisted.model_dump_json()
    assert len(persisted.query_variant_digests) >= 4
    assert all(":" in digest for digest in persisted.query_variant_digests)
    assert "rewritten query" not in serialized
    assert "translated query" not in serialized
    assert "expanded query" not in serialized


@pytest.mark.asyncio
async def test_empty_result_uses_finite_fallback_without_relaxing_hard_or_user_filters() -> None:
    user_filter = MetadataFilterGroup(
        operator=FilterGroupOperator.AND,
        items=(
            MetadataFilter(
                field=MetadataField.LANGUAGE,
                operator=FilterOperator.EQUALS,
                value="zh",
            ),
        ),
    )
    inferred = MetadataFilterGroup(
        items=(
            MetadataFilter(
                field=MetadataField.CONTAINS_TABLE,
                operator=FilterOperator.EQUALS,
                value=True,
            ),
        )
    )
    search = FakeSearchChannels()
    store = MemoryRetrievalTraceStore()
    result = await _service(
        search,
        FakeReranker(),
        store,
        LoggingRetrievalTraceMetrics(),
    ).retrieve(
        _context(roles=("maintenance",)),
        _query(filter_expression=user_filter, inferred_filter_expression=inferred),
    )

    assert result.empty_reason is RetrievalEmptyReason.NO_EVIDENCE
    assert len(result.trace.fallback_steps) == 4
    assert len(search.full_text_queries) + len(search.vector_queries) <= 8
    for query in (*search.full_text_queries, *search.vector_queries):
        assert query.tenant_id == "tenant-a"
        assert query.knowledge_base_ids == ("kb-a",)
        assert query.index_version_ids == ("index-a",)
        assert query.filter_expression == user_filter
    assert any(query.inferred_filter_expression is None for query in search.full_text_queries)


@pytest.mark.asyncio
async def test_expanded_candidate_fallback_recovers_evidence_and_is_traced() -> None:
    search = FakeSearchChannels(
        full_text=(retrieval_candidate("a", full_text_score=5),),
        minimum_top_k=4,
    )
    result = await _service(
        search,
        FakeReranker(error=RuntimeError("offline")),
        MemoryRetrievalTraceStore(),
        LoggingRetrievalTraceMetrics(),
    ).retrieve(_context(), _query())

    assert result.candidates[0].chunk_id == "a"
    assert result.trace.fallback_steps[0].mode == "expanded_hybrid"
    assert result.trace.fallback_steps[0].reason == "recovered_evidence"


@pytest.mark.asyncio
async def test_backend_failure_is_not_reported_as_empty_result() -> None:
    service = _service(
        FakeSearchChannels(fail_full_text=True, fail_vector=True),
        FakeReranker(),
        MemoryRetrievalTraceStore(),
        LoggingRetrievalTraceMetrics(),
    )

    with pytest.raises(KnowledgeRetrievalError):
        await service.retrieve(_context(), _query())


@pytest.mark.asyncio
async def test_trace_write_failure_does_not_break_retrieval_and_is_observable() -> None:
    store = MemoryRetrievalTraceStore()
    store.error = RuntimeError("database offline")
    metrics = LoggingRetrievalTraceMetrics()
    result = await _service(
        FakeSearchChannels(full_text=(retrieval_candidate("a", full_text_score=5),)),
        FakeReranker({"a": 0.8}),
        store,
        metrics,
    ).retrieve(_context(), _query())

    assert result.candidates
    assert metrics.write_failure_count == 1


@pytest.mark.asyncio
async def test_trace_access_is_tenant_and_role_scoped_and_cleanup_is_executable() -> None:
    store = MemoryRetrievalTraceStore()
    service = _service(
        FakeSearchChannels(full_text=(retrieval_candidate("a", full_text_score=5),)),
        FakeReranker({"a": 0.8}),
        store,
        LoggingRetrievalTraceMetrics(),
    )
    await service.retrieve(_context(), _query())
    access = RetrievalTraceAccessService(
        store,
        detailed_roles=("retrieval_debug", "operations"),
    )

    with pytest.raises(KnowledgeAuthorizationError):
        await access.get_detailed(_context(), "trace-a")
    assert (
        await access.get_detailed(
            _context(tenant="tenant-b", roles=("retrieval_debug",)), "trace-a"
        )
        is None
    )
    trace = await access.get_detailed(_context(roles=("retrieval_debug",)), "trace-a")
    assert trace is not None
    deleted = await RetrievalTraceMaintenanceService(store).cleanup_expired(
        before=NOW + timedelta(days=31)
    )
    assert deleted == 1
    assert store.traces == {}
