"""Fail-closed validation of derived index manifests."""

from dataclasses import dataclass

from ragflow_agent.knowledge.advanced.domain import (
    ADVANCED_SCHEMA_VERSION,
    AdvancedCapability,
    AdvancedIndexManifest,
)


@dataclass(frozen=True, slots=True)
class CompatibilityDecision:
    usable: bool
    fallback_reason: str | None = None


def check_manifest(
    manifest: AdvancedIndexManifest | None,
    *,
    capability: AdvancedCapability,
    tenant_id: str,
    knowledge_base_id: str,
    active_document_versions: frozenset[str],
) -> CompatibilityDecision:
    if manifest is None:
        return CompatibilityDecision(False, "index_missing")
    if manifest.schema_version != ADVANCED_SCHEMA_VERSION:
        return CompatibilityDecision(False, "schema_incompatible")
    if not manifest.complete:
        return CompatibilityDecision(False, "index_incomplete")
    if manifest.capability is not capability:
        return CompatibilityDecision(False, "capability_mismatch")
    if manifest.tenant_id != tenant_id or manifest.knowledge_base_id != knowledge_base_id:
        return CompatibilityDecision(False, "scope_mismatch")
    if not set(manifest.document_version_ids).issubset(active_document_versions):
        return CompatibilityDecision(False, "stale_document_version")
    return CompatibilityDecision(True)
