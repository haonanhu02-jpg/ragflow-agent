"""Reconciliation is bounded, tenant-scoped, and dry-run by default."""

from datetime import timedelta

import pytest
from tests.fakes.knowledge import (
    FixedClock,
    MemoryKnowledgeStore,
    MemoryKnowledgeUnitOfWorkFactory,
    MemoryObjectStorage,
    MemorySearchIndex,
)
from tests.fakes.lifecycle import NOW, context, seed_active_document

from ragflow_agent.knowledge.application.lifecycle.reconcile import LifecycleReconciler
from ragflow_agent.knowledge.domain.lifecycle import (
    LifecycleOperation,
    LifecycleOperationKind,
)


@pytest.mark.asyncio
async def test_reconciler_detects_cross_store_drift_without_mutating_in_dry_run() -> None:
    store = MemoryKnowledgeStore()
    document, version = seed_active_document(store)
    store.lifecycle_operations["operation-a"] = LifecycleOperation(
        id="operation-a",
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        document_id=document.id,
        version_id=version.id,
        kind=LifecycleOperationKind.REPARSE,
        idempotency_key="reparse-a",
        actor_id="owner-a",
        reason="parser upgrade",
        request_id="request-a",
        expected_document_revision=0,
        fencing_token=1,
        created_at=NOW,
        updated_at=NOW,
    )
    report = await LifecycleReconciler(
        unit_of_work_factory=MemoryKnowledgeUnitOfWorkFactory(store),
        search=MemorySearchIndex(),
        storage=MemoryObjectStorage(),
        clock=FixedClock(NOW + timedelta(hours=2)),
        limit=10,
    ).run(context(), stale_before=NOW + timedelta(hours=1))
    assert report.dry_run
    assert report.scanned == 2
    assert report.findings[0].kind == "cross_store_drift"
    assert not report.findings[0].repaired


@pytest.mark.asyncio
async def test_reconciler_never_scans_another_tenant() -> None:
    store = MemoryKnowledgeStore()
    document, version = seed_active_document(store, tenant_id="tenant-b")
    store.lifecycle_operations["operation-b"] = LifecycleOperation(
        id="operation-b",
        tenant_id="tenant-b",
        knowledge_base_id="kb-a",
        document_id=document.id,
        version_id=version.id,
        kind=LifecycleOperationKind.REPARSE,
        idempotency_key="reparse-b",
        actor_id="owner-a",
        reason="parser upgrade",
        request_id="request-b",
        expected_document_revision=0,
        fencing_token=1,
        created_at=NOW,
        updated_at=NOW,
    )
    report = await LifecycleReconciler(
        unit_of_work_factory=MemoryKnowledgeUnitOfWorkFactory(store),
        search=MemorySearchIndex(),
        storage=MemoryObjectStorage(),
        clock=FixedClock(NOW + timedelta(hours=2)),
    ).run(context("tenant-a"), stale_before=NOW + timedelta(hours=1))
    assert report.scanned == 0
    assert report.findings == ()
