from math import isclose

import pytest

from ragflow_agent.evaluation.metrics import (
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


def test_retrieval_metrics_match_hand_calculation() -> None:
    retrieved = ("noise", "relevant-a", "relevant-b")
    relevant = frozenset({"relevant-a", "relevant-b"})
    assert precision_at_k(retrieved, relevant, 2) == 0.5
    assert recall_at_k(retrieved, relevant, 2) == 0.5
    assert mean_reciprocal_rank((retrieved,), (relevant,)) == 0.5
    expected_ndcg = (1 / 1.584962500721156 + 1 / 2) / (1 + 1 / 1.584962500721156)
    assert isclose(ndcg_at_k(retrieved, {"relevant-a": 1, "relevant-b": 1}, 3), expected_ndcg)


def test_metrics_reject_invalid_shapes() -> None:
    with pytest.raises(ValueError):
        precision_at_k((), frozenset(), 0)
    with pytest.raises(ValueError):
        mean_reciprocal_rank((), ())
