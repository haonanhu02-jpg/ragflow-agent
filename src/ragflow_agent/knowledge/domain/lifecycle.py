"""Authoritative Phase 07 lifecycle, outbox, retry, and batch contracts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError

LIFECYCLE_SCHEMA_VERSION = 1


class LifecycleOperationKind(StrEnum):
    UPDATE = "update"
    REPARSE = "reparse"
    REBUILD = "rebuild"
    ACTIVATE = "activate"
    ROLLBACK = "rollback"
    DELETE = "delete"
    RESTORE = "restore"
    PURGE = "purge"
    RECONCILE = "reconcile"


class LifecycleOperationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_RETRY = "waiting_retry"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


TERMINAL_LIFECYCLE_STATUSES = frozenset(
    {
        LifecycleOperationStatus.CANCELLED,
        LifecycleOperationStatus.SUCCEEDED,
        LifecycleOperationStatus.FAILED,
        LifecycleOperationStatus.DEAD_LETTER,
    }
)


class LifecycleStep(StrEnum):
    REGISTER = "register"
    STORE_OBJECT = "store_object"
    PARSE = "parse"
    CHUNK = "chunk"
    EMBED = "embed"
    WRITE_INDEX = "write_index"
    VALIDATE = "validate"
    PROMOTE = "promote"
    ACTIVATE = "activate"
    RETIRE_PREVIOUS = "retire_previous"
    MARK_INVISIBLE = "mark_invisible"
    CLEAN_INDEX = "clean_index"
    CLEAN_OBJECTS = "clean_objects"
    COMPLETE = "complete"


class LifecycleStepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class FailureClass(StrEnum):
    TRANSIENT = "transient"
    CONCURRENCY = "concurrency"
    PERMANENT = "permanent"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class LifecycleError(KnowledgeModel):
    classification: FailureClass
    code: NonEmptyStr
    message: NonEmptyStr
    retryable: bool


class LifecycleStepState(KnowledgeModel):
    step: LifecycleStep
    status: LifecycleStepStatus = LifecycleStepStatus.PENDING
    attempts: int = Field(default=0, ge=0)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    last_error: LifecycleError | None = None

    @field_validator("started_at", "completed_at")
    @classmethod
    def timestamps_are_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("lifecycle step timestamps must be timezone-aware")
        return value


class LifecycleOperation(KnowledgeModel):
    """PostgreSQL-authoritative record for one cross-store state transition."""

    schema_version: int = LIFECYCLE_SCHEMA_VERSION
    id: NonEmptyStr
    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    document_id: NonEmptyStr
    version_id: NonEmptyStr
    kind: LifecycleOperationKind
    idempotency_key: NonEmptyStr
    actor_id: NonEmptyStr
    reason: NonEmptyStr
    request_id: NonEmptyStr
    status: LifecycleOperationStatus = LifecycleOperationStatus.PENDING
    current_step: LifecycleStep = LifecycleStep.REGISTER
    attempts: int = Field(default=0, ge=0)
    expected_document_revision: int = Field(ge=0)
    fencing_token: int = Field(ge=1)
    previous_version_id: str | None = None
    index_version_id: str | None = None
    batch_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    progress: float = Field(default=0, ge=0, le=1)
    next_attempt_at: datetime | None = None
    purge_after: datetime | None = None
    steps: tuple[LifecycleStepState, ...] = ()
    error: LifecycleError | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", "next_attempt_at", "purge_after")
    @classmethod
    def timestamps_are_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("lifecycle timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_operation(self) -> LifecycleOperation:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot precede created_at")
        if (
            self.status
            in {
                LifecycleOperationStatus.FAILED,
                LifecycleOperationStatus.DEAD_LETTER,
            }
            and self.error is None
        ):
            raise ValueError("failed lifecycle operations require an error")
        if (
            self.status
            not in {
                LifecycleOperationStatus.FAILED,
                LifecycleOperationStatus.DEAD_LETTER,
                LifecycleOperationStatus.WAITING_RETRY,
            }
            and self.error is not None
        ):
            raise ValueError("only failed or retry-waiting operations may carry an error")
        return self


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"


class LifecycleOutboxEvent(KnowledgeModel):
    schema_version: int = LIFECYCLE_SCHEMA_VERSION
    id: NonEmptyStr
    tenant_id: NonEmptyStr
    operation_id: NonEmptyStr
    aggregate_type: NonEmptyStr = "document"
    aggregate_id: NonEmptyStr
    event_type: NonEmptyStr
    idempotency_key: NonEmptyStr
    payload: dict[str, object] = Field(default_factory=dict)
    status: OutboxStatus = OutboxStatus.PENDING
    attempts: int = Field(default=0, ge=0)
    available_at: datetime
    published_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("available_at", "published_at", "created_at", "updated_at")
    @classmethod
    def timestamps_are_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("outbox timestamps must be timezone-aware")
        return value


class LifecycleBatchStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"


class LifecycleBatch(KnowledgeModel):
    schema_version: int = LIFECYCLE_SCHEMA_VERSION
    id: NonEmptyStr
    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    kind: LifecycleOperationKind
    requested_by: NonEmptyStr
    idempotency_key: NonEmptyStr
    status: LifecycleBatchStatus = LifecycleBatchStatus.PENDING
    operation_ids: tuple[NonEmptyStr, ...] = Field(min_length=1, max_length=1000)
    concurrency: int = Field(default=2, ge=1, le=100)
    succeeded: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    cancelled: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def timestamps_are_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("batch timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def counts_fit_batch(self) -> LifecycleBatch:
        if len(set(self.operation_ids)) != len(self.operation_ids):
            raise ValueError("batch operation ids must be unique")
        if self.succeeded + self.failed + self.cancelled > len(self.operation_ids):
            raise ValueError("batch terminal counts exceed operation count")
        return self


class IndexGeneration(KnowledgeModel):
    """Tenant/knowledge-base scoped physical index generation."""

    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    generation: int = Field(ge=1)
    physical_index: NonEmptyStr
    read_alias: NonEmptyStr
    write_alias: NonEmptyStr
    fencing_token: int = Field(ge=1)
    expected_chunks: int = Field(ge=0)
    mapping_version: NonEmptyStr
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def created_at_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("index generation timestamp must be timezone-aware")
        return value


class IndexGenerationValidation(KnowledgeModel):
    physical_index: NonEmptyStr
    mapping_valid: bool
    chunk_count: int = Field(ge=0)
    tenant_scope_valid: bool
    knowledge_base_scope_valid: bool
    lifecycle_fields_valid: bool
    sample_query_valid: bool
    checksum: NonEmptyStr

    @property
    def healthy(self) -> bool:
        return (
            self.mapping_valid
            and self.tenant_scope_valid
            and self.knowledge_base_scope_valid
            and self.lifecycle_fields_valid
            and self.sample_query_valid
        )


def update_step(
    operation: LifecycleOperation,
    step: LifecycleStep,
    status: LifecycleStepStatus,
    *,
    changed_at: datetime,
    error: LifecycleError | None = None,
) -> LifecycleOperation:
    """Persist a monotonic, idempotent step snapshot inside an operation."""
    states = {item.step: item for item in operation.steps}
    current = states.get(step, LifecycleStepState(step=step))
    if current.status is LifecycleStepStatus.SUCCEEDED and status is not current.status:
        raise KnowledgeConflictError(
            "completed lifecycle steps cannot regress",
            error_code="lifecycle_step_regression",
        )
    attempts = current.attempts + (1 if status is LifecycleStepStatus.RUNNING else 0)
    states[step] = LifecycleStepState(
        step=step,
        status=status,
        attempts=attempts,
        started_at=current.started_at or changed_at,
        completed_at=(
            changed_at
            if status in {LifecycleStepStatus.SUCCEEDED, LifecycleStepStatus.SKIPPED}
            else None
        ),
        last_error=error,
    )
    return operation.model_copy(
        update={
            "current_step": step,
            "steps": tuple(states[item] for item in LifecycleStep if item in states),
            "updated_at": changed_at,
        }
    )


def require_not_cancelled(operation: LifecycleOperation) -> None:
    if operation.status in {
        LifecycleOperationStatus.CANCEL_REQUESTED,
        LifecycleOperationStatus.CANCELLED,
    }:
        raise KnowledgeConflictError(
            "lifecycle operation is cancelled",
            error_code="lifecycle_cancelled",
        )


def update_progress(
    operation: LifecycleOperation,
    progress: float,
    *,
    changed_at: datetime,
) -> LifecycleOperation:
    if not 0 <= progress <= 1:
        raise ValueError("progress must be between zero and one")
    if progress < operation.progress:
        raise KnowledgeConflictError(
            "lifecycle progress cannot decrease",
            error_code="lifecycle_progress_regression",
        )
    return operation.model_copy(update={"progress": progress, "updated_at": changed_at})
