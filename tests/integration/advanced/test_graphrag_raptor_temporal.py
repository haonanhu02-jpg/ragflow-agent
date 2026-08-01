from datetime import UTC, timedelta

import pytest

from ragflow_agent.knowledge.advanced.domain import (
    AdvancedBuild,
    AdvancedBuildStatus,
    AdvancedCapability,
    AdvancedResourceBudget,
)
from ragflow_agent.knowledge.advanced.graphrag.service import GraphRagService
from ragflow_agent.knowledge.advanced.infrastructure.memory import MemoryAdvancedBuildRepository
from ragflow_agent.knowledge.advanced.raptor.service import RaptorBuilder
from ragflow_agent.knowledge.advanced.temporal.service import (
    TemporalEvent,
    TemporalRagService,
    TimePoint,
)
from tests.fakes.advanced import NOW, make_chunk


@pytest.mark.asyncio
async def test_graphrag_is_idempotent_scoped_and_cancellable() -> None:
    repository = MemoryAdvancedBuildRepository()
    service = GraphRagService(repository, AdvancedResourceBudget())
    build = AdvancedBuild(
        id="build-1",
        idempotency_key="idem-1",
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        capability=AdvancedCapability.GRAPHRAG,
        build_version="graph-v1",
        document_version_ids=("ver-a",),
        updated_at=NOW,
    )
    chunks = (make_chunk("chunk-1", "Train Brake Controller Alarm"),)
    completed, snapshot = await service.build(build, chunks, now=NOW)
    assert completed.status is AdvancedBuildStatus.SUCCEEDED
    assert snapshot is not None and snapshot.entities
    repeated, repeated_snapshot = await service.build(build, chunks, now=NOW)
    assert repeated == completed and repeated_snapshot is None
    cancelled = await service.cancel(tenant_id="tenant-a", build_id="build-1", now=NOW)
    assert cancelled.status is AdvancedBuildStatus.CANCELLED


def test_raptor_converges_and_every_node_keeps_leaf_sources() -> None:
    chunks = tuple(
        make_chunk(f"chunk-{i}", f"section {i} brake alarm", sequence=i) for i in range(5)
    )
    tree = RaptorBuilder().build(chunks, build_version="raptor-v1", max_levels=4)
    assert all(
        len(right) < len(left) for left, right in zip(tree.levels, tree.levels[1:], strict=False)
    )
    assert all(node.source_chunk_ids for level in tree.levels for node in level)


def test_temporal_windows_sort_missing_values_and_isolate_scope() -> None:
    service = TemporalRagService()
    events = (
        TemporalEvent(
            id="event-2",
            tenant_id="tenant-a",
            knowledge_base_id="kb-a",
            series_id="train-1",
            occurred_at=NOW + timedelta(minutes=2),
            original_timezone="Asia/Shanghai",
            text="work order closed",
            source_chunk_ids=("chunk-2",),
        ),
        TemporalEvent(
            id="event-1",
            tenant_id="tenant-a",
            knowledge_base_id="kb-a",
            series_id="train-1",
            occurred_at=NOW,
            original_timezone="Asia/Shanghai",
            text="alarm opened",
            source_chunk_ids=("chunk-1",),
        ),
    )
    assert [item.id for item in service.timeline(events)] == ["event-1", "event-2"]
    points = (
        TimePoint(observed_at=NOW + timedelta(seconds=30), value=3),
        TimePoint(observed_at=NOW, value=1),
        TimePoint(observed_at=NOW + timedelta(seconds=10), value=None),
    )
    windows = service.windows(
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        series_id="train-1",
        original_timezone="Asia/Shanghai",
        points=points,
        window_seconds=60,
        source_chunk_ids=("chunk-1",),
    )
    assert windows[0].start_at.tzinfo is UTC
    assert windows[0].missing_count == 1
    assert windows[0].mean == 2
