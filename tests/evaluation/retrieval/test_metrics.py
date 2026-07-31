"""Versioned Phase 06 retrieval quality and ablation baseline."""

import pytest

from ragflow_agent.knowledge.evaluation import evaluate_ranking


def test_hybrid_ranking_improves_over_single_channel_fixture() -> None:
    relevant = frozenset({"alarm-code", "semantic-procedure"})
    full_text = evaluate_ranking(("alarm-code", "noise-a", "noise-b"), relevant, k=3)
    vector = evaluate_ranking(("semantic-procedure", "noise-b", "noise-a"), relevant, k=3)
    hybrid = evaluate_ranking(("alarm-code", "semantic-procedure", "noise-a"), relevant, k=3)

    assert hybrid.recall_at_k == 1
    assert hybrid.recall_at_k > full_text.recall_at_k
    assert hybrid.recall_at_k > vector.recall_at_k
    assert hybrid.ndcg_at_k > full_text.ndcg_at_k


def test_empty_relevance_and_invalid_k_have_explicit_semantics() -> None:
    assert evaluate_ranking((), frozenset(), k=3).recall_at_k == 1
    with pytest.raises(ValueError, match="positive"):
        evaluate_ranking((), frozenset(), k=0)
