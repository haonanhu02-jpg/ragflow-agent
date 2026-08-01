"""Hand-checkable information-retrieval and citation metrics."""

from math import log2


def precision_at_k(retrieved: tuple[str, ...], relevant: frozenset[str], k: int) -> float:
    if k < 1:
        raise ValueError("k must be positive")
    selected = retrieved[:k]
    return sum(item in relevant for item in selected) / k


def recall_at_k(retrieved: tuple[str, ...], relevant: frozenset[str], k: int) -> float:
    if k < 1:
        raise ValueError("k must be positive")
    if not relevant:
        return 1.0 if not retrieved[:k] else 0.0
    return len(set(retrieved[:k]) & relevant) / len(relevant)


def mean_reciprocal_rank(
    results: tuple[tuple[str, ...], ...], qrels: tuple[frozenset[str], ...]
) -> float:
    if len(results) != len(qrels) or not results:
        raise ValueError("MRR requires aligned non-empty results and qrels")
    reciprocal = []
    for retrieved, relevant in zip(results, qrels, strict=True):
        rank = next((index for index, item in enumerate(retrieved, 1) if item in relevant), None)
        reciprocal.append(0.0 if rank is None else 1 / rank)
    return sum(reciprocal) / len(reciprocal)


def ndcg_at_k(retrieved: tuple[str, ...], relevance: dict[str, float], k: int) -> float:
    if k < 1 or any(value < 0 for value in relevance.values()):
        raise ValueError("NDCG requires positive k and non-negative relevance")
    dcg = sum(
        (2 ** relevance.get(item, 0) - 1) / log2(index + 1)
        for index, item in enumerate(retrieved[:k], 1)
    )
    ideal = sorted(relevance.values(), reverse=True)[:k]
    idcg = sum((2**value - 1) / log2(index + 1) for index, value in enumerate(ideal, 1))
    return 0.0 if idcg == 0 else dcg / idcg


def citation_precision_recall(
    predicted: frozenset[str], expected: frozenset[str]
) -> tuple[float, float]:
    precision = (
        1.0
        if not predicted and not expected
        else len(predicted & expected) / max(1, len(predicted))
    )
    recall = 1.0 if not expected else len(predicted & expected) / len(expected)
    return precision, recall
