"""Candidate cleaning and deterministic final selection."""

from __future__ import annotations

from dataclasses import dataclass

from ragflow_agent.knowledge.domain.retrieval import RetrievalCandidate


@dataclass(frozen=True, slots=True)
class CleanResult:
    candidates: tuple[RetrievalCandidate, ...]
    excluded: tuple[tuple[RetrievalCandidate, str], ...]


def clean_candidates(
    candidates: tuple[RetrievalCandidate, ...],
    *,
    threshold: float,
    per_document_limit: int,
    final_top_k: int,
) -> CleanResult:
    """Apply soft relevance and diversity limits without touching hard scope."""

    kept: list[RetrievalCandidate] = []
    excluded: list[tuple[RetrievalCandidate, str]] = []
    document_counts: dict[str, int] = {}
    seen: set[str] = set()
    for candidate in candidates:
        if candidate.chunk_id in seen:
            excluded.append((candidate, "duplicate_chunk"))
            continue
        seen.add(candidate.chunk_id)
        if candidate.score.final_score < threshold:
            excluded.append((candidate, "below_threshold"))
            continue
        count = document_counts.get(candidate.document_id, 0)
        if count >= per_document_limit:
            excluded.append((candidate, "per_document_limit"))
            continue
        document_counts[candidate.document_id] = count + 1
        rank = len(kept) + 1
        kept.append(
            candidate.model_copy(
                update={"score": candidate.score.model_copy(update={"final_rank": rank})}
            )
        )
        if len(kept) >= final_top_k:
            break
    return CleanResult(candidates=tuple(kept), excluded=tuple(excluded))
