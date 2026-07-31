"""Generation-based Elasticsearch rebuild and atomic alias publication."""

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.domain.lifecycle import IndexGeneration, IndexGenerationValidation
from ragflow_agent.knowledge.domain.retrieval import IndexRecord
from ragflow_agent.knowledge.ports.search import LifecycleSearchPort


class IndexRebuildService:
    def __init__(self, search: LifecycleSearchPort) -> None:
        self._search = search

    async def build_and_publish(
        self,
        context: AuthorizationContext,
        generation: IndexGeneration,
        records: tuple[IndexRecord, ...],
        *,
        expected_current: str | None,
    ) -> IndexGenerationValidation:
        if context.tenant_id != generation.tenant_id:
            raise KnowledgeConflictError("tenant mismatch", error_code="tenant_mismatch")
        await self._search.create_staging_generation(context, generation)
        try:
            await self._search.write_generation(context, generation, records)
            validation = await self._search.validate_generation(context, generation)
            if not validation.healthy or validation.chunk_count != generation.expected_chunks:
                raise KnowledgeConflictError(
                    "staging index validation failed",
                    error_code="index_generation_invalid",
                )
            try:
                previous = await self._search.switch_alias(
                    context, generation, expected_current=expected_current
                )
            except Exception:
                actual = await self._search.resolve_alias(context, alias=generation.read_alias)
                if actual != generation.physical_index:
                    raise
                previous = expected_current
            if previous != expected_current:
                raise KnowledgeConflictError(
                    "read alias changed concurrently", error_code="index_alias_conflict"
                )
            return validation
        except Exception:
            actual = await self._search.resolve_alias(context, alias=generation.read_alias)
            if actual != generation.physical_index:
                await self._search.delete_generation(context, generation)
            raise

    async def rollback_alias(
        self,
        context: AuthorizationContext,
        target: IndexGeneration,
        *,
        expected_current: str,
    ) -> None:
        validation = await self._search.validate_generation(context, target)
        if not validation.healthy:
            raise KnowledgeConflictError(
                "rollback index is unhealthy", error_code="index_generation_invalid"
            )
        await self._search.switch_alias(context, target, expected_current=expected_current)
