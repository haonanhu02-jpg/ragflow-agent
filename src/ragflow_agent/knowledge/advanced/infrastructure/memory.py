"""Deterministic advanced repositories for unit tests and local evaluation."""

from ragflow_agent.knowledge.advanced.domain import AdvancedArtifact, AdvancedBuild


class MemoryAdvancedArtifactRepository:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], AdvancedArtifact] = {}

    async def put(self, artifact: AdvancedArtifact) -> None:
        self._items[(artifact.tenant_id, artifact.id)] = artifact

    async def list_for_version(
        self, *, tenant_id: str, document_version_id: str
    ) -> tuple[AdvancedArtifact, ...]:
        return tuple(
            item
            for (item_tenant, _), item in self._items.items()
            if item_tenant == tenant_id and item.document_version_id == document_version_id
        )

    async def delete_version(self, *, tenant_id: str, document_version_id: str) -> int:
        keys = [
            key
            for key, item in self._items.items()
            if key[0] == tenant_id and item.document_version_id == document_version_id
        ]
        for key in keys:
            del self._items[key]
        return len(keys)


class MemoryAdvancedBuildRepository:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], AdvancedBuild] = {}

    async def get(self, *, tenant_id: str, build_id: str) -> AdvancedBuild | None:
        return self._items.get((tenant_id, build_id))

    async def get_by_idempotency_key(
        self, *, tenant_id: str, idempotency_key: str
    ) -> AdvancedBuild | None:
        return next(
            (
                item
                for (item_tenant, _), item in self._items.items()
                if item_tenant == tenant_id and item.idempotency_key == idempotency_key
            ),
            None,
        )

    async def save(self, build: AdvancedBuild) -> None:
        self._items[(build.tenant_id, build.id)] = build
