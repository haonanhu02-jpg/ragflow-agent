"""Deterministic heading tree; model output may only fill missing labels."""

from __future__ import annotations

from pydantic import Field, model_validator

from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.chunk import BlockKind, ParsedDocument


class TocNode(KnowledgeModel):
    id: NonEmptyStr
    title: NonEmptyStr
    level: int = Field(ge=1)
    order: int = Field(ge=0)
    block_id: NonEmptyStr
    page_number: int | None = Field(default=None, ge=1)
    chunk_ids: tuple[NonEmptyStr, ...] = ()


class TocTree(KnowledgeModel):
    document_version_id: NonEmptyStr
    nodes: tuple[TocNode, ...]

    @model_validator(mode="after")
    def ordered_and_acyclic(self) -> TocTree:
        orders = [item.order for item in self.nodes]
        ids = [item.id for item in self.nodes]
        if orders != sorted(orders) or len(ids) != len(set(ids)):
            raise ValueError("TOC nodes must be ordered and unique")
        return self


class TocBuilder:
    def build(
        self,
        document: ParsedDocument,
        *,
        chunk_by_block: dict[str, tuple[str, ...]] | None = None,
    ) -> TocTree:
        links = chunk_by_block or {}
        nodes = []
        for block in document.blocks:
            if block.kind is not BlockKind.HEADING:
                continue
            level = max(1, len(block.heading_path) or 1)
            nodes.append(
                TocNode(
                    id=f"toc_{document.document_version_id}_{block.order}",
                    title=block.text.strip(),
                    level=level,
                    order=block.order,
                    block_id=block.id,
                    page_number=block.page_number,
                    chunk_ids=links.get(block.id, ()),
                )
            )
        return TocTree(document_version_id=document.document_version_id, nodes=tuple(nodes))
