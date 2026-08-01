from ragflow_agent.knowledge.advanced.enrichment.summaries import SummaryBuilder, SummaryLevel
from tests.fakes.advanced import NOW, make_chunk


def test_chunk_document_and_hierarchical_summaries_keep_sources() -> None:
    chunks = (
        make_chunk("chunk-1", "alpha beta gamma", sequence=0),
        make_chunk("chunk-2", "delta epsilon zeta", sequence=1),
    )
    builder = SummaryBuilder()
    for level in SummaryLevel:
        artifact = builder.build(
            chunks,
            level=level,
            build_version="build-1",
            created_at=NOW,
            max_tokens=4,
        )
        assert artifact.source_chunk_ids == ("chunk-1", "chunk-2")
        assert len(artifact.text.split()) <= 5
