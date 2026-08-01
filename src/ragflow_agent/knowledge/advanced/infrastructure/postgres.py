"""PostgreSQL authority adapters for advanced artifacts and build state."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ragflow_agent.knowledge.advanced.domain import AdvancedArtifact, AdvancedBuild
from ragflow_agent.knowledge.infrastructure.database.models import (
    AdvancedArtifactRow,
    AdvancedBuildRow,
)


class SqlAlchemyAdvancedArtifactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def put(self, artifact: AdvancedArtifact) -> None:
        row = await self._session.get(AdvancedArtifactRow, (artifact.tenant_id, artifact.id))
        values = artifact.model_dump(mode="json")
        if row is None:
            self._session.add(
                AdvancedArtifactRow(
                    tenant_id=artifact.tenant_id,
                    id=artifact.id,
                    knowledge_base_id=artifact.knowledge_base_id,
                    document_id=artifact.document_id,
                    document_version_id=artifact.document_version_id,
                    capability=artifact.capability.value,
                    build_version=artifact.build_version,
                    payload=values,
                )
            )
        else:
            row.payload = values

    async def list_for_version(
        self, *, tenant_id: str, document_version_id: str
    ) -> tuple[AdvancedArtifact, ...]:
        rows = (
            await self._session.scalars(
                select(AdvancedArtifactRow).where(
                    AdvancedArtifactRow.tenant_id == tenant_id,
                    AdvancedArtifactRow.document_version_id == document_version_id,
                )
            )
        ).all()
        return tuple(AdvancedArtifact.model_validate(row.payload) for row in rows)

    async def delete_version(self, *, tenant_id: str, document_version_id: str) -> int:
        result = await self._session.execute(
            delete(AdvancedArtifactRow).where(
                AdvancedArtifactRow.tenant_id == tenant_id,
                AdvancedArtifactRow.document_version_id == document_version_id,
            )
        )
        return int(result.rowcount or 0)  # type: ignore[attr-defined]


class SqlAlchemyAdvancedBuildRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, *, tenant_id: str, build_id: str) -> AdvancedBuild | None:
        row = await self._session.get(AdvancedBuildRow, (tenant_id, build_id))
        return None if row is None else AdvancedBuild.model_validate(row.payload)

    async def get_by_idempotency_key(
        self, *, tenant_id: str, idempotency_key: str
    ) -> AdvancedBuild | None:
        row = await self._session.scalar(
            select(AdvancedBuildRow).where(
                AdvancedBuildRow.tenant_id == tenant_id,
                AdvancedBuildRow.idempotency_key == idempotency_key,
            )
        )
        return None if row is None else AdvancedBuild.model_validate(row.payload)

    async def save(self, build: AdvancedBuild) -> None:
        row = await self._session.get(AdvancedBuildRow, (build.tenant_id, build.id))
        values = build.model_dump(mode="json")
        if row is None:
            self._session.add(
                AdvancedBuildRow(
                    tenant_id=build.tenant_id,
                    id=build.id,
                    knowledge_base_id=build.knowledge_base_id,
                    capability=build.capability.value,
                    status=build.status.value,
                    idempotency_key=build.idempotency_key,
                    updated_at=build.updated_at,
                    payload=values,
                )
            )
        else:
            row.status = build.status.value
            row.updated_at = build.updated_at
            row.payload = values
