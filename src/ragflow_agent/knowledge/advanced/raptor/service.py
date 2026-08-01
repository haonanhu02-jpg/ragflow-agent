"""Bounded RAPTOR tree that strictly converges and preserves leaf sources."""

from __future__ import annotations

from pydantic import Field

from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.chunk import ChunkRecord


class RaptorNode(KnowledgeModel):
    id: NonEmptyStr
    level: int = Field(ge=0)
    text: NonEmptyStr
    source_chunk_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    child_ids: tuple[NonEmptyStr, ...] = ()


class RaptorTree(KnowledgeModel):
    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    document_version_id: NonEmptyStr
    build_version: NonEmptyStr
    levels: tuple[tuple[RaptorNode, ...], ...] = Field(min_length=1)


class RaptorBuilder:
    def build(
        self,
        chunks: tuple[ChunkRecord, ...],
        *,
        build_version: str,
        max_levels: int = 4,
        summary_words: int = 96,
    ) -> RaptorTree:
        if not chunks or not 1 <= max_levels <= 4:
            raise ValueError("RAPTOR requires chunks and one to four levels")
        first = chunks[0]
        scope = (first.tenant_id, first.knowledge_base_id, first.document_version_id)
        if any(
            (item.tenant_id, item.knowledge_base_id, item.document_version_id) != scope
            for item in chunks
        ):
            raise ValueError(
                "RAPTOR chunks must share tenant, knowledge base, and document version"
            )
        current = tuple(
            RaptorNode(
                id=f"raptor_leaf_{item.id}", level=0, text=item.content, source_chunk_ids=(item.id,)
            )
            for item in chunks
        )
        levels: list[tuple[RaptorNode, ...]] = [current]
        level = 1
        while len(current) > 1 and level < max_levels:
            parents: list[RaptorNode] = []
            for index in range(0, len(current), 2):
                children = current[index : index + 2]
                sources = tuple(
                    dict.fromkeys(source for child in children for source in child.source_chunk_ids)
                )
                words = " ".join(child.text for child in children).split()[:summary_words]
                parents.append(
                    RaptorNode(
                        id=f"raptor_{build_version}_{level}_{index // 2}",
                        level=level,
                        text=" ".join(words),
                        source_chunk_ids=sources,
                        child_ids=tuple(child.id for child in children),
                    )
                )
            current = tuple(parents)
            if len(current) >= len(levels[-1]):
                raise RuntimeError("RAPTOR tree failed to converge")
            levels.append(current)
            level += 1
        return RaptorTree(
            tenant_id=first.tenant_id,
            knowledge_base_id=first.knowledge_base_id,
            document_version_id=first.document_version_id,
            build_version=build_version,
            levels=tuple(levels),
        )
