"""Deterministic reciprocal-rank fusion with complete rank provenance."""

from __future__ import annotations

from dataclasses import dataclass

from ragflow_agent.knowledge.domain.retrieval import RetrievalCandidate


@dataclass(slots=True)
class _FusionEntry:
    candidate: RetrievalCandidate
    rrf: float = 0.0
    full_text_rank: int | None = None
    full_text_score: float | None = None
    vector_rank: int | None = None
    vector_score: float | None = None


def reciprocal_rank_fusion(
    full_text: tuple[RetrievalCandidate, ...],
    vector: tuple[RetrievalCandidate, ...],
    *,
    k: int,
) -> tuple[RetrievalCandidate, ...]:
    """Deduplicate by chunk ID and retain raw scores/ranks from both channels."""

    entries: dict[str, _FusionEntry] = {}
    for channel, candidates in (("full_text", full_text), ("vector", vector)):
        for rank, candidate in enumerate(candidates, start=1):
            entry = entries.setdefault(candidate.chunk_id, _FusionEntry(candidate=candidate))
            entry.rrf += 1.0 / (k + rank)
            if channel == "full_text":
                entry.full_text_rank = rank
                entry.full_text_score = candidate.score.full_text_score
            else:
                entry.vector_rank = rank
                entry.vector_score = candidate.score.vector_score
    ordered = sorted(
        entries.values(),
        key=lambda item: (-item.rrf, item.candidate.chunk_id),
    )
    fused: list[RetrievalCandidate] = []
    for fusion_rank, entry in enumerate(ordered, start=1):
        candidate = entry.candidate
        score = candidate.score.model_copy(
            update={
                "final_score": entry.rrf,
                "full_text_score": entry.full_text_score,
                "vector_score": entry.vector_score,
                "fusion_score": entry.rrf,
                "full_text_rank": entry.full_text_rank,
                "vector_rank": entry.vector_rank,
                "fusion_rank": fusion_rank,
            }
        )
        fused.append(candidate.model_copy(update={"score": score}))
    return tuple(fused)
