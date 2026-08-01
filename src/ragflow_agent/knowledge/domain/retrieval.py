"""Backend-neutral retrieval, citation, trace, and index metadata protocols."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from hashlib import sha256

from pydantic import Field, field_validator, model_validator

from ragflow_agent.knowledge.domain.authorization import Visibility
from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.chunk import BoundingBox, ChunkMetadata

RETRIEVAL_SCHEMA_VERSION = 2
INDEX_SCHEMA_VERSION = 1

type FilterScalar = str | int | float | bool


class MetadataField(StrEnum):
    """Portable metadata fields allowed before a search backend is selected."""

    DOCUMENT_ID = "document_id"
    DOCUMENT_VERSION_ID = "document_version_id"
    MEDIA_TYPE = "media_type"
    LANGUAGE = "language"
    CREATED_AT = "created_at"
    HEADING_PATH = "heading_path"
    CONTAINS_TABLE = "contains_table"
    CONTAINS_IMAGE = "contains_image"
    CHUNK_STRATEGY_ID = "chunk_strategy_id"


class FilterOperator(StrEnum):
    """Small backend-independent filter vocabulary."""

    EQUALS = "equals"
    IN = "in"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN_OR_EQUAL = "lte"


class MetadataFilter(KnowledgeModel):
    """Typed filter expression; adapters translate it to their own DSL."""

    field: MetadataField
    operator: FilterOperator
    value: FilterScalar | tuple[FilterScalar, ...]

    @model_validator(mode="after")
    def validate_operator_value(self) -> MetadataFilter:
        is_collection = isinstance(self.value, tuple)
        if self.operator is FilterOperator.IN and (not is_collection or not self.value):
            raise ValueError("in filters require a non-empty tuple")
        if self.operator is not FilterOperator.IN and is_collection:
            raise ValueError("only in filters accept tuple values")
        return self


class FilterGroupOperator(StrEnum):
    """Boolean operators supported by the backend-neutral Filter AST."""

    AND = "and"
    OR = "or"
    NOT = "not"


class MetadataFilterGroup(KnowledgeModel):
    """Recursive, validated metadata expression compiled only by adapters."""

    operator: FilterGroupOperator = FilterGroupOperator.AND
    items: tuple[MetadataFilter | MetadataFilterGroup, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def not_has_exactly_one_child(self) -> MetadataFilterGroup:
        if self.operator is FilterGroupOperator.NOT and len(self.items) != 1:
            raise ValueError("not filter groups require exactly one child")
        return self


class RetrievalQuery(KnowledgeModel):
    """Shared fixed-RAG and KnowledgeBaseTool query request."""

    schema_version: int = RETRIEVAL_SCHEMA_VERSION
    tenant_id: NonEmptyStr
    text: NonEmptyStr
    knowledge_base_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    top_k: int = Field(default=100, ge=1, le=10_000)
    top_n: int = Field(default=10, ge=1, le=1_000)
    filters: tuple[MetadataFilter, ...] = ()
    filter_expression: MetadataFilterGroup | None = None
    inferred_filter_expression: MetadataFilterGroup | None = None
    index_version_ids: tuple[NonEmptyStr, ...] = ()
    history: tuple[str, ...] = ()
    target_languages: tuple[NonEmptyStr, ...] = ()
    trace_id: NonEmptyStr
    request_id: NonEmptyStr | None = None

    @field_validator("knowledge_base_ids")
    @classmethod
    def knowledge_base_ids_are_unique(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("knowledge_base_ids must be unique")
        return value

    @model_validator(mode="after")
    def top_n_does_not_exceed_top_k(self) -> RetrievalQuery:
        if self.top_n > self.top_k:
            raise ValueError("top_n cannot exceed top_k")
        return self


class QueryVariantKind(StrEnum):
    """Auditable source of one retrieval query variant."""

    CANONICAL = "canonical"
    REWRITE = "rewrite"
    TRANSLATION = "translation"
    KEYWORD = "keyword"


class QueryVariant(KnowledgeModel):
    """Bounded query variation that never carries authorization state."""

    text: NonEmptyStr
    kind: QueryVariantKind
    language: str | None = None
    provider: str | None = None


class ScoreBreakdown(KnowledgeModel):
    """Explainable scores without assuming backend score ranges."""

    final_score: float
    full_text_score: float | None = None
    vector_score: float | None = None
    fusion_score: float | None = None
    rerank_score: float | None = None
    full_text_rank: int | None = Field(default=None, ge=1)
    vector_rank: int | None = Field(default=None, ge=1)
    fusion_rank: int | None = Field(default=None, ge=1)
    rerank_rank: int | None = Field(default=None, ge=1)
    final_rank: int | None = Field(default=None, ge=1)


class Citation(KnowledgeModel):
    """Version-bound source reference returned with retrieved evidence."""

    schema_version: int = RETRIEVAL_SCHEMA_VERSION
    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    document_id: NonEmptyStr
    document_version_id: NonEmptyStr
    chunk_id: NonEmptyStr
    quote: NonEmptyStr
    page_number: int | None = Field(default=None, ge=1)
    bounding_box: BoundingBox | None = None
    source_uri: str | None = None
    media_kind: str | None = None
    time_start_seconds: float | None = Field(default=None, ge=0)
    time_end_seconds: float | None = Field(default=None, ge=0)
    observed_at: datetime | None = None

    @model_validator(mode="after")
    def bounding_box_requires_page(self) -> Citation:
        if self.bounding_box is not None and self.page_number is None:
            raise ValueError("citation bounding_box requires page_number")
        if (self.time_start_seconds is None) != (self.time_end_seconds is None):
            raise ValueError("citation time range requires both endpoints")
        if (
            self.time_start_seconds is not None
            and self.time_end_seconds is not None
            and self.time_end_seconds <= self.time_start_seconds
        ):
            raise ValueError("citation time range must have positive duration")
        if self.observed_at is not None and self.observed_at.utcoffset() is None:
            raise ValueError("citation observed_at must be timezone-aware")
        return self


class RetrievalCandidate(KnowledgeModel):
    """One ranked evidence item and its exact citation."""

    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    document_id: NonEmptyStr
    document_version_id: NonEmptyStr
    chunk_id: NonEmptyStr
    content: NonEmptyStr
    score: ScoreBreakdown
    citation: Citation

    @model_validator(mode="after")
    def citation_matches_candidate(self) -> RetrievalCandidate:
        candidate_scope = (
            self.tenant_id,
            self.knowledge_base_id,
            self.document_id,
            self.document_version_id,
            self.chunk_id,
        )
        citation_scope = (
            self.citation.tenant_id,
            self.citation.knowledge_base_id,
            self.citation.document_id,
            self.citation.document_version_id,
            self.citation.chunk_id,
        )
        if candidate_scope != citation_scope:
            raise ValueError("candidate and citation scope must match")
        return self


class RetrievalStage(StrEnum):
    """Trace stages shared by simple and advanced retrieval."""

    QUERY = "query"
    PREPROCESS = "preprocess"
    REWRITE = "rewrite"
    TRANSLATE = "translate"
    EXPAND = "expand"
    AUTHORIZATION = "authorization"
    FILTER = "filter"
    FULL_TEXT = "full_text"
    VECTOR = "vector"
    FUSION = "fusion"
    RERANK = "rerank"
    CLEAN = "clean"
    FALLBACK = "fallback"
    SELECT = "select"
    TRACE_PERSIST = "trace_persist"


class TraceAttribute(KnowledgeModel):
    """Typed trace attribute that avoids unbounded dictionaries."""

    name: NonEmptyStr
    value: FilterScalar


class RetrievalTraceEvent(KnowledgeModel):
    """One ordered retrieval stage observation."""

    sequence: int = Field(ge=0)
    stage: RetrievalStage
    elapsed_ms: float = Field(ge=0)
    candidate_count: int = Field(ge=0)
    attributes: tuple[TraceAttribute, ...] = ()


class RetrievalCandidateTrace(KnowledgeModel):
    """Content-free ranking evidence persisted for audit and evaluation."""

    knowledge_base_id: NonEmptyStr
    document_id: NonEmptyStr
    document_version_id: NonEmptyStr
    chunk_id: NonEmptyStr
    full_text_rank: int | None = Field(default=None, ge=1)
    full_text_score: float | None = None
    vector_rank: int | None = Field(default=None, ge=1)
    vector_score: float | None = None
    fusion_rank: int | None = Field(default=None, ge=1)
    fusion_score: float | None = None
    rerank_rank: int | None = Field(default=None, ge=1)
    rerank_score: float | None = None
    final_rank: int | None = Field(default=None, ge=1)
    selected: bool = False
    exclusion_reason: str | None = None


class RetrievalFallbackStep(KnowledgeModel):
    """One finite fallback attempt without any mutable authorization scope."""

    attempt: int = Field(ge=1)
    mode: NonEmptyStr
    reason: NonEmptyStr
    candidate_top_k: int = Field(ge=1)
    threshold: float
    inferred_filter_removed: bool = False
    result_count: int = Field(ge=0)


class RetrievalTraceStatus(StrEnum):
    """Final retrieval state, intentionally separating no evidence and failure."""

    SUCCESS = "success"
    NO_EVIDENCE = "no_evidence"
    FAILED = "failed"


class RetrievalTrace(KnowledgeModel):
    """Versioned trace sufficient to reconstruct retrieval selection."""

    schema_version: int = RETRIEVAL_SCHEMA_VERSION
    trace_id: NonEmptyStr
    request_id: NonEmptyStr | None = None
    tenant_id: NonEmptyStr
    original_query: NonEmptyStr | None = Field(default=None, exclude=True)
    canonical_query: NonEmptyStr | None = Field(default=None, exclude=True)
    query_digest: str = ""
    canonical_query_digest: str = ""
    rewritten_queries: tuple[str, ...] = Field(default=(), exclude=True)
    query_variant_digests: tuple[NonEmptyStr, ...] = ()
    authorization_applied: bool
    events: tuple[RetrievalTraceEvent, ...]
    knowledge_base_ids: tuple[NonEmptyStr, ...] = ()
    index_version_ids: tuple[NonEmptyStr, ...] = ()
    config_version: NonEmptyStr = "retrieval-v2"
    provider_ids: tuple[NonEmptyStr, ...] = ()
    filter_summary: tuple[str, ...] = ()
    candidates: tuple[RetrievalCandidateTrace, ...] = ()
    fallback_steps: tuple[RetrievalFallbackStep, ...] = ()
    status: RetrievalTraceStatus = RetrievalTraceStatus.SUCCESS
    error_code: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def event_sequences_are_ordered(self) -> RetrievalTrace:
        sequences = [event.sequence for event in self.events]
        if len(sequences) != len(set(sequences)) or sequences != sorted(sequences):
            raise ValueError("retrieval trace sequences must be unique and ordered")
        original = self.original_query or ""
        canonical = self.canonical_query or original
        if not self.query_digest and original:
            object.__setattr__(
                self,
                "query_digest",
                sha256(original.encode("utf-8")).hexdigest(),
            )
        if not self.canonical_query_digest and canonical:
            object.__setattr__(
                self,
                "canonical_query_digest",
                sha256(canonical.encode("utf-8")).hexdigest(),
            )
        if self.started_at and self.completed_at and self.completed_at < self.started_at:
            raise ValueError("retrieval trace completion cannot precede start")
        if self.completed_at and self.expires_at and self.expires_at <= self.completed_at:
            raise ValueError("retrieval trace expiry must follow completion")
        return self


class RetrievalEmptyReason(StrEnum):
    """Stable reasons for successful queries with no returned evidence."""

    NO_MATCH = "no_match"
    PERMISSION_FILTERED = "permission_filtered"
    BELOW_THRESHOLD = "below_threshold"
    NO_EVIDENCE = "no_evidence"


class RetrievalResult(KnowledgeModel):
    """Shared structured query outcome consumed by fixed RAG and Agent Tool."""

    schema_version: int = RETRIEVAL_SCHEMA_VERSION
    query: RetrievalQuery
    candidates: tuple[RetrievalCandidate, ...]
    trace: RetrievalTrace
    empty_reason: RetrievalEmptyReason | None = None

    @model_validator(mode="after")
    def validate_result_scope_and_empty_state(self) -> RetrievalResult:
        if self.trace.trace_id != self.query.trace_id:
            raise ValueError("query and trace identifiers must match")
        if self.trace.tenant_id != self.query.tenant_id:
            raise ValueError("query and trace tenant must match")
        if self.trace.original_query is not None and self.trace.original_query != self.query.text:
            raise ValueError("trace original_query must match query text")
        if (
            self.query.request_id is not None
            and self.trace.request_id is not None
            and self.trace.request_id != self.query.request_id
        ):
            raise ValueError("query and trace request identifiers must match")
        if self.candidates and self.empty_reason is not None:
            raise ValueError("non-empty results cannot have empty_reason")
        if not self.candidates and self.empty_reason is None:
            raise ValueError("empty results require empty_reason")
        allowed_knowledge_bases = set(self.query.knowledge_base_ids)
        for candidate in self.candidates:
            if candidate.tenant_id != self.query.tenant_id:
                raise ValueError("candidate tenant must match query tenant")
            if candidate.knowledge_base_id not in allowed_knowledge_bases:
                raise ValueError("candidate knowledge base was not requested")
        return self

    @property
    def citations(self) -> tuple[Citation, ...]:
        return tuple(candidate.citation for candidate in self.candidates)


class IndexVersionStatus(StrEnum):
    """Index-version lifecycle independent from index aliases."""

    BUILDING = "building"
    READY = "ready"
    ACTIVE = "active"
    FAILED = "failed"
    RETIRED = "retired"


class EmbeddingMetadata(KnowledgeModel):
    """Embedding compatibility identity stored with an index version."""

    model_id: NonEmptyStr
    dimensions: int = Field(ge=1)
    normalized: bool


class IndexVersion(KnowledgeModel):
    """Tenant and knowledge-base scoped index compatibility contract."""

    schema_version: int = INDEX_SCHEMA_VERSION
    id: NonEmptyStr
    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    document_id: str | None = None
    generation: int | None = Field(default=None, ge=1)
    embedding: EmbeddingMetadata
    status: IndexVersionStatus
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def created_at_is_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("index-version created_at must be timezone-aware")
        return value


class IndexRecord(KnowledgeModel):
    """Portable search write model for one version-bound ChunkRecord."""

    schema_version: int = INDEX_SCHEMA_VERSION
    index_version_id: NonEmptyStr
    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    owner_id: NonEmptyStr
    visibility: Visibility
    allowed_actor_ids: tuple[NonEmptyStr, ...] = ()
    allowed_roles: tuple[NonEmptyStr, ...] = ()
    document_enabled: bool = True
    document_deleted: bool = False
    document_id: NonEmptyStr
    document_version_id: NonEmptyStr
    chunk_id: NonEmptyStr
    content: NonEmptyStr
    media_type: NonEmptyStr
    created_at: datetime
    embedding: tuple[float, ...] = Field(min_length=1)
    metadata: ChunkMetadata

    @field_validator("created_at")
    @classmethod
    def created_at_is_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("index-record created_at must be timezone-aware")
        return value
