"""Ingestion Job/Task state, retry, and envelope tests."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.domain.ingestion import (
    IngestionEnvelope,
    IngestionError,
    IngestionJob,
    IngestionStage,
    IngestionStatus,
    IngestionTask,
    retry_ingestion_task,
    transition_ingestion,
)

NOW = datetime(2026, 7, 30, 8, 0, tzinfo=UTC)


def _job(**overrides: object) -> IngestionJob:
    values: dict[str, object] = {
        "id": "job-1",
        "tenant_id": "tenant-a",
        "knowledge_base_id": "kb-1",
        "document_id": "document-1",
        "document_version_id": "version-1",
        "requested_by": "owner-a",
        "idempotency_key": "tenant-a:version-1",
        "trace_id": "trace-1",
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return IngestionJob.model_validate(values)


def _task(**overrides: object) -> IngestionTask:
    values: dict[str, object] = {
        "id": "task-1",
        "tenant_id": "tenant-a",
        "job_id": "job-1",
        "document_version_id": "version-1",
        "stage": IngestionStage.PARSE,
        "idempotency_key": "job-1:parse",
        "trace_id": "trace-1",
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return IngestionTask.model_validate(values)


def test_job_progresses_monotonically_to_success() -> None:
    running = transition_ingestion(
        _job(),
        IngestionStatus.RUNNING,
        progress=0.1,
        changed_at=NOW + timedelta(seconds=1),
    )
    succeeded = transition_ingestion(
        running,
        IngestionStatus.SUCCEEDED,
        progress=1,
        changed_at=NOW + timedelta(seconds=2),
    )

    assert succeeded.status is IngestionStatus.SUCCEEDED
    assert succeeded.progress == 1


def test_progress_regression_and_terminal_transition_are_rejected() -> None:
    running = _task(status=IngestionStatus.RUNNING, progress=0.5)
    with pytest.raises(KnowledgeConflictError) as regression:
        transition_ingestion(
            running,
            IngestionStatus.SUCCEEDED,
            progress=0.4,
            changed_at=NOW + timedelta(seconds=1),
        )
    assert regression.value.error_code == "ingestion_progress_regression"

    succeeded = _task(status=IngestionStatus.SUCCEEDED, progress=1)
    with pytest.raises(KnowledgeConflictError) as terminal:
        transition_ingestion(
            succeeded,
            IngestionStatus.CANCELLED,
            progress=1,
            changed_at=NOW + timedelta(seconds=1),
        )
    assert terminal.value.error_code == "ingestion_transition_invalid"


def test_ingestion_timestamp_cannot_move_backwards() -> None:
    task = _task(updated_at=NOW + timedelta(seconds=1))

    with pytest.raises(KnowledgeConflictError) as captured:
        transition_ingestion(
            task,
            IngestionStatus.RUNNING,
            progress=0.1,
            changed_at=NOW,
        )
    assert captured.value.error_code == "ingestion_timestamp_regression"


def test_same_state_delivery_is_idempotent_only_when_payload_matches() -> None:
    task = _task()

    assert (
        transition_ingestion(
            task,
            IngestionStatus.PENDING,
            progress=0,
            changed_at=NOW + timedelta(seconds=1),
        )
        is task
    )
    with pytest.raises(KnowledgeConflictError):
        transition_ingestion(
            task,
            IngestionStatus.PENDING,
            progress=0.1,
            changed_at=NOW + timedelta(seconds=1),
        )


def test_retryable_failure_starts_new_attempt_without_progress_loss() -> None:
    error = IngestionError(code="parser_busy", message="busy", retryable=True)
    failed = _task(
        status=IngestionStatus.FAILED,
        progress=0.4,
        error=error,
    )

    retried = retry_ingestion_task(failed, changed_at=NOW + timedelta(seconds=1))

    assert retried.status is IngestionStatus.RUNNING
    assert retried.attempt == 2
    assert retried.progress == 0.4
    assert retried.error is None


def test_permanent_failure_cannot_retry() -> None:
    failed = _task(
        status=IngestionStatus.FAILED,
        error=IngestionError(code="unsupported", message="unsupported", retryable=False),
    )

    with pytest.raises(KnowledgeConflictError) as captured:
        retry_ingestion_task(failed, changed_at=NOW + timedelta(seconds=1))
    assert captured.value.error_code == "ingestion_retry_not_allowed"


def test_failed_and_success_states_enforce_error_and_progress() -> None:
    with pytest.raises(ValidationError):
        _task(status=IngestionStatus.FAILED)
    with pytest.raises(ValidationError):
        _task(status=IngestionStatus.SUCCEEDED, progress=0.9)


def test_queue_envelope_carries_tenant_job_version_attempt_and_trace() -> None:
    envelope = IngestionEnvelope.from_task(
        _task(attempt=3),
        message_id="message-1",
        created_at=NOW,
    )

    assert envelope.tenant_id == "tenant-a"
    assert envelope.job_id == "job-1"
    assert envelope.document_version_id == "version-1"
    assert envelope.attempt == 3
    assert envelope.trace_id == "trace-1"
