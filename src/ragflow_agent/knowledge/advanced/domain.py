"""Strict, provenance-preserving contracts shared by all advanced capabilities."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from hashlib import sha256

from pydantic import Field, field_validator, model_validator

from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr

ADVANCED_SCHEMA_VERSION = 1


class AdvancedCapability(StrEnum):
    KEYWORDS = "keywords"
    QUESTIONS = "questions"
    SUMMARIES = "summaries"
    TOC = "toc"
    PARENT_CHILD = "parent_child"
    MULTIMODAL = "multimodal"
    GRAPHRAG = "graphrag"
    RAPTOR = "raptor"
    TEMPORAL = "temporal"


class AdvancedBuildStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    CANCELLED = "cancelled"
    FAILED = "failed"
    SUCCEEDED = "succeeded"


class AdvancedResourceBudget(KnowledgeModel):
    max_source_chunks: int = Field(default=5_000, ge=1, le=5_000)
    max_active_runtime_seconds: int = Field(default=900, ge=1, le=900)
    max_provider_calls: int = Field(default=500, ge=0, le=500)
    max_generated_tokens: int = Field(default=300_000, ge=0, le=300_000)
    max_keywords_per_chunk: int = Field(default=10, ge=1, le=10)
    max_questions_per_chunk: int = Field(default=5, ge=1, le=5)
    max_parent_context_tokens: int = Field(default=6_000, ge=1, le=6_000)
    max_graph_entities: int = Field(default=20_000, ge=1, le=20_000)
    max_graph_edges: int = Field(default=50_000, ge=1, le=50_000)
    max_raptor_levels: int = Field(default=4, ge=1, le=4)
    max_image_bytes: int = Field(default=20 * 1024 * 1024, ge=1, le=20 * 1024 * 1024)
    max_image_pixels: int = Field(default=25_000_000, ge=1, le=25_000_000)
    max_audio_seconds: int = Field(default=1_800, ge=1, le=1_800)
    max_timeseries_points: int = Field(default=1_000_000, ge=1, le=1_000_000)


class AdvancedIndexManifest(KnowledgeModel):
    schema_version: int = ADVANCED_SCHEMA_VERSION
    capability: AdvancedCapability
    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    build_version: NonEmptyStr
    document_version_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    created_at: datetime
    content_hash: NonEmptyStr
    complete: bool = True

    @field_validator("created_at")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value


class AdvancedArtifact(KnowledgeModel):
    schema_version: int = ADVANCED_SCHEMA_VERSION
    id: NonEmptyStr
    capability: AdvancedCapability
    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    document_id: NonEmptyStr
    document_version_id: NonEmptyStr
    build_version: NonEmptyStr
    source_chunk_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    text: NonEmptyStr
    attributes: tuple[tuple[NonEmptyStr, str], ...] = ()
    created_at: datetime

    @field_validator("source_chunk_ids")
    @classmethod
    def sources_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("source_chunk_ids must be unique")
        return value

    @field_validator("created_at")
    @classmethod
    def created_at_is_aware(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value


class AdvancedBuild(KnowledgeModel):
    id: NonEmptyStr
    idempotency_key: NonEmptyStr
    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    capability: AdvancedCapability
    build_version: NonEmptyStr
    document_version_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    status: AdvancedBuildStatus = AdvancedBuildStatus.PENDING
    processed_chunks: int = Field(default=0, ge=0)
    provider_calls: int = Field(default=0, ge=0)
    generated_tokens: int = Field(default=0, ge=0)
    cancellation_requested: bool = False
    error_code: str | None = None
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def updated_at_is_aware(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("updated_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def terminal_error_is_consistent(self) -> AdvancedBuild:
        if self.status is AdvancedBuildStatus.FAILED and self.error_code is None:
            raise ValueError("failed builds require error_code")
        return self


def derive_artifact_id(
    capability: AdvancedCapability,
    *,
    tenant_id: str,
    document_version_id: str,
    build_version: str,
    source_chunk_ids: tuple[str, ...],
    text: str,
) -> str:
    """Derive an idempotent identity from scope, version, sources, and content."""
    values = (tenant_id.strip(), document_version_id.strip(), build_version.strip(), text.strip())
    if any(not value for value in values) or not source_chunk_ids:
        raise ValueError("artifact identity inputs must not be empty")
    payload = "\x1f".join((capability.value, *values[:3], *source_chunk_ids, values[3]))
    return f"adv_{sha256(payload.encode('utf-8')).hexdigest()[:32]}"
