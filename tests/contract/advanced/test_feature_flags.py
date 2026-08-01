from datetime import UTC, datetime

from ragflow_agent.config import AdvancedRagSettings
from ragflow_agent.knowledge.advanced.domain import AdvancedCapability, AdvancedIndexManifest
from ragflow_agent.knowledge.advanced.routing.feature_flags import AdvancedFeatureFlags
from ragflow_agent.knowledge.advanced.routing.index_compatibility import check_manifest


def test_every_advanced_capability_is_disabled_by_default() -> None:
    flags = AdvancedFeatureFlags(AdvancedRagSettings())
    assert flags.enabled_capabilities() == ()


def test_only_server_settings_can_enable_and_manifest_scope_must_match() -> None:
    flags = AdvancedFeatureFlags(AdvancedRagSettings(graphrag_enabled=True))
    assert flags.enabled(AdvancedCapability.GRAPHRAG)
    manifest = AdvancedIndexManifest(
        capability=AdvancedCapability.GRAPHRAG,
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        build_version="build-1",
        document_version_ids=("ver-a",),
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
        content_hash="sha256:synthetic",
    )
    assert check_manifest(
        manifest,
        capability=AdvancedCapability.GRAPHRAG,
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        active_document_versions=frozenset({"ver-a"}),
    ).usable
    assert not check_manifest(
        manifest,
        capability=AdvancedCapability.GRAPHRAG,
        tenant_id="tenant-b",
        knowledge_base_id="kb-a",
        active_document_versions=frozenset({"ver-a"}),
    ).usable
    assert not check_manifest(
        manifest.model_copy(update={"complete": False}),
        capability=AdvancedCapability.GRAPHRAG,
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        active_document_versions=frozenset({"ver-a"}),
    ).usable
