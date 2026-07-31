"""Finite empty-result fallback steps that never mutate hard filters."""

from __future__ import annotations

from dataclasses import dataclass

from ragflow_agent.knowledge.domain.retrieval import RetrievalQuery


@dataclass(frozen=True, slots=True)
class RetrievalAttempt:
    number: int
    mode: str
    query: RetrievalQuery
    threshold: float
    inferred_filter_removed: bool


def fallback_attempts(
    query: RetrievalQuery,
    *,
    normal_threshold: float,
    threshold_floor: float,
    candidate_multiplier: int,
    maximum_attempts: int,
) -> tuple[RetrievalAttempt, ...]:
    """Build a finite sequence while preserving tenant/scope/user filters verbatim."""

    expanded_top_k = min(10_000, query.top_k * candidate_multiplier)
    lowered = max(threshold_floor, (normal_threshold + threshold_floor) / 2)
    definitions = (
        ("expanded_hybrid", expanded_top_k, lowered, False),
        ("soft_filter_removed", expanded_top_k, threshold_floor, True),
        ("full_text_only", expanded_top_k, threshold_floor, True),
        ("vector_only", expanded_top_k, threshold_floor, True),
    )
    attempts: list[RetrievalAttempt] = []
    for number, (mode, top_k, threshold, remove_inferred) in enumerate(
        definitions[:maximum_attempts], start=1
    ):
        attempts.append(
            RetrievalAttempt(
                number=number,
                mode=mode,
                query=query.model_copy(
                    update={
                        "top_k": top_k,
                        "inferred_filter_expression": (
                            None if remove_inferred else query.inferred_filter_expression
                        ),
                    }
                ),
                threshold=threshold,
                inferred_filter_removed=remove_inferred,
            )
        )
    return tuple(attempts)
