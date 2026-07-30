"""Factory-style Repository and UnitOfWork contract tests."""

from datetime import UTC, datetime

import pytest

from ragflow_agent.knowledge.domain.authorization import Visibility
from ragflow_agent.knowledge.domain.document import Document, DocumentVersion
from ragflow_agent.knowledge.domain.errors import (
    KnowledgeAuthorizationError,
    KnowledgeConflictError,
)
from ragflow_agent.knowledge.domain.knowledge_base import KnowledgeBase
from ragflow_agent.knowledge.ports.uow import KnowledgeUnitOfWork
from tests.fakes.knowledge import MemoryKnowledgeUnitOfWorkFactory

NOW = datetime(2026, 7, 30, 8, 0, tzinfo=UTC)


def _knowledge_base(*, identifier: str = "kb-1", tenant_id: str = "tenant-a") -> KnowledgeBase:
    return KnowledgeBase(
        id=identifier,
        tenant_id=tenant_id,
        owner_id="owner-a",
        name="Operations",
        visibility=Visibility.PRIVATE,
        created_at=NOW,
        updated_at=NOW,
    )


def _document(*, identifier: str = "document-1", tenant_id: str = "tenant-a") -> Document:
    return Document(
        id=identifier,
        tenant_id=tenant_id,
        knowledge_base_id="kb-1",
        owner_id="owner-a",
        name="manual.pdf",
        created_at=NOW,
        updated_at=NOW,
    )


def _version(*, identifier: str = "version-1", tenant_id: str = "tenant-a") -> DocumentVersion:
    return DocumentVersion(
        id=identifier,
        tenant_id=tenant_id,
        knowledge_base_id="kb-1",
        document_id="document-1",
        created_by="owner-a",
        object_key=f"{tenant_id}/version-1/source",
        media_type="application/pdf",
        content_hash="abc123",
        size_bytes=10,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.mark.asyncio
async def test_factory_returns_the_declared_unit_of_work_contract() -> None:
    unit_of_work: KnowledgeUnitOfWork = MemoryKnowledgeUnitOfWorkFactory()()

    assert unit_of_work.knowledge_bases is not None


@pytest.mark.asyncio
async def test_commit_persists_aggregate_and_tenant_scoped_read() -> None:
    factory = MemoryKnowledgeUnitOfWorkFactory()
    async with factory() as unit_of_work:
        await unit_of_work.knowledge_bases.add(
            tenant_id="tenant-a",
            entity=_knowledge_base(),
        )
        await unit_of_work.commit()

    async with factory() as unit_of_work:
        assert (
            await unit_of_work.knowledge_bases.get(
                tenant_id="tenant-a",
                resource_id="kb-1",
            )
            is not None
        )
        assert (
            await unit_of_work.knowledge_bases.get(
                tenant_id="tenant-b",
                resource_id="kb-1",
            )
            is None
        )


@pytest.mark.asyncio
async def test_no_commit_and_exception_both_roll_back() -> None:
    factory = MemoryKnowledgeUnitOfWorkFactory()
    async with factory() as unit_of_work:
        await unit_of_work.knowledge_bases.add(
            tenant_id="tenant-a",
            entity=_knowledge_base(),
        )

    with pytest.raises(RuntimeError):
        async with factory() as unit_of_work:
            await unit_of_work.knowledge_bases.add(
                tenant_id="tenant-a",
                entity=_knowledge_base(identifier="kb-2"),
            )
            raise RuntimeError("rollback")

    async with factory() as unit_of_work:
        assert (
            await unit_of_work.knowledge_bases.get(
                tenant_id="tenant-a",
                resource_id="kb-1",
            )
            is None
        )
        assert (
            await unit_of_work.knowledge_bases.get(
                tenant_id="tenant-a",
                resource_id="kb-2",
            )
            is None
        )


@pytest.mark.asyncio
async def test_duplicate_identifier_is_rejected() -> None:
    factory = MemoryKnowledgeUnitOfWorkFactory()
    async with factory() as unit_of_work:
        await unit_of_work.knowledge_bases.add(
            tenant_id="tenant-a",
            entity=_knowledge_base(),
        )
        with pytest.raises(KnowledgeConflictError) as captured:
            await unit_of_work.knowledge_bases.add(
                tenant_id="tenant-a",
                entity=_knowledge_base(),
            )
    assert captured.value.error_code == "knowledge_resource_exists"


@pytest.mark.asyncio
async def test_document_versions_are_listed_only_inside_tenant_and_document() -> None:
    factory = MemoryKnowledgeUnitOfWorkFactory()
    async with factory() as unit_of_work:
        await unit_of_work.documents.add(
            tenant_id="tenant-a",
            entity=_document(),
        )
        await unit_of_work.document_versions.add(
            tenant_id="tenant-a",
            entity=_version(),
        )
        await unit_of_work.document_versions.add(
            tenant_id="tenant-b",
            entity=_version(identifier="version-2", tenant_id="tenant-b"),
        )
        await unit_of_work.commit()

    async with factory() as unit_of_work:
        tenant_a = await unit_of_work.document_versions.list_for_document(
            tenant_id="tenant-a",
            document_id="document-1",
        )
        tenant_b = await unit_of_work.document_versions.list_for_document(
            tenant_id="tenant-b",
            document_id="document-1",
        )

    assert [version.id for version in tenant_a] == ["version-1"]
    assert [version.id for version in tenant_b] == ["version-2"]


@pytest.mark.asyncio
async def test_add_rejects_entity_from_another_tenant() -> None:
    factory = MemoryKnowledgeUnitOfWorkFactory()

    async with factory() as unit_of_work:
        with pytest.raises(KnowledgeAuthorizationError) as captured:
            await unit_of_work.knowledge_bases.add(
                tenant_id="tenant-a",
                entity=_knowledge_base(tenant_id="tenant-b"),
            )

    assert captured.value.error_code == "tenant_mismatch"
