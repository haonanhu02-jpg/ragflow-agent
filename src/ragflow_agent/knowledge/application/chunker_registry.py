"""Versioned Chunk Method registry with deterministic auto selection."""

from __future__ import annotations

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.chunk import ChunkRecord
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.ports.chunking import ChunkerPort, ChunkingRequest


class ChunkerRegistry:
    """Resolve one explicit or parser-recommended strategy."""

    strategy_id = "registry"
    strategy_version = "1"

    def __init__(self, *, chunkers: tuple[ChunkerPort, ...]) -> None:
        if not chunkers:
            raise ValueError("at least one chunker must be registered")
        identifiers = [self._identity(chunker)[0] for chunker in chunkers]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("chunk strategy identifiers must be unique")
        self._chunkers = {
            self._identity(chunker)[0]: chunker for chunker in chunkers
        }

    async def chunk(
        self,
        context: AuthorizationContext,
        request: ChunkingRequest,
    ) -> tuple[ChunkRecord, ...]:
        strategy_id = request.strategy_id
        if strategy_id == "auto":
            strategy_id = request.parsed_document.recommended_chunk_strategy
        chunker = self._chunkers.get(strategy_id)
        if chunker is None:
            raise KnowledgeConflictError(
                "chunk strategy is not registered",
                error_code="chunk_strategy_unknown",
                details={"strategy_id": strategy_id},
            )
        chunker_id, chunker_version = self._identity(chunker)
        if (
            request.strategy_id != "auto"
            and request.strategy_version not in {"auto", chunker_version}
        ):
            raise KnowledgeConflictError(
                "chunk strategy version is not available",
                error_code="chunk_strategy_version_unknown",
                details={
                    "strategy_id": chunker_id,
                    "strategy_version": request.strategy_version,
                },
            )
        return await chunker.chunk(
            context,
            request.model_copy(
                update={
                    "strategy_id": chunker_id,
                    "strategy_version": chunker_version,
                }
            ),
        )

    @staticmethod
    def _identity(chunker: ChunkerPort) -> tuple[str, str]:
        strategy_id = getattr(chunker, "strategy_id", None)
        strategy_version = getattr(chunker, "strategy_version", None)
        if not isinstance(strategy_id, str) or not strategy_id:
            raise ValueError("chunker must declare strategy_id")
        if not isinstance(strategy_version, str) or not strategy_version:
            raise ValueError("chunker must declare strategy_version")
        return strategy_id, strategy_version
