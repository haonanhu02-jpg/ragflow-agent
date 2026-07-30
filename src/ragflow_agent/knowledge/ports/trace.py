"""Knowledge lifecycle trace contract."""

from datetime import datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import Field, field_validator

from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.retrieval import TraceAttribute


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
