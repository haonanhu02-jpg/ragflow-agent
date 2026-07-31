"""Cancellation remains cooperative and terminal progress remains explainable."""

from tests.fakes.lifecycle import NOW

from ragflow_agent.knowledge.domain.lifecycle import (
    LifecycleOperation,
    LifecycleOperationKind,
    LifecycleOperationStatus,
)
from ragflow_agent.worker.progress import update_progress


def test_cancelled_operation_cannot_report_false_completion() -> None:
    operation = LifecycleOperation(
        id="op-a",
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        document_id="doc-a",
        version_id="version-a",
        kind=LifecycleOperationKind.REPARSE,
        idempotency_key="key-a",
        actor_id="owner-a",
        reason="parser update",
        request_id="request-a",
        expected_document_revision=1,
        fencing_token=2,
        created_at=NOW,
        updated_at=NOW,
    )
    progressed = update_progress(operation, 0.75, changed_at=NOW)
    cancelled = progressed.model_copy(update={"status": LifecycleOperationStatus.CANCELLED})
    assert cancelled.progress == 0.75
    assert cancelled.status is LifecycleOperationStatus.CANCELLED
