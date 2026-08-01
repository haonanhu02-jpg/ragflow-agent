from ragflow_agent.evaluation.answers import score_answer


def test_answer_and_citation_metrics_cannot_hide_missing_citation() -> None:
    score = score_answer(
        expected_facts=frozenset({"a", "b"}),
        stated_facts=frozenset({"a", "hallucination"}),
        supported_facts=frozenset({"a"}),
        expected_citations=frozenset({"c1", "c2"}),
        predicted_citations=frozenset({"c1", "wrong"}),
        should_refuse=False,
        refused=False,
    )
    assert score.correctness == 0.5
    assert score.faithfulness == 0.5
    assert score.citation_precision == 0.5
    assert score.citation_recall == 0.5
