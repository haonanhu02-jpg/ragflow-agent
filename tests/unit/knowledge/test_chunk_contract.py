"""ParsedDocument and ChunkRecord contract tests."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ragflow_agent.knowledge.domain.chunk import (
    CHUNK_ID_ALGORITHM,
    BlockKind,
    BoundingBox,
    ChunkMetadata,
    ChunkRecord,
    CoordinateSpace,
    ImageReference,
    ParsedBlock,
    ParsedDocument,
    TableMetadata,
    derive_chunk_id,
)

NOW = datetime(2026, 7, 30, 8, 0, tzinfo=UTC)


def _text_block(*, identifier: str = "block-1", order: int = 0) -> ParsedBlock:
    return ParsedBlock(
        id=identifier,
        kind=BlockKind.TEXT,
        order=order,
        text="Traction power procedure",
        page_number=1,
        bounding_box=BoundingBox(
            x0=0.1,
            y0=0.2,
            x1=0.9,
            y1=0.4,
            coordinate_space=CoordinateSpace.NORMALIZED,
        ),
        heading_path=("Maintenance",),
    )


def test_parsed_blocks_keep_typed_page_table_and_image_sources() -> None:
    table = ParsedBlock(
        id="table-1",
        kind=BlockKind.TABLE,
        order=0,
        text="alarm | action",
        page_number=2,
        table=TableMetadata(rows=2, columns=2, has_header=True),
    )
    image = ParsedBlock(
        id="image-1",
        kind=BlockKind.IMAGE,
        order=1,
        text="breaker diagram",
        page_number=3,
        image=ImageReference(
            object_key="tenant-a/images/image-1.png",
            media_type="image/png",
            width=640,
            height=480,
        ),
    )

    assert table.table is not None
    assert image.image is not None


def test_bounding_box_rejects_invalid_normalized_geometry() -> None:
    with pytest.raises(ValidationError):
        BoundingBox(
            x0=0,
            y0=0,
            x1=1.1,
            y1=1,
            coordinate_space=CoordinateSpace.NORMALIZED,
        )


def test_block_kind_requires_matching_typed_payload() -> None:
    with pytest.raises(ValidationError):
        ParsedBlock(id="table-1", kind=BlockKind.TABLE, order=0, text="data")
    with pytest.raises(ValidationError):
        ParsedBlock(id="image-1", kind=BlockKind.IMAGE, order=0)


def test_parsed_document_rejects_duplicate_or_unsorted_blocks() -> None:
    base = {
        "id": "parsed-1",
        "tenant_id": "tenant-a",
        "knowledge_base_id": "kb-1",
        "document_id": "document-1",
        "document_version_id": "version-1",
        "parser_name": "fixture",
        "parser_version": "1",
        "parsed_at": NOW,
    }
    with pytest.raises(ValidationError):
        ParsedDocument.model_validate({**base, "blocks": (_text_block(), _text_block())})
    with pytest.raises(ValidationError):
        ParsedDocument.model_validate(
            {
                **base,
                "blocks": (
                    _text_block(identifier="block-2", order=1),
                    _text_block(identifier="block-1", order=0),
                ),
            }
        )


def test_chunk_identity_is_stable_and_changes_with_source_or_content() -> None:
    first = derive_chunk_id(
        tenant_id="tenant-a",
        document_version_id="version-1",
        sequence=0,
        source_block_ids=("block-1",),
        content="Traction power procedure",
    )
    second = derive_chunk_id(
        tenant_id="tenant-a",
        document_version_id="version-1",
        sequence=0,
        source_block_ids=("block-1",),
        content="Traction power procedure",
    )
    changed = derive_chunk_id(
        tenant_id="tenant-a",
        document_version_id="version-1",
        sequence=0,
        source_block_ids=("block-1",),
        content="Changed procedure",
    )

    assert first == second
    assert first.startswith("chk_")
    assert changed != first


def test_chunk_record_requires_sources_and_valid_page_range() -> None:
    chunk_id = derive_chunk_id(
        tenant_id="tenant-a",
        document_version_id="version-1",
        sequence=0,
        source_block_ids=("block-1",),
        content="Traction power procedure",
    )
    chunk = ChunkRecord(
        id=chunk_id,
        tenant_id="tenant-a",
        knowledge_base_id="kb-1",
        document_id="document-1",
        document_version_id="version-1",
        parsed_document_id="parsed-1",
        sequence=0,
        content="Traction power procedure",
        source_block_ids=("block-1",),
        metadata=ChunkMetadata(page_start=1, page_end=1),
    )

    assert chunk.id_algorithm == CHUNK_ID_ALGORITHM
    with pytest.raises(ValidationError):
        ChunkMetadata(page_start=2, page_end=1)
