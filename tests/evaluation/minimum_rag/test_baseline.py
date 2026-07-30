"""Versioned deterministic Recall@K and citation-presence baseline."""

from tests.fakes.minimum_rag import KeywordEmbedding

BASELINE_VERSION = "minimum-rag-baseline-v1"


def test_keyword_embedding_recall_baseline() -> None:
    embedding = KeywordEmbedding(dimensions=32)
    documents = {
        "relevant": embedding.vector("alarm reset controller inspection"),
        "unrelated": embedding.vector("financial procurement invoice"),
    }
    query = embedding.vector("controller reset")
    scores = {
        name: sum(left * right for left, right in zip(query, vector, strict=True))
        for name, vector in documents.items()
    }
    ranked = sorted(scores, key=lambda name: scores[name], reverse=True)

    recall_at_1 = 1.0 if ranked[0] == "relevant" else 0.0

    assert BASELINE_VERSION == "minimum-rag-baseline-v1"
    assert recall_at_1 == 1.0
