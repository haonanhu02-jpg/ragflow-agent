"""Shared artifact construction without merging capability behavior."""

from datetime import datetime

from ragflow_agent.knowledge.advanced.domain import (
    AdvancedArtifact,
    AdvancedCapability,
    derive_artifact_id,
)
from ragflow_agent.knowledge.domain.chunk import ChunkRecord


def artifact_from_chunk(
    chunk: ChunkRecord,
    *,
    capability: AdvancedCapability,
    build_version: str,
    text: str,
    created_at: datetime,
    attributes: tuple[tuple[str, str], ...] = (),
) -> AdvancedArtifact:
    return AdvancedArtifact(
        id=derive_artifact_id(
            capability,
            tenant_id=chunk.tenant_id,
            document_version_id=chunk.document_version_id,
            build_version=build_version,
            source_chunk_ids=(chunk.id,),
            text=text,
        ),
        capability=capability,
        tenant_id=chunk.tenant_id,
        knowledge_base_id=chunk.knowledge_base_id,
        document_id=chunk.document_id,
        document_version_id=chunk.document_version_id,
        build_version=build_version,
        source_chunk_ids=(chunk.id,),
        text=text,
        attributes=attributes,
        created_at=created_at,
    )
