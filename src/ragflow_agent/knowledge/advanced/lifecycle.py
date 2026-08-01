"""Advanced derived-data cleanup hook used by Phase 07 lifecycle orchestration."""

from ragflow_agent.knowledge.advanced.ports import AdvancedArtifactRepository


class AdvancedLifecycleService:
    def __init__(self, repository: AdvancedArtifactRepository) -> None:
        self._repository = repository

    async def retire_document_version(self, *, tenant_id: str, document_version_id: str) -> int:
        """Physically remove derived artifacts before a version can no longer be active."""
        return await self._repository.delete_version(
            tenant_id=tenant_id,
            document_version_id=document_version_id,
        )
