"""Default-off server feature flags; client and model input never mutate them."""

from ragflow_agent.config import AdvancedRagSettings
from ragflow_agent.knowledge.advanced.domain import AdvancedCapability


class AdvancedFeatureFlags:
    def __init__(self, settings: AdvancedRagSettings) -> None:
        self._enabled = {
            AdvancedCapability.KEYWORDS: settings.keywords_enabled,
            AdvancedCapability.QUESTIONS: settings.questions_enabled,
            AdvancedCapability.SUMMARIES: settings.summaries_enabled,
            AdvancedCapability.TOC: settings.toc_enabled,
            AdvancedCapability.PARENT_CHILD: settings.parent_child_enabled,
            AdvancedCapability.MULTIMODAL: settings.multimodal_enabled,
            AdvancedCapability.GRAPHRAG: settings.graphrag_enabled,
            AdvancedCapability.RAPTOR: settings.raptor_enabled,
            AdvancedCapability.TEMPORAL: settings.temporal_enabled,
        }

    def enabled(self, capability: AdvancedCapability) -> bool:
        return self._enabled[capability]

    def enabled_capabilities(self) -> tuple[AdvancedCapability, ...]:
        return tuple(capability for capability, enabled in self._enabled.items() if enabled)
