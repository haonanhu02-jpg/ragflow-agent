"""Tenant-scoped ingestion job, task, state, and queue-envelope contracts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError

INGESTION_SCHEMA_VERSION = 1


class IngestionStatus(StrEnum):
    """Shared lifecycle for an ingestion job or stage task."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IngestionStage(StrEnum):
    """Stable pipeline stages; implementations arrive in later phases."""

    REGISTER = "register"
    PARSE = "parse"
    CHUNK = "chunk"
    EMBED = "embed"
    INDEX = "index"


TERMINAL_INGESTION_STATUSES = frozenset(
    {
        IngestionStatus.SUCCEEDED,
        IngestionStatus.FAILED,
        IngestionStatus.CANCELLED,
    }
)
_TRANSITIONS: dict[IngestionStatus, frozenset[IngestionStatus]] = {
    IngestionStatus.PENDING: frozenset({IngestionStatus.RUNNING, IngestionStatus.CANCELLED}),
    IngestionStatus.RUNNING: frozenset(
        {
            IngestionStatus.SUCCEEDED,
            IngestionStatus.FAILED,
            IngestionStatus.CANCELLED,
        }
    ),
    IngestionStatus.SUCCEEDED: frozenset(),
    IngestionStatus.FAILED: frozenset(),
    IngestionStatus.CANCELLED: frozenset(),
}


class IngestionError(KnowledgeModel):
    """Stable failure recorded in the database, not only in queue metadata."""

    code: NonEmptyStr
    message: NonEmptyStr
    retryable: bool


class IngestionJob(KnowledgeModel):
    """Business record for building one immutable document version."""

    schema_version: int = INGESTION_SCHEMA_VERSION
    id: NonEmptyStr
    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    document_id: NonEmptyStr
    document_version_id: NonEmptyStr
    requested_by: NonEmptyStr
    idempotency_key: NonEmptyStr
    trace_id: NonEmptyStr
    status: IngestionStatus = IngestionStatus.PENDING
    progress: float = Field(default=0, ge=0, le=1)
    error: IngestionError | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def timestamps_are_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("ingestion timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_job(self) -> IngestionJob:
        _validate_ingestion_record(
            status=self.status,
            progress=self.progress,
            error=self.error,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
        return self


class IngestionTask(KnowledgeModel):
    """One retry-aware pipeline stage belonging to an IngestionJob."""

    schema_version: int = INGESTION_SCHEMA_VERSION
    id: NonEmptyStr
    tenant_id: NonEmptyStr
    job_id: NonEmptyStr
    document_version_id: NonEmptyStr
    stage: IngestionStage
    attempt: int = Field(default=1, ge=1)
    idempotency_key: NonEmptyStr
    trace_id: NonEmptyStr
    status: IngestionStatus = IngestionStatus.PENDING
    progress: float = Field(default=0, ge=0, le=1)
    error: IngestionError | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def timestamps_are_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("ingestion timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_task(self) -> IngestionTask:
        _validate_ingestion_record(
            status=self.status,
            progress=self.progress,
            error=self.error,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
        return self


class IngestionEnvelope(KnowledgeModel):
    """Versioned queue payload that carries all isolation and recovery identities."""

    schema_version: int = INGESTION_SCHEMA_VERSION
    message_id: NonEmptyStr
    tenant_id: NonEmptyStr
    job_id: NonEmptyStr
    task_id: NonEmptyStr
    document_version_id: NonEmptyStr
    stage: IngestionStage
    attempt: int = Field(ge=1)
    idempotency_key: NonEmptyStr
    trace_id: NonEmptyStr
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def created_at_is_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("envelope created_at must be timezone-aware")
        return value

    @classmethod
    def from_task(
        cls,
        task: IngestionTask,
        *,
        message_id: str,
        created_at: datetime,
    ) -> IngestionEnvelope:
        return cls(
            message_id=message_id,
            tenant_id=task.tenant_id,
            job_id=task.job_id,
            task_id=task.id,
            document_version_id=task.document_version_id,
            stage=task.stage,
            attempt=task.attempt,
            idempotency_key=task.idempotency_key,
            trace_id=task.trace_id,
            created_at=created_at,
        )


def transition_ingestion[IngestionRecord: (IngestionJob, IngestionTask)](
    record: IngestionRecord,
    target: IngestionStatus,
    *,
    progress: float,
    changed_at: datetime,
    error: IngestionError | None = None,
) -> IngestionRecord:
    """Move a job/task monotonically along a declared lifecycle edge."""
    if changed_at < record.updated_at:
        raise KnowledgeConflictError(
            "ingestion timestamp cannot move backwards",
            error_code="ingestion_timestamp_regression",
        )
    if target is record.status:
        if progress == record.progress and error == record.error:
            return record
        raise KnowledgeConflictError(
            "same-state ingestion updates must be idempotent",
            error_code="ingestion_duplicate_conflict",
        )
    if target not in _TRANSITIONS[record.status]:
        raise KnowledgeConflictError(
            "ingestion transition is not allowed",
            error_code="ingestion_transition_invalid",
            details={"current": record.status.value, "target": target.value},
        )
    if progress < record.progress:
        raise KnowledgeConflictError(
            "ingestion progress cannot decrease",
            error_code="ingestion_progress_regression",
        )
    return type(record).model_validate(
        {
            **record.model_dump(),
            "status": target,
            "progress": progress,
            "error": error,
            "updated_at": changed_at,
        }
    )


def retry_ingestion_task(
    task: IngestionTask,
    *,
    changed_at: datetime,
) -> IngestionTask:
    """Start a new attempt after a retryable failed stage without losing progress."""
    if changed_at < task.updated_at:
        raise KnowledgeConflictError(
            "ingestion timestamp cannot move backwards",
            error_code="ingestion_timestamp_regression",
        )
    if task.status is not IngestionStatus.FAILED or task.error is None or not task.error.retryable:
        raise KnowledgeConflictError(
            "only retryable failed tasks can start another attempt",
            error_code="ingestion_retry_not_allowed",
        )
    return IngestionTask.model_validate(
        {
            **task.model_dump(),
            "status": IngestionStatus.RUNNING,
            "attempt": task.attempt + 1,
            "error": None,
            "updated_at": changed_at,
        }
    )


def _validate_ingestion_record(
    *,
    status: IngestionStatus,
    progress: float,
    error: IngestionError | None,
    created_at: datetime,
    updated_at: datetime,
) -> None:
    if updated_at < created_at:
        raise ValueError("updated_at cannot precede created_at")
    if status is IngestionStatus.SUCCEEDED and progress != 1:
        raise ValueError("succeeded ingestion records require progress=1")
    if status is IngestionStatus.FAILED and error is None:
        raise ValueError("failed ingestion records require an error")
    if status is not IngestionStatus.FAILED and error is not None:
        raise ValueError("only failed ingestion records can carry an error")
