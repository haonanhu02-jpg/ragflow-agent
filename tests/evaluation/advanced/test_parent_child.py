from ragflow_agent.knowledge.advanced.enrichment.parent_child import ParentContextExpander
from tests.fakes.advanced import make_chunk


def test_parent_neighbor_expansion_cannot_cross_tenant_version_or_budget() -> None:
    parent = make_chunk("parent", "parent context", sequence=0)
    hit = make_chunk("child-1", "hit", sequence=1, parent_chunk_id="parent")
    neighbor = make_chunk("child-2", "next", sequence=2, parent_chunk_id="parent")
    other_tenant = make_chunk("evil", "secret", tenant_id="tenant-b", sequence=1)
    stale = make_chunk("stale", "old", document_version_id="ver-old", sequence=1)
    result = ParentContextExpander().expand(
        hit, (parent, hit, neighbor, other_tenant, stale), max_tokens=10
    )
    assert [item.id for item in result] == ["parent", "child-1", "child-2"]
