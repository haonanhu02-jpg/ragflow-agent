"""Elasticsearch 8 minimum BM25, KNN, and RRF hybrid adapter."""

from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any, cast

from elasticsearch import AsyncElasticsearch, BadRequestError, NotFoundError

from ragflow_agent.config import SearchSettings
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, Visibility
from ragflow_agent.knowledge.domain.chunk import BoundingBox, CoordinateSpace
from ragflow_agent.knowledge.domain.errors import (
    KnowledgeAuthorizationError,
    KnowledgeConflictError,
)
from ragflow_agent.knowledge.domain.lifecycle import (
    IndexGeneration,
    IndexGenerationValidation,
)
from ragflow_agent.knowledge.domain.retrieval import (
    Citation,
    FilterGroupOperator,
    FilterOperator,
    IndexRecord,
    IndexVersion,
    MetadataFilter,
    MetadataFilterGroup,
    RetrievalCandidate,
    RetrievalEmptyReason,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStage,
    RetrievalTrace,
    RetrievalTraceEvent,
    ScoreBreakdown,
    TraceAttribute,
)
from ragflow_agent.knowledge.ports.embedding import EmbeddingInput, EmbeddingPort, EmbeddingRequest

_RRF_K = 60
_PHASE05_METADATA_PROPERTIES: dict[str, dict[str, Any]] = {
    "source_order_start": {"type": "integer"},
    "source_order_end": {"type": "integer"},
    "block_kinds": {"type": "keyword"},
    "bbox_x0": {"type": "double"},
    "bbox_y0": {"type": "double"},
    "bbox_x1": {"type": "double"},
    "bbox_y1": {"type": "double"},
    "bbox_coordinate_space": {"type": "keyword"},
    "contains_table": {"type": "boolean"},
    "contains_image": {"type": "boolean"},
    "parser_name": {"type": "keyword"},
    "parser_version": {"type": "keyword"},
    "chunk_strategy_id": {"type": "keyword"},
    "chunk_strategy_version": {"type": "keyword"},
}
_PHASE06_SECURITY_PROPERTIES: dict[str, dict[str, Any]] = {
    "allowed_actor_ids": {"type": "keyword"},
    "allowed_roles": {"type": "keyword"},
    "document_enabled": {"type": "boolean"},
    "document_deleted": {"type": "boolean"},
}
_PHASE07_LIFECYCLE_PROPERTIES: dict[str, dict[str, Any]] = {
    "lifecycle_fencing_token": {"type": "long"},
}


class ElasticsearchSearchAdapter:
    """Map backend-neutral records and queries to Elasticsearch 8 APIs."""

    def __init__(
        self,
        settings: SearchSettings,
        *,
        embedding: EmbeddingPort,
        embedding_model_id: str,
        embedding_dimensions: int,
        client: AsyncElasticsearch | None = None,
    ) -> None:
        self._settings = settings
        self._index_name = settings.index_name
        self._embedding = embedding
        self._embedding_model_id = embedding_model_id
        self._dimensions = embedding_dimensions
        self._client = client or AsyncElasticsearch(
            settings.url.get_secret_value(),
            request_timeout=settings.request_timeout_seconds,
            verify_certs=settings.verify_certs,
        )

    async def close(self) -> None:
        await self._client.close()

    async def ensure_index(self) -> None:
        if await self._client.indices.exists(index=self._index_name):
            await self._validate_index_mapping()
            await self._client.indices.put_mapping(
                index=self._index_name,
                properties={
                    **_PHASE05_METADATA_PROPERTIES,
                    **_PHASE06_SECURITY_PROPERTIES,
                    **_PHASE07_LIFECYCLE_PROPERTIES,
                },
            )
            return
        try:
            await self._client.indices.create(
                index=self._index_name,
                mappings={
                    "dynamic": "strict",
                    "properties": {
                        "index_version_id": {"type": "keyword"},
                        "tenant_id": {"type": "keyword"},
                        "knowledge_base_id": {"type": "keyword"},
                        "owner_id": {"type": "keyword"},
                        "visibility": {"type": "keyword"},
                        "document_id": {"type": "keyword"},
                        "document_version_id": {"type": "keyword"},
                        "chunk_id": {"type": "keyword"},
                        "content": {"type": "text"},
                        "media_type": {"type": "keyword"},
                        "created_at": {"type": "date"},
                        "active": {"type": "boolean"},
                        **_PHASE06_SECURITY_PROPERTIES,
                        **_PHASE07_LIFECYCLE_PROPERTIES,
                        "heading_path": {"type": "keyword"},
                        "page_start": {"type": "integer"},
                        "page_end": {"type": "integer"},
                        "language": {"type": "keyword"},
                        **_PHASE05_METADATA_PROPERTIES,
                        "embedding": {
                            "type": "dense_vector",
                            "dims": self._dimensions,
                            "index": True,
                            "similarity": "cosine",
                        },
                    },
                },
            )
        except BadRequestError:
            if not await self._client.indices.exists(index=self._index_name):
                raise
        await self._validate_index_mapping()

    async def _validate_index_mapping(self) -> None:
        response = await self._client.indices.get_mapping(index=self._index_name)
        try:
            dimensions = int(
                response[self._index_name]["mappings"]["properties"]["embedding"]["dims"]
            )
        except (KeyError, TypeError, ValueError) as error:
            raise KnowledgeConflictError(
                "Elasticsearch index has no compatible embedding mapping",
                error_code="search_index_mapping_incompatible",
            ) from error
        if dimensions != self._dimensions:
            raise KnowledgeConflictError(
                "Elasticsearch index embedding dimensions differ from configuration",
                error_code="search_index_dimension_mismatch",
                details={"expected": self._dimensions, "actual": dimensions},
            )

    async def upsert(
        self,
        context: AuthorizationContext,
        version: IndexVersion,
        records: tuple[IndexRecord, ...],
    ) -> None:
        self._require_tenant(context, version.tenant_id)
        if version.embedding.dimensions != self._dimensions:
            raise KnowledgeConflictError(
                "index version dimensions do not match Elasticsearch mapping",
                error_code="index_dimension_mismatch",
            )
        operations: list[dict[str, Any]] = []
        for record in records:
            expected = (version.tenant_id, version.knowledge_base_id, version.id)
            actual = (record.tenant_id, record.knowledge_base_id, record.index_version_id)
            if actual != expected or len(record.embedding) != self._dimensions:
                raise KnowledgeConflictError(
                    "index record is incompatible with index version",
                    error_code="index_record_incompatible",
                )
            document_id = self._document_key(record)
            operations.extend(
                [
                    {"index": {"_index": self._index_name, "_id": document_id}},
                    self._source(record, active=False),
                ]
            )
        if operations:
            response = await self._client.bulk(operations=operations, refresh="wait_for")
            if bool(response.get("errors")):
                raise KnowledgeConflictError(
                    "Elasticsearch bulk upsert was partially rejected",
                    error_code="search_bulk_partial_failure",
                )

    async def delete(
        self,
        context: AuthorizationContext,
        *,
        index_version_id: str,
        chunk_ids: tuple[str, ...],
    ) -> None:
        if not chunk_ids:
            return
        await self._client.delete_by_query(
            index=self._index_name,
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": context.tenant_id}},
                        {"term": {"index_version_id": index_version_id}},
                        {"terms": {"chunk_id": list(chunk_ids)}},
                    ]
                }
            },
            refresh=True,
            conflicts="proceed",
        )

    async def activate(
        self,
        context: AuthorizationContext,
        version: IndexVersion,
    ) -> None:
        self._require_tenant(context, version.tenant_id)
        base_filter = [
            {"term": {"tenant_id": version.tenant_id}},
            {"term": {"knowledge_base_id": version.knowledge_base_id}},
        ]
        if version.document_id is not None:
            base_filter.append({"term": {"document_id": version.document_id}})
        await self._client.update_by_query(
            index=self._index_name,
            query={"bool": {"filter": base_filter}},
            script={"source": "ctx._source.active = false", "lang": "painless"},
            refresh=True,
            conflicts="proceed",
        )
        response = await self._client.update_by_query(
            index=self._index_name,
            query={
                "bool": {
                    "filter": [
                        *base_filter,
                        {"term": {"index_version_id": version.id}},
                    ]
                }
            },
            script={"source": "ctx._source.active = true", "lang": "painless"},
            refresh=True,
            conflicts="proceed",
        )
        if int(response.get("updated", 0)) == 0:
            raise KnowledgeConflictError(
                "index version contains no records to activate",
                error_code="index_activation_empty",
            )

    async def validate_document_version(
        self,
        context: AuthorizationContext,
        *,
        knowledge_base_id: str,
        document_id: str,
        document_version_id: str,
    ) -> int:
        response = await self._client.count(
            index=self._index_name,
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": context.tenant_id}},
                        {"term": {"knowledge_base_id": knowledge_base_id}},
                        {"term": {"document_id": document_id}},
                        {"term": {"document_version_id": document_version_id}},
                        {"term": {"document_deleted": False}},
                    ]
                }
            },
        )
        return int(response.get("count", 0))

    async def promote_document_version(
        self,
        context: AuthorizationContext,
        *,
        knowledge_base_id: str,
        document_id: str,
        document_version_id: str,
        fencing_token: int,
    ) -> None:
        response = await self._client.update_by_query(
            index=self._index_name,
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": context.tenant_id}},
                        {"term": {"knowledge_base_id": knowledge_base_id}},
                        {"term": {"document_id": document_id}},
                        {"term": {"document_version_id": document_version_id}},
                    ]
                }
            },
            script={
                "lang": "painless",
                "source": (
                    "if (ctx._source.lifecycle_fencing_token == null || "
                    "ctx._source.lifecycle_fencing_token <= params.token) { "
                    "ctx._source.active = true; ctx._source.document_deleted = false; "
                    "ctx._source.document_enabled = true; "
                    "ctx._source.lifecycle_fencing_token = params.token; } else { ctx.op='noop'; }"
                ),
                "params": {"token": fencing_token},
            },
            refresh=True,
            conflicts="proceed",
        )
        if int(response.get("updated", 0)) == 0 and int(response.get("noops", 0)) == 0:
            raise KnowledgeConflictError(
                "document version has no projection to promote",
                error_code="index_activation_empty",
            )

    async def retire_document_version(
        self,
        context: AuthorizationContext,
        *,
        knowledge_base_id: str,
        document_id: str,
        document_version_id: str,
    ) -> None:
        await self._set_document_version_active(
            context,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            document_version_id=document_version_id,
            active=False,
        )

    async def delete_document_version(
        self,
        context: AuthorizationContext,
        *,
        knowledge_base_id: str,
        document_id: str,
        document_version_id: str,
    ) -> None:
        await self._client.delete_by_query(
            index=self._index_name,
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": context.tenant_id}},
                        {"term": {"knowledge_base_id": knowledge_base_id}},
                        {"term": {"document_id": document_id}},
                        {"term": {"document_version_id": document_version_id}},
                    ]
                }
            },
            refresh=True,
            conflicts="proceed",
        )

    async def list_projection_versions(
        self,
        context: AuthorizationContext,
        *,
        limit: int = 1000,
    ) -> tuple[tuple[str, str, str], ...]:
        response = await self._client.search(
            index=self._index_name,
            query={"term": {"tenant_id": context.tenant_id}},
            size=limit,
            source_includes=[
                "knowledge_base_id",
                "document_id",
                "document_version_id",
            ],
        )
        hits = cast(list[dict[str, Any]], response["hits"]["hits"])
        return tuple(
            dict.fromkeys(
                (
                    str(hit["_source"]["knowledge_base_id"]),
                    str(hit["_source"]["document_id"]),
                    str(hit["_source"]["document_version_id"]),
                )
                for hit in hits
            )
        )

    async def create_staging_generation(
        self,
        context: AuthorizationContext,
        generation: IndexGeneration,
    ) -> None:
        self._require_generation_scope(context, generation)
        if await self._client.indices.exists(index=generation.physical_index):
            return
        await self._client.indices.create(
            index=generation.physical_index,
            mappings={"dynamic": "strict", "properties": self._mapping_properties()},
        )

    async def write_generation(
        self,
        context: AuthorizationContext,
        generation: IndexGeneration,
        records: tuple[IndexRecord, ...],
    ) -> None:
        self._require_generation_scope(context, generation)
        operations: list[dict[str, Any]] = []
        for record in records:
            if (
                record.tenant_id != context.tenant_id
                or record.knowledge_base_id != generation.knowledge_base_id
            ):
                raise KnowledgeAuthorizationError(reason_code="tenant_mismatch")
            operations.extend(
                [
                    {
                        "index": {
                            "_index": generation.physical_index,
                            "_id": self._document_key(record),
                        }
                    },
                    self._source(
                        record,
                        active=record.document_enabled and not record.document_deleted,
                    ),
                ]
            )
        if operations:
            response = await self._client.bulk(operations=operations, refresh="wait_for")
            if bool(response.get("errors")):
                raise KnowledgeConflictError(
                    "staging generation bulk upsert was partially rejected",
                    error_code="search_bulk_partial_failure",
                )

    async def validate_generation(
        self,
        context: AuthorizationContext,
        generation: IndexGeneration,
    ) -> IndexGenerationValidation:
        self._require_generation_scope(context, generation)
        mapping = await self._client.indices.get_mapping(index=generation.physical_index)
        properties = mapping[generation.physical_index]["mappings"].get("properties", {})
        response = await self._client.search(
            index=generation.physical_index,
            query={"match_all": {}},
            size=1,
            source_excludes=["embedding", "content"],
            track_total_hits=True,
        )
        total = int(response["hits"]["total"]["value"])
        sample = response["hits"]["hits"]
        tenant_valid = all(hit["_source"].get("tenant_id") == context.tenant_id for hit in sample)
        kb_valid = all(
            hit["_source"].get("knowledge_base_id") == generation.knowledge_base_id
            for hit in sample
        )
        lifecycle_valid = all(
            field in properties for field in ("active", "document_deleted", "document_version_id")
        )
        checksum = f"{generation.mapping_version}:{total}:{len(properties)}"
        return IndexGenerationValidation(
            physical_index=generation.physical_index,
            mapping_valid="embedding" in properties,
            chunk_count=total,
            tenant_scope_valid=tenant_valid,
            knowledge_base_scope_valid=kb_valid,
            lifecycle_fields_valid=lifecycle_valid,
            sample_query_valid=(not sample or (tenant_valid and kb_valid)),
            checksum=checksum,
        )

    async def switch_alias(
        self,
        context: AuthorizationContext,
        generation: IndexGeneration,
        *,
        expected_current: str | None,
    ) -> str | None:
        self._require_generation_scope(context, generation)
        current = await self.resolve_alias(context, alias=generation.read_alias)
        if current != expected_current:
            raise KnowledgeConflictError(
                "index alias changed before publication",
                error_code="index_alias_conflict",
                details={"expected": expected_current, "actual": current},
            )
        actions: list[dict[str, Any]] = []
        if current is not None:
            actions.extend(
                [
                    {"remove": {"index": current, "alias": generation.read_alias}},
                    {"remove": {"index": current, "alias": generation.write_alias}},
                ]
            )
        actions.extend(
            [
                {"add": {"index": generation.physical_index, "alias": generation.read_alias}},
                {"add": {"index": generation.physical_index, "alias": generation.write_alias}},
            ]
        )
        await self._client.indices.update_aliases(actions=actions)
        actual = await self.resolve_alias(context, alias=generation.read_alias)
        if actual != generation.physical_index:
            raise KnowledgeConflictError(
                "index alias publication result is unknown",
                error_code="index_alias_result_unknown",
                details={"actual": actual},
            )
        return current

    async def resolve_alias(
        self,
        context: AuthorizationContext,
        *,
        alias: str,
    ) -> str | None:
        if not alias.startswith(f"{self._index_name}-"):
            raise KnowledgeAuthorizationError(reason_code="tenant_mismatch")
        try:
            response = await self._client.indices.get_alias(name=alias)
        except NotFoundError:
            return None
        indices = sorted(str(index) for index in response)
        if len(indices) > 1:
            raise KnowledgeConflictError(
                "read alias points to multiple physical indexes",
                error_code="index_alias_ambiguous",
            )
        return indices[0] if indices else None

    async def delete_generation(
        self,
        context: AuthorizationContext,
        generation: IndexGeneration,
    ) -> None:
        self._require_generation_scope(context, generation)
        current = await self.resolve_alias(context, alias=generation.read_alias)
        if current == generation.physical_index:
            raise KnowledgeConflictError(
                "active index generation cannot be deleted",
                error_code="index_generation_active",
            )
        await self._client.indices.delete(index=generation.physical_index, ignore_unavailable=True)

    async def _set_document_version_active(
        self,
        context: AuthorizationContext,
        *,
        knowledge_base_id: str,
        document_id: str,
        document_version_id: str,
        active: bool,
    ) -> None:
        await self._client.update_by_query(
            index=self._index_name,
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": context.tenant_id}},
                        {"term": {"knowledge_base_id": knowledge_base_id}},
                        {"term": {"document_id": document_id}},
                        {"term": {"document_version_id": document_version_id}},
                    ]
                }
            },
            script={"source": "ctx._source.active = params.active", "params": {"active": active}},
            refresh=True,
            conflicts="proceed",
        )

    def _mapping_properties(self) -> dict[str, Any]:
        return {
            "index_version_id": {"type": "keyword"},
            "tenant_id": {"type": "keyword"},
            "knowledge_base_id": {"type": "keyword"},
            "owner_id": {"type": "keyword"},
            "visibility": {"type": "keyword"},
            "document_id": {"type": "keyword"},
            "document_version_id": {"type": "keyword"},
            "chunk_id": {"type": "keyword"},
            "content": {"type": "text"},
            "media_type": {"type": "keyword"},
            "created_at": {"type": "date"},
            "active": {"type": "boolean"},
            **_PHASE06_SECURITY_PROPERTIES,
            **_PHASE07_LIFECYCLE_PROPERTIES,
            "heading_path": {"type": "keyword"},
            "page_start": {"type": "integer"},
            "page_end": {"type": "integer"},
            "language": {"type": "keyword"},
            **_PHASE05_METADATA_PROPERTIES,
            "embedding": {
                "type": "dense_vector",
                "dims": self._dimensions,
                "index": True,
                "similarity": "cosine",
            },
        }

    def _require_generation_scope(
        self,
        context: AuthorizationContext,
        generation: IndexGeneration,
    ) -> None:
        self._require_tenant(context, generation.tenant_id)
        prefix = f"{self._index_name}-"
        if not all(
            value.startswith(prefix)
            for value in (
                generation.physical_index,
                generation.read_alias,
                generation.write_alias,
            )
        ):
            raise KnowledgeAuthorizationError(reason_code="tenant_mismatch")

    async def retrieve(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
    ) -> RetrievalResult:
        self._require_tenant(context, query.tenant_id)
        started = perf_counter()
        embedding_result = await self._embedding.embed(
            context,
            EmbeddingRequest(
                tenant_id=query.tenant_id,
                model_id=self._embedding_model_id,
                inputs=(EmbeddingInput(id="query", text=query.text),),
                trace_id=query.trace_id,
            ),
        )
        query_vector = embedding_result.vectors[0].values
        text_hits, vector_hits = await asyncio.gather(
            self._full_text_hits(context, query),
            self._vector_hits(context, query, query_vector),
        )
        candidates = self._fuse(text_hits, vector_hits, top_n=query.top_n)
        elapsed = (perf_counter() - started) * 1000
        trace = RetrievalTrace(
            trace_id=query.trace_id,
            tenant_id=query.tenant_id,
            original_query=query.text,
            authorization_applied=True,
            events=(
                RetrievalTraceEvent(
                    sequence=0,
                    stage=RetrievalStage.AUTHORIZATION,
                    elapsed_ms=0,
                    candidate_count=0,
                    attributes=(TraceAttribute(name="tenant_filter", value=True),),
                ),
                RetrievalTraceEvent(
                    sequence=1,
                    stage=RetrievalStage.FULL_TEXT,
                    elapsed_ms=elapsed,
                    candidate_count=len(text_hits),
                ),
                RetrievalTraceEvent(
                    sequence=2,
                    stage=RetrievalStage.VECTOR,
                    elapsed_ms=elapsed,
                    candidate_count=len(vector_hits),
                ),
                RetrievalTraceEvent(
                    sequence=3,
                    stage=RetrievalStage.FUSION,
                    elapsed_ms=elapsed,
                    candidate_count=len(candidates),
                    attributes=(TraceAttribute(name="method", value="rrf"),),
                ),
                RetrievalTraceEvent(
                    sequence=4,
                    stage=RetrievalStage.SELECT,
                    elapsed_ms=elapsed,
                    candidate_count=len(candidates),
                ),
            ),
        )
        return RetrievalResult(
            query=query,
            candidates=tuple(candidates),
            trace=trace,
            empty_reason=None if candidates else RetrievalEmptyReason.NO_MATCH,
        )

    async def retrieve_full_text(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
    ) -> tuple[RetrievalCandidate, ...]:
        """Expose the Phase 04 BM25 path for contract verification."""
        hits = await self._full_text_hits(context, query)
        return tuple(
            self._candidate(
                hit,
                full_text_score=hit.score,
                full_text_rank=rank,
            )
            for rank, hit in enumerate(hits[: query.top_k], start=1)
        )

    async def retrieve_vector(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
    ) -> tuple[RetrievalCandidate, ...]:
        """Expose the Phase 04 KNN path for contract verification."""
        result = await self._embedding.embed(
            context,
            EmbeddingRequest(
                tenant_id=query.tenant_id,
                model_id=self._embedding_model_id,
                inputs=(EmbeddingInput(id="query", text=query.text),),
                trace_id=query.trace_id,
            ),
        )
        hits = await self._vector_hits(context, query, result.vectors[0].values)
        return tuple(
            self._candidate(
                hit,
                vector_score=hit.score,
                vector_rank=rank,
            )
            for rank, hit in enumerate(hits[: query.top_k], start=1)
        )

    async def _full_text_hits(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
    ) -> list[_SearchHit]:
        response = await self._client.search(
            index=self._index_name,
            query={
                "bool": {
                    "must": [
                        {
                            "match": {
                                "content": {
                                    "query": query.text,
                                    "operator": "or",
                                }
                            }
                        }
                    ],
                    "should": [{"match_phrase": {"content": {"query": query.text, "boost": 2}}}],
                    "filter": self._filters(context, query),
                }
            },
            size=query.top_k,
            source_excludes=["embedding"],
        )
        return self._hits(response)

    async def _vector_hits(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
        query_vector: tuple[float, ...],
    ) -> list[_SearchHit]:
        response = await self._client.search(
            index=self._index_name,
            knn={
                "field": "embedding",
                "query_vector": list(query_vector),
                "k": query.top_k,
                "num_candidates": max(query.top_k, min(query.top_k * 4, 10_000)),
                "filter": {"bool": {"filter": self._filters(context, query)}},
            },
            size=query.top_k,
            source_excludes=["embedding"],
        )
        return self._hits(response)

    def _filters(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
    ) -> list[dict[str, Any]]:
        filters: list[dict[str, Any]] = [
            {"term": {"tenant_id": context.tenant_id}},
            {"terms": {"knowledge_base_id": list(query.knowledge_base_ids)}},
            {"term": {"active": True}},
            {
                "bool": {
                    "should": [
                        {"term": {"document_enabled": True}},
                        {"bool": {"must_not": [{"exists": {"field": "document_enabled"}}]}},
                    ],
                    "minimum_should_match": 1,
                }
            },
            {"bool": {"must_not": [{"term": {"document_deleted": True}}]}},
            {
                "bool": {
                    "should": [
                        {"term": {"owner_id": context.actor_id}},
                        {"term": {"visibility": Visibility.TENANT.value}},
                        {"term": {"allowed_actor_ids": context.actor_id}},
                        *(
                            [{"terms": {"allowed_roles": list(context.roles)}}]
                            if context.roles
                            else []
                        ),
                    ],
                    "minimum_should_match": 1,
                }
            },
        ]
        if query.index_version_ids:
            filters.append({"terms": {"index_version_id": list(query.index_version_ids)}})
        filters.extend(self._metadata_filter(item) for item in query.filters)
        if query.filter_expression is not None:
            filters.append(self._metadata_filter_group(query.filter_expression))
        if query.inferred_filter_expression is not None:
            filters.append(self._metadata_filter_group(query.inferred_filter_expression))
        return filters

    @staticmethod
    def _metadata_filter(item: MetadataFilter) -> dict[str, Any]:
        field_name = item.field.value
        if item.operator is FilterOperator.EQUALS:
            return {"term": {field_name: item.value}}
        if item.operator is FilterOperator.IN:
            return {"terms": {field_name: list(cast(tuple[object, ...], item.value))}}
        operation = "gte" if item.operator is FilterOperator.GREATER_THAN_OR_EQUAL else "lte"
        return {"range": {field_name: {operation: item.value}}}

    @classmethod
    def _metadata_filter_group(cls, group: MetadataFilterGroup) -> dict[str, Any]:
        children = [
            cls._metadata_filter(item)
            if isinstance(item, MetadataFilter)
            else cls._metadata_filter_group(item)
            for item in group.items
        ]
        if group.operator is FilterGroupOperator.AND:
            return {"bool": {"filter": children}}
        if group.operator is FilterGroupOperator.OR:
            return {"bool": {"should": children, "minimum_should_match": 1}}
        return {"bool": {"must_not": children}}

    @staticmethod
    def _hits(response: Any) -> list[_SearchHit]:
        raw_hits = cast(list[dict[str, Any]], response["hits"]["hits"])
        return [
            _SearchHit(
                source=cast(dict[str, Any], hit["_source"]),
                score=float(hit.get("_score") or 0),
            )
            for hit in raw_hits
        ]

    def _fuse(
        self,
        text_hits: list[_SearchHit],
        vector_hits: list[_SearchHit],
        *,
        top_n: int,
    ) -> list[RetrievalCandidate]:
        by_chunk: dict[str, dict[str, Any]] = {}
        for score_name, hits in (("full_text", text_hits), ("vector", vector_hits)):
            for rank, hit in enumerate(hits, start=1):
                chunk_id = str(hit.source["chunk_id"])
                entry = by_chunk.setdefault(
                    chunk_id,
                    {"hit": hit, "rrf": 0.0, "full_text": None, "vector": None},
                )
                entry["rrf"] = float(entry["rrf"]) + 1 / (_RRF_K + rank)
                entry[score_name] = hit.score
        ranked = sorted(by_chunk.values(), key=lambda item: float(item["rrf"]), reverse=True)
        return [
            self._candidate(
                cast(_SearchHit, item["hit"]),
                full_text_score=cast(float | None, item["full_text"]),
                vector_score=cast(float | None, item["vector"]),
                fusion_score=float(item["rrf"]),
            )
            for item in ranked[:top_n]
        ]

    @staticmethod
    def _candidate(
        hit: _SearchHit,
        *,
        full_text_score: float | None = None,
        vector_score: float | None = None,
        fusion_score: float | None = None,
        full_text_rank: int | None = None,
        vector_rank: int | None = None,
    ) -> RetrievalCandidate:
        source = hit.source
        quote = str(source["content"])
        page_number = source.get("page_start")
        bounding_box = ElasticsearchSearchAdapter._bounding_box(source)
        citation = Citation(
            tenant_id=str(source["tenant_id"]),
            knowledge_base_id=str(source["knowledge_base_id"]),
            document_id=str(source["document_id"]),
            document_version_id=str(source["document_version_id"]),
            chunk_id=str(source["chunk_id"]),
            quote=quote,
            page_number=int(page_number) if page_number is not None else None,
            bounding_box=bounding_box,
            source_uri=(
                f"documents/{source['document_id']}/versions/{source['document_version_id']}"
            ),
        )
        final_score = fusion_score if fusion_score is not None else hit.score
        return RetrievalCandidate(
            tenant_id=citation.tenant_id,
            knowledge_base_id=citation.knowledge_base_id,
            document_id=citation.document_id,
            document_version_id=citation.document_version_id,
            chunk_id=citation.chunk_id,
            content=quote,
            score=ScoreBreakdown(
                final_score=final_score,
                full_text_score=full_text_score,
                vector_score=vector_score,
                fusion_score=fusion_score,
                full_text_rank=full_text_rank,
                vector_rank=vector_rank,
            ),
            citation=citation,
        )

    @staticmethod
    def _source(record: IndexRecord, *, active: bool) -> dict[str, Any]:
        bounding_box = record.metadata.bounding_box
        return {
            "index_version_id": record.index_version_id,
            "tenant_id": record.tenant_id,
            "knowledge_base_id": record.knowledge_base_id,
            "owner_id": record.owner_id,
            "visibility": record.visibility.value,
            "document_id": record.document_id,
            "document_version_id": record.document_version_id,
            "chunk_id": record.chunk_id,
            "content": record.content,
            "media_type": record.media_type,
            "created_at": record.created_at.isoformat(),
            "active": active,
            "allowed_actor_ids": list(record.allowed_actor_ids),
            "allowed_roles": list(record.allowed_roles),
            "document_enabled": record.document_enabled,
            "document_deleted": record.document_deleted,
            "lifecycle_fencing_token": 0,
            "heading_path": list(record.metadata.heading_path),
            "page_start": record.metadata.page_start,
            "page_end": record.metadata.page_end,
            "language": record.metadata.language,
            "source_order_start": record.metadata.source_order_start,
            "source_order_end": record.metadata.source_order_end,
            "block_kinds": [kind.value for kind in record.metadata.block_kinds],
            "bbox_x0": bounding_box.x0 if bounding_box is not None else None,
            "bbox_y0": bounding_box.y0 if bounding_box is not None else None,
            "bbox_x1": bounding_box.x1 if bounding_box is not None else None,
            "bbox_y1": bounding_box.y1 if bounding_box is not None else None,
            "bbox_coordinate_space": (
                bounding_box.coordinate_space.value if bounding_box is not None else None
            ),
            "contains_table": record.metadata.contains_table,
            "contains_image": record.metadata.contains_image,
            "parser_name": record.metadata.parser_name,
            "parser_version": record.metadata.parser_version,
            "chunk_strategy_id": record.metadata.chunk_strategy_id,
            "chunk_strategy_version": record.metadata.chunk_strategy_version,
            "embedding": list(record.embedding),
        }

    @staticmethod
    def _bounding_box(source: dict[str, Any]) -> BoundingBox | None:
        values = (
            source.get("bbox_x0"),
            source.get("bbox_y0"),
            source.get("bbox_x1"),
            source.get("bbox_y1"),
            source.get("bbox_coordinate_space"),
        )
        if any(value is None for value in values):
            return None
        x0, y0, x1, y1, coordinate_space = values
        try:
            return BoundingBox(
                x0=float(str(x0)),
                y0=float(str(y0)),
                x1=float(str(x1)),
                y1=float(str(y1)),
                coordinate_space=CoordinateSpace(str(coordinate_space)),
            )
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _document_key(record: IndexRecord) -> str:
        return f"{record.tenant_id}:{record.index_version_id}:{record.chunk_id}"

    @staticmethod
    def _require_tenant(context: AuthorizationContext, tenant_id: str) -> None:
        if context.tenant_id != tenant_id:
            raise KnowledgeAuthorizationError(reason_code="tenant_mismatch")


class _SearchHit:
    """Small internal hit shape insulated from Elasticsearch response classes."""

    __slots__ = ("score", "source")

    def __init__(self, *, source: dict[str, Any], score: float) -> None:
        self.source = source
        self.score = score
