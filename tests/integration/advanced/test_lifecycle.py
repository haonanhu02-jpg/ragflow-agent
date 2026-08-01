import pytest

from ragflow_agent.knowledge.advanced.domain import AdvancedCapability
from ragflow_agent.knowledge.advanced.enrichment.keywords import KeywordExtractor
from ragflow_agent.knowledge.advanced.infrastructure.memory import MemoryAdvancedArtifactRepository
from ragflow_agent.knowledge.advanced.lifecycle import AdvancedLifecycleService
from tests.fakes.advanced import NOW, make_chunk


@pytest.mark.asyncio
async def test_derived_artifacts_are_deleted_by_tenant_and_version() -> None:
    repository = MemoryAdvancedArtifactRepository()
    artifact = KeywordExtractor().extract(
        make_chunk("chunk-1", "brake alarm"), build_version="build-1", created_at=NOW
    )
    assert artifact.capability is AdvancedCapability.KEYWORDS
    await repository.put(artifact)
    service = AdvancedLifecycleService(repository)
    assert (
        await service.retire_document_version(tenant_id="tenant-b", document_version_id="ver-a")
        == 0
    )
    assert (
        await service.retire_document_version(tenant_id="tenant-a", document_version_id="ver-a")
        == 1
    )
    assert (
        await repository.list_for_version(tenant_id="tenant-a", document_version_id="ver-a") == ()
    )
