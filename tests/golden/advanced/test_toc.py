from datetime import UTC, datetime

from ragflow_agent.knowledge.advanced.enrichment.toc import TocBuilder
from ragflow_agent.knowledge.domain.chunk import BlockKind, ParsedBlock, ParsedDocument


def test_toc_is_deterministic_ordered_and_page_block_chunk_bound() -> None:
    document = ParsedDocument(
        id="parsed-a",
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        document_id="doc-a",
        document_version_id="ver-a",
        parser_name="fake",
        parser_version="1",
        parsed_at=datetime(2026, 8, 1, tzinfo=UTC),
        blocks=(
            ParsedBlock(
                id="heading-1",
                kind=BlockKind.HEADING,
                order=0,
                text="Safety",
                page_number=1,
                heading_path=("Safety",),
            ),
            ParsedBlock(id="body-1", kind=BlockKind.TEXT, order=1, text="Wear PPE."),
            ParsedBlock(
                id="heading-2",
                kind=BlockKind.HEADING,
                order=2,
                text="Brake",
                page_number=2,
                heading_path=("Safety", "Brake"),
            ),
        ),
    )
    tree = TocBuilder().build(document, chunk_by_block={"heading-1": ("chunk-1",)})
    assert [(item.title, item.level, item.page_number) for item in tree.nodes] == [
        ("Safety", 1, 1),
        ("Brake", 2, 2),
    ]
    assert tree.nodes[0].block_id == "heading-1"
    assert tree.nodes[0].chunk_ids == ("chunk-1",)
