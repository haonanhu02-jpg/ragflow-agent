"""Bounded Reranker execution with explicit RRF fallback."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.retrieval import RetrievalCandidate, RetrievalQuery
from ragflow_agent.knowledge.ports.search import RerankerPort, RerankRequest


@dataclass(frozen=True, slots=True)
class RerankOutcome:
    candidates: tuple[RetrievalCandidate, ...]
    applied: bool
    fallback_reason: str | None = None


async def rerank_with_fallback(
    reranker: RerankerPort,
    context: AuthorizationContext,
    query: RetrievalQuery,
    candidates: tuple[RetrievalCandidate, ...],
    *,
    timeout_seconds: float,
) -> RerankOutcome:
    if not candidates:
        return RerankOutcome(candidates=(), applied=False)
    try:
        reranked = await asyncio.wait_for(
            reranker.rerank(context, RerankRequest(query=query, candidates=candidates)),
            timeout=timeout_seconds,
        )
        expected = {candidate.chunk_id for candidate in candidates}
        actual = {candidate.chunk_id for candidate in reranked}
        if expected != actual or len(reranked) != len(candidates):
            raise ValueError("reranker changed candidate identity")
        normalized = tuple(
            candidate.model_copy(
                update={
                    "score": candidate.score.model_copy(
                        update={
                            "rerank_rank": rank,
                            "final_score": (
                                candidate.score.rerank_score
                                if candidate.score.rerank_score is not None
                                else candidate.score.final_score
                            ),
                        }
                    )
                }
            )
            for rank, candidate in enumerate(reranked, start=1)
        )
        return RerankOutcome(candidates=normalized, applied=True)
    except TimeoutError:
        return RerankOutcome(
            candidates=candidates,
            applied=False,
            fallback_reason="reranker_timeout",
        )
    except Exception as error:
        return RerankOutcome(
            candidates=candidates,
            applied=False,
            fallback_reason=f"reranker_error:{type(error).__name__}",
        )
