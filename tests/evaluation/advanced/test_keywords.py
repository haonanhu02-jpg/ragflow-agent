from ragflow_agent.knowledge.advanced.enrichment.keywords import KeywordExtractor
from tests.fakes.advanced import NOW, make_chunk


def test_keywords_are_bounded_deduplicated_and_source_bound() -> None:
    chunk = make_chunk("chunk-1", "brake alarm brake maintenance maintenance rail")
    artifact = KeywordExtractor().extract(chunk, build_version="build-1", created_at=NOW, limit=3)
    assert artifact.text.splitlines() == ["brake", "maintenance", "alarm"]
    assert artifact.source_chunk_ids == (chunk.id,)
