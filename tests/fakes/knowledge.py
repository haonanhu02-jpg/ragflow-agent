"""Deterministic Phase 03 adapters used by unit and contract tests."""

from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator
from datetime import datetime
from hashlib import sha256
from types import TracebackType
from typing import Protocol, Self

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.chunk import ChunkRecord, ParsedDocument
from ragflow_agent.knowledge.domain.document import Document, DocumentStatus, DocumentVersion
from ragflow_agent.knowledge.domain.errors import (
    KnowledgeAuthorizationError,
    KnowledgeConflictError,
    KnowledgeNotFoundError,
)
from ragflow_agent.knowledge.domain.ingestion import (
    IngestionEnvelope,
    IngestionJob,
    IngestionTask,
)
from ragflow_agent.knowledge.domain.knowledge_base import KnowledgeBase
from ragflow_agent.knowledge.domain.lifecycle import (
    IndexGeneration,
    IndexGenerationValidation,
    LifecycleBatch,
    LifecycleOperation,
    LifecycleOperationStatus,
    LifecycleOutboxEvent,
    OutboxStatus,
)
from ragflow_agent.knowledge.domain.retrieval import (
    IndexRecord,
    IndexVersion,
    RetrievalCandidate,
    RetrievalQuery,
    RetrievalResult,
)
from ragflow_agent.knowledge.ports.chunking import ChunkingRequest
from ragflow_agent.knowledge.ports.embedding import (
    EmbeddingRequest,
    EmbeddingResult,
    EmbeddingVector,
)
from ragflow_agent.knowledge.ports.parsing import ParseRequest
from ragflow_agent.knowledge.ports.queue import QueueReceipt
from ragflow_agent.knowledge.ports.search import RerankRequest
from ragflow_agent.knowledge.ports.storage import StorageWriteRequest, StoredObject
from ragflow_agent.knowledge.ports.trace import KnowledgeTraceEvent


class TenantEntity(Protocol):
    """Structural identity required by the memory repositories."""

    id: str
    tenant_id: str


class MemoryTenantRepository[Entity: TenantEntity]:
    """Tenant-scoped repository over one staged dictionary."""

    def __init__(self, values: dict[str, Entity]) -> None:
        self._values = values

    async def get(self, *, tenant_id: str, resource_id: str) -> Entity | None:
        entity = self._values.get(resource_id)
        if entity is None or entity.tenant_id != tenant_id:
            return None
        return entity

    async def add(self, *, tenant_id: str, entity: Entity) -> None:
        if entity.tenant_id != tenant_id:
            raise KnowledgeAuthorizationError(reason_code="tenant_mismatch")
        if entity.id in self._values:
            raise KnowledgeConflictError(
                "resource identifier already exists",
                error_code="knowledge_resource_exists",
                details={"resource_id": entity.id},
            )
        self._values[entity.id] = entity

    async def save(self, *, tenant_id: str, entity: Entity) -> None:
        if entity.tenant_id != tenant_id:
            raise KnowledgeAuthorizationError(reason_code="tenant_mismatch")
        current = self._values.get(entity.id)
        if current is None or current.tenant_id != tenant_id:
            raise KnowledgeNotFoundError("knowledge_resource", entity.id)
        self._values[entity.id] = entity


class MemoryDocumentVersionRepository(MemoryTenantRepository[DocumentVersion]):
    """Memory DocumentVersion repository with scoped aggregate listing."""

    async def list_for_document(
        self,
        *,
        tenant_id: str,
        document_id: str,
    ) -> tuple[DocumentVersion, ...]:
        return tuple(
            version
            for version in self._values.values()
            if version.tenant_id == tenant_id and version.document_id == document_id
        )

    async def list_for_tenant(
        self, *, tenant_id: str, limit: int = 1000
    ) -> tuple[DocumentVersion, ...]:
        return tuple(
            version for version in self._values.values() if version.tenant_id == tenant_id
        )[:limit]


class MemoryDocumentRepository(MemoryTenantRepository[Document]):
    async def save_if_revision(
        self, *, tenant_id: str, entity: Document, expected_revision: int
    ) -> None:
        current = await self.get(tenant_id=tenant_id, resource_id=entity.id)
        if current is None or current.revision != expected_revision:
            raise KnowledgeConflictError(
                "document revision changed", error_code="document_revision_conflict"
            )
        await self.save(tenant_id=tenant_id, entity=entity)

    async def list_by_status(
        self,
        *,
        tenant_id: str,
        statuses: tuple[DocumentStatus, ...],
        limit: int = 100,
    ) -> tuple[Document, ...]:
        return tuple(
            item
            for item in self._values.values()
            if item.tenant_id == tenant_id and item.status in statuses
        )[:limit]


class MemoryLifecycleOperationRepository(MemoryTenantRepository[LifecycleOperation]):
    async def get_by_idempotency_key(
        self, *, tenant_id: str, idempotency_key: str
    ) -> LifecycleOperation | None:
        return next(
            (
                item
                for item in self._values.values()
                if item.tenant_id == tenant_id and item.idempotency_key == idempotency_key
            ),
            None,
        )

    async def list_for_document(
        self, *, tenant_id: str, document_id: str
    ) -> tuple[LifecycleOperation, ...]:
        return tuple(
            item
            for item in self._values.values()
            if item.tenant_id == tenant_id and item.document_id == document_id
        )

    async def list_by_status(
        self,
        *,
        tenant_id: str,
        statuses: tuple[LifecycleOperationStatus, ...],
        updated_before: datetime | None = None,
        limit: int = 100,
    ) -> tuple[LifecycleOperation, ...]:
        return tuple(
            item
            for item in self._values.values()
            if item.tenant_id == tenant_id
            and item.status in statuses
            and (updated_before is None or item.updated_at <= updated_before)
        )[:limit]


class MemoryLifecycleOutboxRepository(MemoryTenantRepository[LifecycleOutboxEvent]):
    async def list_due(
        self, *, tenant_id: str, now: datetime, limit: int
    ) -> tuple[LifecycleOutboxEvent, ...]:
        return tuple(
            item
            for item in self._values.values()
            if item.tenant_id == tenant_id
            and item.status is OutboxStatus.PENDING
            and item.available_at <= now
        )[:limit]


class MemoryLifecycleBatchRepository(MemoryTenantRepository[LifecycleBatch]):
    async def get_by_idempotency_key(
        self, *, tenant_id: str, idempotency_key: str
    ) -> LifecycleBatch | None:
        return next(
            (
                item
                for item in self._values.values()
                if item.tenant_id == tenant_id and item.idempotency_key == idempotency_key
            ),
            None,
        )


class MemoryIngestionTaskRepository(MemoryTenantRepository[IngestionTask]):
    """Memory IngestionTask repository with scoped job listing."""

    async def list_for_job(
        self,
        *,
        tenant_id: str,
        job_id: str,
    ) -> tuple[IngestionTask, ...]:
        return tuple(
            task
            for task in self._values.values()
            if task.tenant_id == tenant_id and task.job_id == job_id
        )


class MemoryKnowledgeStore:
    """Committed state shared by memory UnitOfWork instances."""

    def __init__(self) -> None:
        self.knowledge_bases: dict[str, KnowledgeBase] = {}
        self.documents: dict[str, Document] = {}
        self.document_versions: dict[str, DocumentVersion] = {}
        self.ingestion_jobs: dict[str, IngestionJob] = {}
        self.ingestion_tasks: dict[str, IngestionTask] = {}
        self.lifecycle_operations: dict[str, LifecycleOperation] = {}
        self.lifecycle_outbox: dict[str, LifecycleOutboxEvent] = {}
        self.lifecycle_batches: dict[str, LifecycleBatch] = {}


class MemoryKnowledgeUnitOfWork:
    """Copy-on-enter UnitOfWork proving commit and rollback semantics."""

    def __init__(self, store: MemoryKnowledgeStore) -> None:
        self._store = store
        self._entered = False
        self._committed = False
        self.knowledge_bases = MemoryTenantRepository[KnowledgeBase]({})
        self.documents = MemoryDocumentRepository({})
        self.document_versions = MemoryDocumentVersionRepository({})
        self.ingestion_jobs = MemoryTenantRepository[IngestionJob]({})
        self.ingestion_tasks = MemoryIngestionTaskRepository({})
        self.lifecycle_operations = MemoryLifecycleOperationRepository({})
        self.lifecycle_outbox = MemoryLifecycleOutboxRepository({})
        self.lifecycle_batches = MemoryLifecycleBatchRepository({})

    async def __aenter__(self) -> Self:
        self._entered = True
        self._committed = False
        self.knowledge_bases = MemoryTenantRepository(dict(self._store.knowledge_bases))
        self.documents = MemoryDocumentRepository(dict(self._store.documents))
        self.document_versions = MemoryDocumentVersionRepository(
            dict(self._store.document_versions)
        )
        self.ingestion_jobs = MemoryTenantRepository(dict(self._store.ingestion_jobs))
        self.ingestion_tasks = MemoryIngestionTaskRepository(dict(self._store.ingestion_tasks))
        self.lifecycle_operations = MemoryLifecycleOperationRepository(
            dict(self._store.lifecycle_operations)
        )
        self.lifecycle_outbox = MemoryLifecycleOutboxRepository(dict(self._store.lifecycle_outbox))
        self.lifecycle_batches = MemoryLifecycleBatchRepository(dict(self._store.lifecycle_batches))
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_value, traceback
        if exc_type is not None or not self._committed:
            await self.rollback()
        self._entered = False

    async def commit(self) -> None:
        self._ensure_entered()
        self._store.knowledge_bases = dict(self.knowledge_bases._values)
        self._store.documents = dict(self.documents._values)
        self._store.document_versions = dict(self.document_versions._values)
        self._store.ingestion_jobs = dict(self.ingestion_jobs._values)
        self._store.ingestion_tasks = dict(self.ingestion_tasks._values)
        self._store.lifecycle_operations = dict(self.lifecycle_operations._values)
        self._store.lifecycle_outbox = dict(self.lifecycle_outbox._values)
        self._store.lifecycle_batches = dict(self.lifecycle_batches._values)
        self._committed = True

    async def rollback(self) -> None:
        self._ensure_entered()
        self._committed = False

    def _ensure_entered(self) -> None:
        if not self._entered:
            raise RuntimeError("knowledge unit of work has not been entered")


class MemoryKnowledgeUnitOfWorkFactory:
    """Factory exposing committed memory state to reusable contract suites."""

    def __init__(self, store: MemoryKnowledgeStore | None = None) -> None:
        self.store = store or MemoryKnowledgeStore()

    def __call__(self) -> MemoryKnowledgeUnitOfWork:
        return MemoryKnowledgeUnitOfWork(self.store)


def _require_same_tenant(context: AuthorizationContext, tenant_id: str) -> None:
    if context.tenant_id != tenant_id:
        raise KnowledgeAuthorizationError(reason_code="tenant_mismatch")


class _DeniedObjectRead:
    """Async iterator that fails closed before yielding object bytes."""

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> bytes:
        raise KnowledgeAuthorizationError(reason_code="tenant_mismatch")


class MemoryObjectStorage:
    """Integrity-checking, tenant-scoped streaming object store."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], tuple[StoredObject, bytes]] = {}

    async def put(
        self,
        context: AuthorizationContext,
        request: StorageWriteRequest,
        content: AsyncIterable[bytes],
    ) -> StoredObject:
        _require_same_tenant(context, request.tenant_id)
        payload = b"".join([chunk async for chunk in content])
        digest = sha256(payload).hexdigest()
        if len(payload) != request.size_bytes or digest != request.checksum_sha256:
            raise KnowledgeConflictError(
                "object integrity metadata does not match content",
                error_code="object_integrity_mismatch",
            )
        stored = StoredObject(
            tenant_id=request.tenant_id,
            object_key=request.object_key,
            media_type=request.media_type,
            size_bytes=request.size_bytes,
            checksum_sha256=digest,
            etag=digest,
        )
        self.objects[(stored.tenant_id, stored.object_key)] = (stored, payload)
        return stored

    async def _read_chunks(self, stored_object: StoredObject) -> AsyncIterator[bytes]:
        record = self.objects.get((stored_object.tenant_id, stored_object.object_key))
        if record is None:
            raise KnowledgeNotFoundError("stored_object", stored_object.object_key)
        yield record[1]

    def read(
        self,
        context: AuthorizationContext,
        stored_object: StoredObject,
    ) -> AsyncIterator[bytes]:
        if context.tenant_id != stored_object.tenant_id:
            return _DeniedObjectRead()
        return self._read_chunks(stored_object)

    async def delete(
        self,
        context: AuthorizationContext,
        stored_object: StoredObject,
    ) -> None:
        _require_same_tenant(context, stored_object.tenant_id)
        self.objects.pop((stored_object.tenant_id, stored_object.object_key), None)

    async def exists(self, context: AuthorizationContext, stored_object: StoredObject) -> bool:
        _require_same_tenant(context, stored_object.tenant_id)
        return (stored_object.tenant_id, stored_object.object_key) in self.objects

    async def list_prefix(
        self, context: AuthorizationContext, *, tenant_id: str, prefix: str
    ) -> tuple[str, ...]:
        _require_same_tenant(context, tenant_id)
        return tuple(
            key
            for (scope, key), (_stored, _content) in self.objects.items()
            if scope == tenant_id and key.startswith(prefix)
        )


class FixtureParser:
    """Return one prevalidated parser fixture after scope validation."""

    def __init__(self, output: ParsedDocument) -> None:
        self.output = output

    async def parse(self, request: ParseRequest) -> ParsedDocument:
        expected = (
            self.output.tenant_id,
            self.output.knowledge_base_id,
            self.output.document_id,
            self.output.document_version_id,
        )
        actual = (
            request.tenant_id,
            request.knowledge_base_id,
            request.document_id,
            request.document_version_id,
        )
        if actual != expected:
            raise KnowledgeConflictError(
                "parser fixture scope mismatch",
                error_code="parser_scope_mismatch",
            )
        return self.output


class FixtureChunker:
    """Return stable chunks for one configured ParsedDocument."""

    def __init__(self, output: tuple[ChunkRecord, ...]) -> None:
        self.output = output

    async def chunk(
        self,
        context: AuthorizationContext,
        request: ChunkingRequest,
    ) -> tuple[ChunkRecord, ...]:
        _require_same_tenant(context, request.parsed_document.tenant_id)
        if any(chunk.tenant_id != context.tenant_id for chunk in self.output):
            raise KnowledgeAuthorizationError(reason_code="tenant_mismatch")
        return self.output


class DeterministicEmbedding:
    """Generate fixed-size vectors without a model provider."""

    def __init__(self, dimensions: int = 3) -> None:
        self.dimensions = dimensions

    async def embed(
        self,
        context: AuthorizationContext,
        request: EmbeddingRequest,
    ) -> EmbeddingResult:
        _require_same_tenant(context, request.tenant_id)
        return EmbeddingResult(
            model_id=request.model_id,
            dimensions=self.dimensions,
            normalized=False,
            vectors=tuple(
                EmbeddingVector(
                    input_id=item.id,
                    values=tuple(float(len(item.text) + index) for index in range(self.dimensions)),
                )
                for item in request.inputs
            ),
        )


class MemorySearchIndex:
    """Tenant-scoped write contract without search behavior or vendor DSL."""

    def __init__(self) -> None:
        self.records: dict[tuple[str, str, str], IndexRecord] = {}
        self.active_versions: dict[tuple[str, str], str] = {}
        self.active_document_versions: dict[tuple[str, str, str], str] = {}
        self.generations: dict[str, tuple[IndexGeneration, tuple[IndexRecord, ...]]] = {}
        self.aliases: dict[str, str] = {}

    async def upsert(
        self,
        context: AuthorizationContext,
        version: IndexVersion,
        records: tuple[IndexRecord, ...],
    ) -> None:
        _require_same_tenant(context, version.tenant_id)
        for record in records:
            scope = (record.tenant_id, record.knowledge_base_id, record.index_version_id)
            expected = (version.tenant_id, version.knowledge_base_id, version.id)
            if scope != expected or len(record.embedding) != version.embedding.dimensions:
                raise KnowledgeConflictError(
                    "index record is incompatible with index version",
                    error_code="index_record_incompatible",
                )
            self.records[(record.tenant_id, record.index_version_id, record.chunk_id)] = record

    async def delete(
        self,
        context: AuthorizationContext,
        *,
        index_version_id: str,
        chunk_ids: tuple[str, ...],
    ) -> None:
        keys = [
            key
            for key in self.records
            if key[0] == context.tenant_id and key[1] == index_version_id and key[2] in chunk_ids
        ]
        for key in keys:
            del self.records[key]

    async def activate(
        self,
        context: AuthorizationContext,
        version: IndexVersion,
    ) -> None:
        _require_same_tenant(context, version.tenant_id)
        self.active_versions[(version.tenant_id, version.knowledge_base_id)] = version.id

    async def validate_document_version(
        self,
        context: AuthorizationContext,
        *,
        knowledge_base_id: str,
        document_id: str,
        document_version_id: str,
    ) -> int:
        return sum(
            record.tenant_id == context.tenant_id
            and record.knowledge_base_id == knowledge_base_id
            and record.document_id == document_id
            and record.document_version_id == document_version_id
            for record in self.records.values()
        )

    async def promote_document_version(
        self,
        context: AuthorizationContext,
        *,
        knowledge_base_id: str,
        document_id: str,
        document_version_id: str,
        fencing_token: int,
    ) -> None:
        del fencing_token
        if (
            await self.validate_document_version(
                context,
                knowledge_base_id=knowledge_base_id,
                document_id=document_id,
                document_version_id=document_version_id,
            )
            < 1
        ):
            raise KnowledgeConflictError(
                "index version contains no records", error_code="index_activation_empty"
            )
        self.active_document_versions[(context.tenant_id, knowledge_base_id, document_id)] = (
            document_version_id
        )

    async def retire_document_version(
        self,
        context: AuthorizationContext,
        *,
        knowledge_base_id: str,
        document_id: str,
        document_version_id: str,
    ) -> None:
        key = (context.tenant_id, knowledge_base_id, document_id)
        if self.active_document_versions.get(key) == document_version_id:
            self.active_document_versions.pop(key)

    async def delete_document_version(
        self,
        context: AuthorizationContext,
        *,
        knowledge_base_id: str,
        document_id: str,
        document_version_id: str,
    ) -> None:
        keys = [
            key
            for key, record in self.records.items()
            if record.tenant_id == context.tenant_id
            and record.knowledge_base_id == knowledge_base_id
            and record.document_id == document_id
            and record.document_version_id == document_version_id
        ]
        for key in keys:
            del self.records[key]
        await self.retire_document_version(
            context,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            document_version_id=document_version_id,
        )

    async def list_projection_versions(
        self,
        context: AuthorizationContext,
        *,
        limit: int = 1000,
    ) -> tuple[tuple[str, str, str], ...]:
        return tuple(
            dict.fromkeys(
                (
                    record.knowledge_base_id,
                    record.document_id,
                    record.document_version_id,
                )
                for record in self.records.values()
                if record.tenant_id == context.tenant_id
            )
        )[:limit]

    async def create_staging_generation(
        self, context: AuthorizationContext, generation: IndexGeneration
    ) -> None:
        _require_same_tenant(context, generation.tenant_id)
        self.generations.setdefault(generation.physical_index, (generation, ()))

    async def write_generation(
        self,
        context: AuthorizationContext,
        generation: IndexGeneration,
        records: tuple[IndexRecord, ...],
    ) -> None:
        _require_same_tenant(context, generation.tenant_id)
        self.generations[generation.physical_index] = (generation, records)

    async def validate_generation(
        self, context: AuthorizationContext, generation: IndexGeneration
    ) -> IndexGenerationValidation:
        _require_same_tenant(context, generation.tenant_id)
        records = self.generations.get(generation.physical_index, (generation, ()))[1]
        scoped = all(
            item.tenant_id == generation.tenant_id
            and item.knowledge_base_id == generation.knowledge_base_id
            for item in records
        )
        return IndexGenerationValidation(
            physical_index=generation.physical_index,
            mapping_valid=True,
            chunk_count=len(records),
            tenant_scope_valid=scoped,
            knowledge_base_scope_valid=scoped,
            lifecycle_fields_valid=True,
            sample_query_valid=True,
            checksum=f"records:{len(records)}",
        )

    async def switch_alias(
        self,
        context: AuthorizationContext,
        generation: IndexGeneration,
        *,
        expected_current: str | None,
    ) -> str | None:
        _require_same_tenant(context, generation.tenant_id)
        current = self.aliases.get(generation.read_alias)
        if current != expected_current:
            raise KnowledgeConflictError("alias changed", error_code="index_alias_conflict")
        self.aliases[generation.read_alias] = generation.physical_index
        return current

    async def resolve_alias(self, context: AuthorizationContext, *, alias: str) -> str | None:
        del context
        return self.aliases.get(alias)

    async def delete_generation(
        self, context: AuthorizationContext, generation: IndexGeneration
    ) -> None:
        _require_same_tenant(context, generation.tenant_id)
        if self.aliases.get(generation.read_alias) == generation.physical_index:
            raise KnowledgeConflictError(
                "active generation cannot be deleted",
                error_code="index_generation_active",
            )
        self.generations.pop(generation.physical_index, None)


class FixtureRetriever:
    """Return one prevalidated RetrievalResult after context/query validation."""

    def __init__(self, result: RetrievalResult) -> None:
        self.result = result
        self.calls = 0

    async def retrieve(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
    ) -> RetrievalResult:
        _require_same_tenant(context, query.tenant_id)
        if query != self.result.query:
            raise KnowledgeConflictError(
                "retriever fixture query mismatch",
                error_code="retriever_query_mismatch",
            )
        self.calls += 1
        return self.result


class IdentityReranker:
    """Preserve candidates while proving the provider-neutral interface."""

    async def rerank(
        self,
        context: AuthorizationContext,
        request: RerankRequest,
    ) -> tuple[RetrievalCandidate, ...]:
        _require_same_tenant(context, request.query.tenant_id)
        return request.candidates


class MemoryIngestionQueue:
    """Collect tenant-scoped ingestion envelopes."""

    def __init__(self) -> None:
        self.envelopes: list[IngestionEnvelope] = []

    async def publish(
        self,
        context: AuthorizationContext,
        envelope: IngestionEnvelope,
    ) -> QueueReceipt:
        _require_same_tenant(context, envelope.tenant_id)
        self.envelopes.append(envelope)
        return QueueReceipt(
            message_id=envelope.message_id,
            transport_reference=f"memory:{envelope.message_id}",
        )


class MemoryKnowledgeTrace:
    """Collect versioned trace events for contract assertions."""

    def __init__(self) -> None:
        self.events: list[KnowledgeTraceEvent] = []

    async def record(self, event: KnowledgeTraceEvent) -> None:
        self.events.append(event)


class SequenceIdGenerator:
    """Return deterministic identifiers and fail when a test over-consumes them."""

    def __init__(self, identifiers: list[str]) -> None:
        self._identifiers = iter(identifiers)

    def new_id(self) -> str:
        return next(self._identifiers)


class FixedClock:
    """Return one timezone-aware instant."""

    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now
