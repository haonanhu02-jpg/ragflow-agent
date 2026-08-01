"""Deterministic answer, refusal, groundedness, and citation scoring."""

from pydantic import BaseModel, ConfigDict, Field

from ragflow_agent.evaluation.metrics import citation_precision_recall


class AnswerScore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    correctness: float = Field(ge=0, le=1)
    faithfulness: float = Field(ge=0, le=1)
    refusal_correct: bool
    citation_precision: float = Field(ge=0, le=1)
    citation_recall: float = Field(ge=0, le=1)


def score_answer(
    *,
    expected_facts: frozenset[str],
    stated_facts: frozenset[str],
    supported_facts: frozenset[str],
    expected_citations: frozenset[str],
    predicted_citations: frozenset[str],
    should_refuse: bool,
    refused: bool,
) -> AnswerScore:
    correctness = len(stated_facts & expected_facts) / max(1, len(expected_facts))
    faithfulness = len(stated_facts & supported_facts) / max(1, len(stated_facts))
    citation_precision, citation_recall = citation_precision_recall(
        predicted_citations, expected_citations
    )
    return AnswerScore(
        correctness=correctness,
        faithfulness=faithfulness,
        refusal_correct=should_refuse == refused,
        citation_precision=citation_precision,
        citation_recall=citation_recall,
    )
