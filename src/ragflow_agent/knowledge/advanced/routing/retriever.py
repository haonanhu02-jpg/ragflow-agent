"""Optional advanced candidates merged behind the existing RetrieverPort."""

from collections.abc import Mapping

from ragflow_agent.knowledge.advanced.domain import AdvancedCapability, AdvancedIndexManifest
from ragflow_agent.knowledge.advanced.ports import AdvancedCandidatePort
from ragflow_agent.knowledge.advanced.routing.feature_flags import AdvancedFeatureFlags
from ragflow_agent.knowledge.advanced.routing.index_compatibility import check_manifest
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.retrieval import (
    RetrievalCandidate,
    RetrievalQuery,
    RetrievalResult,
)
from ragflow_agent.knowledge.ports.search import RetrieverPort


class AdvancedRetriever:
    """Decorate Phase 06 retrieval; any advanced fault safely returns the base result."""

    def __init__(
        self,
        *,
        base: RetrieverPort,
        flags: AdvancedFeatureFlags,
        providers: Mapping[AdvancedCapability, AdvancedCandidatePort],
        manifests: Mapping[tuple[str, str, AdvancedCapability], AdvancedIndexManifest],
        active_document_versions: Mapping[tuple[str, str], frozenset[str]],
    ) -> None:
        self._base = base
        self._flags = flags
        self._providers = providers
        self._manifests = manifests
        self._active_document_versions = active_document_versions

    async def retrieve(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
    ) -> RetrievalResult:
        base_result = await self._base.retrieve(context, query)
        merged: dict[str, RetrievalCandidate] = {
            item.chunk_id: item for item in base_result.candidates
        }
        for capability in self._flags.enabled_capabilities():
            provider = self._providers.get(capability)
            if provider is None:
                continue
            for knowledge_base_id in query.knowledge_base_ids:
                manifest = self._manifests.get((context.tenant_id, knowledge_base_id, capability))
                active = self._active_document_versions.get(
                    (context.tenant_id, knowledge_base_id), frozenset()
                )
                decision = check_manifest(
                    manifest,
                    capability=capability,
                    tenant_id=context.tenant_id,
                    knowledge_base_id=knowledge_base_id,
                    active_document_versions=active,
                )
                if not decision.usable:
                    continue
                try:
                    candidates = await provider.retrieve(context, query)
                except (
                    Exception
                ):  # provider errors are observable upstream; retrieval remains available
                    continue
                for candidate in candidates:
                    if (
                        candidate.tenant_id != context.tenant_id
                        or candidate.knowledge_base_id != knowledge_base_id
                        or candidate.document_version_id not in active
                    ):
                        continue
                    prior = merged.get(candidate.chunk_id)
                    if prior is None or candidate.score.final_score > prior.score.final_score:
                        merged[candidate.chunk_id] = candidate
        ranked = tuple(
            sorted(merged.values(), key=lambda item: item.score.final_score, reverse=True)[
                : query.top_n
            ]
        )
        return base_result.model_copy(update={"candidates": ranked})
