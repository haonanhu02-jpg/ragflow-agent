"""Deterministic RRF, deduplication, rerank, and fallback tests."""

from datetime import UTC, datetime

import pytest
from tests.fakes.retrieval import FakeReranker, retrieval_candidate

from ragflow_agent.knowledge.application.query.fusion import reciprocal_rank_fusion
from ragflow_agent.knowledge.application.query.rerank import rerank_with_fallback
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.retrieval import RetrievalQuery

NOW = datetime(2026, 7, 31, tzinfo=UTC)


def _query() -> RetrievalQuery:
    return RetrievalQuery(
        tenant_id="tenant-a",
        text="reset controller",
        knowledge_base_ids=("kb-a",),
        top_k=10,
        top_n=3,
        trace_id="trace-a",
        request_id="request-a",
    )


def test_rrf_deduplicates_and_preserves_channel_scores_and_ranks() -> None:
    text = (
        retrieval_candidate("a", full_text_score=12),
        retrieval_candidate("b", full_text_score=8),
    )
    vector = (
        retrieval_candidate("b", vector_score=0.9),
        retrieval_candidate("c", vector_score=0.8),
    )

    fused = reciprocal_rank_fusion(text, vector, k=60)

    assert [candidate.chunk_id for candidate in fused] == ["b", "a", "c"]
    assert fused[0].score.full_text_rank == 2
    assert fused[0].score.vector_rank == 1
    assert fused[0].score.full_text_score == 8
    assert fused[0].score.vector_score == 0.9
    assert fused[0].score.fusion_rank == 1


@pytest.mark.asyncio
async def test_reranker_becomes_primary_order_and_error_falls_back_to_rrf() -> None:
    context = AuthorizationContext(
        tenant_id="tenant-a",
        actor_id="owner-a",
        request_id="request-a",
    )
    candidates = reciprocal_rank_fusion(
        (
            retrieval_candidate("a", full_text_score=10),
            retrieval_candidate("b", full_text_score=9),
        ),
        (),
        k=60,
    )
    success = await rerank_with_fallback(
        FakeReranker({"a": 0.1, "b": 0.9}),
        context,
        _query(),
        candidates,
        timeout_seconds=1,
    )
    failed = await rerank_with_fallback(
        FakeReranker(error=RuntimeError("offline")),
        context,
        _query(),
        candidates,
        timeout_seconds=1,
    )

    assert success.applied is True
    assert [candidate.chunk_id for candidate in success.candidates] == ["b", "a"]
    assert success.candidates[0].score.final_score == 0.9
    assert failed.applied is False
    assert failed.candidates == candidates
    assert failed.fallback_reason == "reranker_error:RuntimeError"


@pytest.mark.asyncio
async def test_reranker_timeout_falls_back_without_failing_request() -> None:
    context = AuthorizationContext(
        tenant_id="tenant-a",
        actor_id="owner-a",
        request_id="request-a",
    )
    candidates = reciprocal_rank_fusion((retrieval_candidate("a", full_text_score=10),), (), k=60)
    outcome = await rerank_with_fallback(
        FakeReranker(delay_seconds=0.05),
        context,
        _query(),
        candidates,
        timeout_seconds=0.001,
    )

    assert outcome.applied is False
    assert outcome.fallback_reason == "reranker_timeout"
