"""Deterministic Phase 07 state, retry, progress, and cancellation rules."""

from datetime import UTC, datetime

import pytest

from ragflow_agent.knowledge.domain.document import (
    DocumentStatus,
    DocumentVersionStatus,
    activate_document_version,
    transition_document_version,
)
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.domain.lifecycle import (
    FailureClass,
    LifecycleError,
    LifecycleOperation,
    LifecycleOperationKind,
    LifecycleOperationStatus,
)
from ragflow_agent.knowledge.domain.retry import RetryPolicy, classify_failure, may_retry
from ragflow_agent.worker.cancellation import require_not_cancelled
from ragflow_agent.worker.dead_letter import move_to_dead_letter
from ragflow_agent.worker.progress import update_progress
from tests.fakes.knowledge import MemoryKnowledgeStore
from tests.fakes.lifecycle import NOW, seed_active_document


def _operation() -> LifecycleOperation:
    return LifecycleOperation(
        id="op-a",
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        document_id="doc-a",
        version_id="version-2",
        kind=LifecycleOperationKind.UPDATE,
        idempotency_key="update-a",
        actor_id="owner-a",
        reason="refresh",
        request_id="request-a",
        expected_document_revision=0,
        fencing_token=1,
        created_at=NOW,
        updated_at=NOW,
    )


def test_immutable_versions_and_delete_pending_block_activation() -> None:
    store = MemoryKnowledgeStore()
    document, version = seed_active_document(store)
    superseded = transition_document_version(
        version, DocumentVersionStatus.SUPERSEDED, changed_at=NOW
    )
    ready = transition_document_version(superseded, DocumentVersionStatus.READY, changed_at=NOW)
    tombstone = document.model_copy(
        update={
            "status": DocumentStatus.DELETE_PENDING,
            "current_version_id": None,
            "deleted_at": NOW,
        }
    )
    with pytest.raises(KnowledgeConflictError, match="cannot activate"):
        activate_document_version(tombstone, ready, changed_at=NOW)


def test_retry_policy_is_bounded_and_unknown_failure_is_permanent() -> None:
    policy = RetryPolicy(max_attempts=6, concurrency_attempts=3)
    transient = classify_failure(TimeoutError("temporary"))
    unknown = classify_failure(RuntimeError("bug"))
    assert transient.classification is FailureClass.TRANSIENT
    assert may_retry(transient, attempt=5, policy=policy)
    assert not may_retry(transient, attempt=6, policy=policy)
    assert unknown.classification is FailureClass.UNKNOWN
    assert not unknown.retryable


def test_progress_cancellation_and_dead_letter_are_auditable() -> None:
    operation = update_progress(_operation(), 0.5, changed_at=NOW)
    with pytest.raises(KnowledgeConflictError, match="cannot decrease"):
        update_progress(operation, 0.4, changed_at=NOW)
    cancelled = operation.model_copy(update={"status": LifecycleOperationStatus.CANCEL_REQUESTED})
    with pytest.raises(KnowledgeConflictError, match="cancelled"):
        require_not_cancelled(cancelled)
    error = LifecycleError(
        classification=FailureClass.TRANSIENT,
        code="timeout",
        message="exhausted",
        retryable=False,
    )
    dead = move_to_dead_letter(operation, error, changed_at=datetime.now(UTC))
    assert dead.status is LifecycleOperationStatus.DEAD_LETTER
    assert dead.error == error
