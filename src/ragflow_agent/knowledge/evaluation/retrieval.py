"""Small deterministic Recall, reciprocal-rank, and NDCG baseline."""

from __future__ import annotations

import math

from pydantic import Field

from ragflow_agent.knowledge.domain.base import KnowledgeModel


class RetrievalMetrics(KnowledgeModel):
    """Per-query metrics used by Phase 06 ablation tests."""

    recall_at_k: float = Field(ge=0, le=1)
    reciprocal_rank: float = Field(ge=0, le=1)
    ndcg_at_k: float = Field(ge=0, le=1)


def evaluate_ranking(
    ranked_chunk_ids: tuple[str, ...],
    relevant_chunk_ids: frozenset[str],
    *,
    k: int,
) -> RetrievalMetrics:
    """Evaluate binary relevance without importing a heavyweight framework."""
    if k < 1:
        raise ValueError("evaluation k must be positive")
    selected = ranked_chunk_ids[:k]
    hits = sum(chunk_id in relevant_chunk_ids for chunk_id in selected)
    recall = hits / len(relevant_chunk_ids) if relevant_chunk_ids else 1.0
    first_rank = next(
        (rank for rank, chunk_id in enumerate(selected, start=1) if chunk_id in relevant_chunk_ids),
        None,
    )
    reciprocal_rank = 1 / first_rank if first_rank is not None else 0.0
    dcg = sum(
        1 / math.log2(rank + 1)
        for rank, chunk_id in enumerate(selected, start=1)
        if chunk_id in relevant_chunk_ids
    )
    ideal_hits = min(len(relevant_chunk_ids), k)
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    ndcg = dcg / ideal if ideal else 1.0
    return RetrievalMetrics(
        recall_at_k=recall,
        reciprocal_rank=reciprocal_rank,
        ndcg_at_k=ndcg,
    )
