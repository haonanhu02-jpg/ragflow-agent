"""Versioned parser output, source coordinates, and index-neutral chunks."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from hashlib import sha256

from pydantic import Field, field_validator, model_validator

from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr

PARSED_DOCUMENT_SCHEMA_VERSION = 2
CHUNK_SCHEMA_VERSION = 2
CHUNK_ID_ALGORITHM = "sha256-v1"
CHUNK_ID_ALGORITHM_V2 = "sha256-v2"


class BlockKind(StrEnum):
    """Normalized block kinds supported by the parser contract."""

    HEADING = "heading"
    TEXT = "text"
    LIST = "list"
    TABLE = "table"
    IMAGE = "image"
    CODE = "code"


class CoordinateSpace(StrEnum):
    """Coordinate system used by a source bounding box."""

    PAGE_POINTS = "page_points"
    PIXELS = "pixels"
    NORMALIZED = "normalized"


class BoundingBox(KnowledgeModel):
    """Rectangle in an explicitly named coordinate space."""

    x0: float
    y0: float
    x1: float
    y1: float
    coordinate_space: CoordinateSpace

    @model_validator(mode="after")
    def validate_geometry(self) -> BoundingBox:
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("bounding box must have positive width and height")
        if self.coordinate_space is CoordinateSpace.NORMALIZED:
            values = (self.x0, self.y0, self.x1, self.y1)
            if any(value < 0 or value > 1 for value in values):
                raise ValueError("normalized bounding-box coordinates must be in [0, 1]")
        return self


class TableMetadata(KnowledgeModel):
    """Typed table shape retained without parser-specific dictionaries."""

    rows: int = Field(ge=1)
    columns: int = Field(ge=1)
    has_header: bool = False


class ImageReference(KnowledgeModel):
    """Object-storage reference for an extracted image."""

    object_key: NonEmptyStr
    media_type: NonEmptyStr
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    embedded_path: str | None = None


class ParseWarning(KnowledgeModel):
    """Stable, non-fatal parser degradation visible to ingestion callers."""

    code: NonEmptyStr
    message: NonEmptyStr
    page_number: int | None = Field(default=None, ge=1)


class ParsedBlock(KnowledgeModel):
    """Ordered parser output with optional page geometry."""

    id: NonEmptyStr
    kind: BlockKind
    order: int = Field(ge=0)
    text: str = ""
    page_number: int | None = Field(default=None, ge=1)
    bounding_box: BoundingBox | None = None
    heading_path: tuple[str, ...] = ()
    table: TableMetadata | None = None
    image: ImageReference | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("heading_path")
    @classmethod
    def headings_are_not_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            raise ValueError("heading_path cannot contain blank values")
        return normalized

    @model_validator(mode="after")
    def validate_kind_payload(self) -> ParsedBlock:
        if self.bounding_box is not None and self.page_number is None:
            raise ValueError("bounding_box requires page_number")
        if self.kind is BlockKind.TABLE and self.table is None:
            raise ValueError("table blocks require table metadata")
        if self.kind is not BlockKind.TABLE and self.table is not None:
            raise ValueError("table metadata is only valid for table blocks")
        if self.kind is BlockKind.IMAGE and self.image is None:
            raise ValueError("image blocks require an image reference")
        if self.kind is not BlockKind.IMAGE and self.image is not None:
            raise ValueError("image reference is only valid for image blocks")
        if not self.text.strip() and self.image is None:
            raise ValueError("non-image blocks require text")
        return self


class ParsedDocument(KnowledgeModel):
    """Parser-neutral, versioned document representation."""

    schema_version: int = PARSED_DOCUMENT_SCHEMA_VERSION
    id: NonEmptyStr
    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    document_id: NonEmptyStr
    document_version_id: NonEmptyStr
    parser_name: NonEmptyStr
    parser_version: NonEmptyStr
    parsed_at: datetime
    blocks: tuple[ParsedBlock, ...]
    source_media_type: str | None = None
    source_name: str | None = None
    recommended_chunk_strategy: NonEmptyStr = "general"
    warnings: tuple[ParseWarning, ...] = ()

    @field_validator("parsed_at")
    @classmethod
    def parsed_at_is_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("parsed_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def blocks_are_unique_and_ordered(self) -> ParsedDocument:
        identifiers = [block.id for block in self.blocks]
        orders = [block.order for block in self.blocks]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("parsed block identifiers must be unique")
        if len(orders) != len(set(orders)):
            raise ValueError("parsed block order values must be unique")
        if orders != sorted(orders):
            raise ValueError("parsed blocks must be sorted by order")
        return self


class ChunkMetadata(KnowledgeModel):
    """Backend-independent metadata retained by each chunk."""

    heading_path: tuple[str, ...] = ()
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    language: str | None = None
    source_order_start: int | None = Field(default=None, ge=0)
    source_order_end: int | None = Field(default=None, ge=0)
    block_kinds: tuple[BlockKind, ...] = ()
    bounding_box: BoundingBox | None = None
    contains_table: bool = False
    contains_image: bool = False
    parser_name: str | None = None
    parser_version: str | None = None
    chunk_strategy_id: str | None = None
    chunk_strategy_version: str | None = None

    @model_validator(mode="after")
    def validate_page_range(self) -> ChunkMetadata:
        if (self.page_start is None) != (self.page_end is None):
            raise ValueError("page_start and page_end must be provided together")
        if (
            self.page_start is not None
            and self.page_end is not None
            and self.page_end < self.page_start
        ):
            raise ValueError("page_end cannot precede page_start")
        if (self.source_order_start is None) != (self.source_order_end is None):
            raise ValueError("source order bounds must be provided together")
        if (
            self.source_order_start is not None
            and self.source_order_end is not None
            and self.source_order_end < self.source_order_start
        ):
            raise ValueError("source_order_end cannot precede source_order_start")
        if self.bounding_box is not None and self.page_start != self.page_end:
            raise ValueError("one chunk bounding_box requires one source page")
        return self


class ChunkRecord(KnowledgeModel):
    """Stable chunk contract before an embedding or search backend is selected."""

    schema_version: int = CHUNK_SCHEMA_VERSION
    id: NonEmptyStr
    id_algorithm: NonEmptyStr = CHUNK_ID_ALGORITHM
    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    document_id: NonEmptyStr
    document_version_id: NonEmptyStr
    parsed_document_id: NonEmptyStr
    sequence: int = Field(ge=0)
    content: NonEmptyStr
    source_block_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    parent_chunk_id: str | None = None
    token_count: int | None = Field(default=None, ge=0)
    metadata: ChunkMetadata = Field(default_factory=ChunkMetadata)

    @field_validator("source_block_ids")
    @classmethod
    def source_blocks_are_unique(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("source_block_ids must be unique")
        return value


def derive_chunk_id(
    *,
    tenant_id: str,
    document_version_id: str,
    sequence: int,
    source_block_ids: tuple[str, ...],
    content: str,
) -> str:
    """Derive a deterministic v1 chunk ID from stable source identity and content."""
    if sequence < 0:
        raise ValueError("sequence must be non-negative")
    parts = (
        CHUNK_ID_ALGORITHM,
        tenant_id.strip(),
        document_version_id.strip(),
        str(sequence),
        ",".join(source_block_ids),
        sha256(content.encode("utf-8")).hexdigest(),
    )
    if not parts[1] or not parts[2] or not source_block_ids or not content.strip():
        raise ValueError("chunk identity inputs must not be empty")
    digest = sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return f"chk_{digest[:32]}"


def derive_chunk_id_v2(
    *,
    tenant_id: str,
    document_version_id: str,
    strategy_id: str,
    strategy_version: str,
    sequence: int,
    source_block_ids: tuple[str, ...],
    content: str,
) -> str:
    """Derive a strategy-aware stable ID without changing Phase 04 v1 IDs."""
    values = (
        tenant_id.strip(),
        document_version_id.strip(),
        strategy_id.strip(),
        strategy_version.strip(),
        content.strip(),
    )
    if sequence < 0 or any(not value for value in values) or not source_block_ids:
        raise ValueError("v2 chunk identity inputs must not be empty")
    parts = (
        CHUNK_ID_ALGORITHM_V2,
        values[0],
        values[1],
        values[2],
        values[3],
        str(sequence),
        ",".join(source_block_ids),
        sha256(values[4].encode("utf-8")).hexdigest(),
    )
    digest = sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return f"chk_{digest[:32]}"
