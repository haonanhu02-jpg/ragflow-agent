"""Versioned GraphRAG construction and query without a graph database."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from itertools import pairwise

from pydantic import Field

from ragflow_agent.knowledge.advanced.domain import (
    AdvancedBuild,
    AdvancedBuildStatus,
    AdvancedResourceBudget,
)
from ragflow_agent.knowledge.advanced.ports import AdvancedBuildRepository
from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.chunk import ChunkRecord

_ENTITY = re.compile(r"[A-Z][A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,12}")


class GraphEntity(KnowledgeModel):
    name: NonEmptyStr
    source_chunk_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)


class GraphEdge(KnowledgeModel):
    source: NonEmptyStr
    target: NonEmptyStr
    source_chunk_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)


class GraphSnapshot(KnowledgeModel):
    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    build_version: NonEmptyStr
    document_version_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    entities: tuple[GraphEntity, ...]
    edges: tuple[GraphEdge, ...]
    communities: tuple[tuple[NonEmptyStr, ...], ...]


class GraphRagService:
    def __init__(self, repository: AdvancedBuildRepository, budget: AdvancedResourceBudget) -> None:
        self._repository = repository
        self._budget = budget

    async def build(
        self,
        build: AdvancedBuild,
        chunks: tuple[ChunkRecord, ...],
        *,
        now: datetime,
    ) -> tuple[AdvancedBuild, GraphSnapshot | None]:
        prior = await self._repository.get_by_idempotency_key(
            tenant_id=build.tenant_id, idempotency_key=build.idempotency_key
        )
        if prior is not None and prior.status is AdvancedBuildStatus.SUCCEEDED:
            return prior, None
        if len(chunks) > self._budget.max_source_chunks:
            failed = build.model_copy(
                update={
                    "status": AdvancedBuildStatus.FAILED,
                    "error_code": "source_budget_exceeded",
                    "updated_at": now,
                }
            )
            await self._repository.save(failed)
            return failed, None
        running = build.model_copy(
            update={"status": AdvancedBuildStatus.RUNNING, "updated_at": now}
        )
        await self._repository.save(running)
        if running.cancellation_requested:
            cancelled = running.model_copy(
                update={"status": AdvancedBuildStatus.CANCELLED, "updated_at": now}
            )
            await self._repository.save(cancelled)
            return cancelled, None
        sources: dict[str, set[str]] = defaultdict(set)
        edge_sources: dict[tuple[str, str], set[str]] = defaultdict(set)
        for chunk in chunks:
            if (
                chunk.tenant_id != build.tenant_id
                or chunk.knowledge_base_id != build.knowledge_base_id
            ):
                raise ValueError("GraphRAG source scope mismatch")
            entities = tuple(dict.fromkeys(_ENTITY.findall(chunk.content)))[:32]
            for entity in entities:
                sources[entity].add(chunk.id)
            for source, target in pairwise(entities):
                if source != target:
                    edge_sources[tuple(sorted((source, target)))].add(chunk.id)
        if (
            len(sources) > self._budget.max_graph_entities
            or len(edge_sources) > self._budget.max_graph_edges
        ):
            failed = running.model_copy(
                update={
                    "status": AdvancedBuildStatus.FAILED,
                    "error_code": "graph_budget_exceeded",
                    "updated_at": now,
                }
            )
            await self._repository.save(failed)
            return failed, None
        entities_out = tuple(
            GraphEntity(name=name, source_chunk_ids=tuple(sorted(ids)))
            for name, ids in sorted(sources.items())
        )
        edges_out = tuple(
            GraphEdge(source=pair[0], target=pair[1], source_chunk_ids=tuple(sorted(ids)))
            for pair, ids in sorted(edge_sources.items())
        )
        adjacency: dict[str, set[str]] = defaultdict(set)
        for edge in edges_out:
            adjacency[edge.source].add(edge.target)
            adjacency[edge.target].add(edge.source)
        communities = tuple(
            tuple(sorted({name, *neighbors})) for name, neighbors in sorted(adjacency.items())
        )
        snapshot = GraphSnapshot(
            tenant_id=build.tenant_id,
            knowledge_base_id=build.knowledge_base_id,
            build_version=build.build_version,
            document_version_ids=build.document_version_ids,
            entities=entities_out,
            edges=edges_out,
            communities=communities,
        )
        succeeded = running.model_copy(
            update={
                "status": AdvancedBuildStatus.SUCCEEDED,
                "processed_chunks": len(chunks),
                "updated_at": now,
            }
        )
        await self._repository.save(succeeded)
        return succeeded, snapshot

    def query(self, snapshot: GraphSnapshot, text: str) -> tuple[GraphEntity, ...]:
        terms = {term.casefold() for term in _ENTITY.findall(text)}
        return tuple(entity for entity in snapshot.entities if entity.name.casefold() in terms)

    async def cancel(self, *, tenant_id: str, build_id: str, now: datetime) -> AdvancedBuild:
        build = await self._repository.get(tenant_id=tenant_id, build_id=build_id)
        if build is None:
            raise LookupError("advanced build not found")
        cancelled = build.model_copy(
            update={
                "cancellation_requested": True,
                "status": AdvancedBuildStatus.CANCELLED,
                "updated_at": now,
            }
        )
        await self._repository.save(cancelled)
        return cancelled
