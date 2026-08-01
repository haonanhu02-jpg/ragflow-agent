"""Chunk, document, and hierarchical extractive summaries with token ceilings."""

from datetime import datetime
from enum import StrEnum

from ragflow_agent.knowledge.advanced.domain import (
    AdvancedArtifact,
    AdvancedCapability,
    derive_artifact_id,
)
from ragflow_agent.knowledge.domain.chunk import ChunkRecord


class SummaryLevel(StrEnum):
    CHUNK = "chunk"
    DOCUMENT = "document"
    HIERARCHICAL = "hierarchical"


class SummaryBuilder:
    def build(
        self,
        chunks: tuple[ChunkRecord, ...],
        *,
        level: SummaryLevel,
        build_version: str,
        created_at: datetime,
        max_tokens: int,
    ) -> AdvancedArtifact:
        if not chunks or max_tokens < 1:
            raise ValueError("summary requires chunks and a positive token budget")
        first = chunks[0]
        scope = (
            first.tenant_id,
            first.knowledge_base_id,
            first.document_id,
            first.document_version_id,
        )
        if any(
            (item.tenant_id, item.knowledge_base_id, item.document_id, item.document_version_id)
            != scope
            for item in chunks
        ):
            raise ValueError(
                "summary chunks must share tenant, knowledge base, document, and version"
            )
        words = " ".join(item.content for item in chunks).split()
        text = " ".join(words[:max_tokens])
        sources = tuple(dict.fromkeys(item.id for item in chunks))
        return AdvancedArtifact(
            id=derive_artifact_id(
                AdvancedCapability.SUMMARIES,
                tenant_id=first.tenant_id,
                document_version_id=first.document_version_id,
                build_version=build_version,
                source_chunk_ids=sources,
                text=f"{level.value}: {text}",
            ),
            capability=AdvancedCapability.SUMMARIES,
            tenant_id=first.tenant_id,
            knowledge_base_id=first.knowledge_base_id,
            document_id=first.document_id,
            document_version_id=first.document_version_id,
            build_version=build_version,
            source_chunk_ids=sources,
            text=f"{level.value}: {text}",
            attributes=(
                ("summary_level", level.value),
                ("token_count", str(min(len(words), max_tokens))),
            ),
            created_at=created_at,
        )
