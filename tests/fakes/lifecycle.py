"""Deterministic lifecycle fixtures with no external infrastructure."""

from datetime import UTC, datetime

from ragflow_agent.knowledge.domain.authorization import (
    AuthorizationContext,
    Visibility,
)
from ragflow_agent.knowledge.domain.chunk import ChunkMetadata
from ragflow_agent.knowledge.domain.document import (
    Document,
    DocumentVersion,
    DocumentVersionStatus,
)
from ragflow_agent.knowledge.domain.knowledge_base import KnowledgeBase
from ragflow_agent.knowledge.domain.retrieval import IndexRecord
from tests.fakes.knowledge import MemoryKnowledgeStore, MemorySearchIndex

NOW = datetime(2026, 7, 31, tzinfo=UTC)


def context(tenant_id: str = "tenant-a") -> AuthorizationContext:
    return AuthorizationContext(
        tenant_id=tenant_id,
        actor_id="owner-a",
        request_id="request-a",
        roles=("operator",),
    )


def seed_active_document(
    store: MemoryKnowledgeStore,
    *,
    tenant_id: str = "tenant-a",
    document_id: str = "doc-a",
    version_id: str = "version-1",
) -> tuple[Document, DocumentVersion]:
    store.knowledge_bases["kb-a"] = KnowledgeBase(
        id="kb-a",
        tenant_id=tenant_id,
        owner_id="owner-a",
        name="Operations",
        visibility=Visibility.TENANT,
        created_at=NOW,
        updated_at=NOW,
    )
    document = Document(
        id=document_id,
        tenant_id=tenant_id,
        knowledge_base_id="kb-a",
        owner_id="owner-a",
        name="manual.md",
        visibility=Visibility.TENANT,
        current_version_id=version_id,
        created_at=NOW,
        updated_at=NOW,
    )
    version = DocumentVersion(
        id=version_id,
        tenant_id=tenant_id,
        knowledge_base_id="kb-a",
        document_id=document_id,
        created_by="owner-a",
        object_key=f"tenants/{tenant_id}/documents/{document_id}/versions/{version_id}/manual.md",
        media_type="text/markdown",
        content_hash="old-hash",
        size_bytes=8,
        status=DocumentVersionStatus.READY,
        index_version_id=f"idx_{version_id}",
        activated_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )
    store.documents[document.id] = document
    store.document_versions[version.id] = version
    return document, version


def seed_index(
    search: MemorySearchIndex,
    version: DocumentVersion,
    *,
    chunk_id: str = "chunk-1",
) -> None:
    record = IndexRecord(
        index_version_id=version.index_version_id or f"idx_{version.id}",
        tenant_id=version.tenant_id,
        knowledge_base_id=version.knowledge_base_id,
        owner_id="owner-a",
        visibility=Visibility.TENANT,
        document_id=version.document_id,
        document_version_id=version.id,
        chunk_id=chunk_id,
        content="reset controller",
        media_type=version.media_type,
        created_at=NOW,
        embedding=(1.0, 0.0, 0.0),
        metadata=ChunkMetadata(),
    )
    search.records[(version.tenant_id, record.index_version_id, record.chunk_id)] = record
