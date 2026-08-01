"""Child retrieval followed by scope-safe parent and neighbor expansion."""

from ragflow_agent.knowledge.domain.chunk import ChunkRecord


class ParentContextExpander:
    def expand(
        self,
        hit: ChunkRecord,
        candidates: tuple[ChunkRecord, ...],
        *,
        max_tokens: int = 6_000,
    ) -> tuple[ChunkRecord, ...]:
        if max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        same_scope = [
            item
            for item in candidates
            if item.tenant_id == hit.tenant_id
            and item.knowledge_base_id == hit.knowledge_base_id
            and item.document_id == hit.document_id
            and item.document_version_id == hit.document_version_id
        ]
        allowed_ids = {hit.id, hit.parent_chunk_id}
        allowed_sequences = {hit.sequence - 1, hit.sequence, hit.sequence + 1}
        selected = [
            item
            for item in same_scope
            if item.id in allowed_ids
            or item.parent_chunk_id == hit.parent_chunk_id
            or item.sequence in allowed_sequences
        ]
        selected.sort(key=lambda item: item.sequence)
        result: list[ChunkRecord] = []
        used = 0
        for item in selected:
            cost = item.token_count if item.token_count is not None else len(item.content.split())
            if used + cost > max_tokens:
                continue
            if item.id not in {existing.id for existing in result}:
                result.append(item)
                used += cost
        return tuple(result)
