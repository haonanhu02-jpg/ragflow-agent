from ragflow_agent.knowledge.advanced.enrichment.questions import QuestionGenerator
from tests.fakes.advanced import NOW, make_chunk


def test_questions_are_bounded_and_source_bound() -> None:
    chunk = make_chunk("chunk-1", "Brake pressure dropped. Inspect valve A. Reset after repair.")
    artifact = QuestionGenerator().generate(chunk, build_version="build-1", created_at=NOW, limit=2)
    assert len(artifact.text.splitlines()) == 2
    assert artifact.source_chunk_ids == ("chunk-1",)
