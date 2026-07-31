"""Knowledge lifecycle trace contract."""

from datetime import datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import Field, field_validator

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.retrieval import RetrievalTrace, TraceAttribute


class KnowledgeTraceKind(StrEnum):
    """Auditable knowledge operation categories."""

    AUTHORIZATION = "authorization"
    KNOWLEDGE_BASE = "knowledge_base"
    DOCUMENT = "document"
    INGESTION = "ingestion"
    RETRIEVAL = "retrieval"
    INDEX = "index"


class KnowledgeTraceEvent(KnowledgeModel):
    """Versioned, tenant-bound application trace event."""

    schema_version: int = 1
    trace_id: NonEmptyStr
    request_id: NonEmptyStr
    tenant_id: NonEmptyStr
    actor_id: NonEmptyStr
    kind: KnowledgeTraceKind
    action: NonEmptyStr
    resource_type: NonEmptyStr
    resource_id: NonEmptyStr
    occurred_at: datetime
    attributes: tuple[TraceAttribute, ...] = Field(default_factory=tuple)

    @field_validator("occurred_at")
    @classmethod
    def occurred_at_is_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("trace occurred_at must be timezone-aware")
        return value


@runtime_checkable
class KnowledgeTracePort(Protocol):
    """Record an event without selecting a persistence or observability backend."""

    async def record(self, event: KnowledgeTraceEvent) -> None: ...


@runtime_checkable
class RetrievalTraceStorePort(Protocol):
    """Persist minimized tenant-scoped retrieval traces with explicit cleanup."""

    async def save(self, trace: RetrievalTrace) -> None: ...

    async def get(
        self,
        context: AuthorizationContext,
        trace_id: str,
    ) -> RetrievalTrace | None: ...

    async def delete_expired(self, *, before: datetime) -> int: ...


@runtime_checkable
class RetrievalTraceMetricsPort(Protocol):
    """Observable counter boundary for non-blocking trace write failures."""

    def record_write_failure(self, *, tenant_id: str, reason: str) -> None: ...
