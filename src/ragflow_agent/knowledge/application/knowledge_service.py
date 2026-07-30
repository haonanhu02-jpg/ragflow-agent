"""Knowledge command/query services shared by API, Worker, fixed RAG, and Agent Tool."""

from __future__ import annotations

from pydantic import Field, model_validator

from ragflow_agent.knowledge.domain.authorization import (
    AuthorizationContext,
    PermissionAction,
    Visibility,
)
from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.document import Document, DocumentVersion
from ragflow_agent.knowledge.domain.errors import (
    KnowledgeAuthorizationError,
    KnowledgeConflictError,
    KnowledgeNotFoundError,
)
from ragflow_agent.knowledge.domain.knowledge_base import KnowledgeBase
from ragflow_agent.knowledge.domain.retrieval import RetrievalQuery, RetrievalResult
from ragflow_agent.knowledge.ports.permission import PermissionChecker
from ragflow_agent.knowledge.ports.search import RetrieverPort
from ragflow_agent.knowledge.ports.trace import (
    KnowledgeTraceEvent,
    KnowledgeTraceKind,
    KnowledgeTracePort,
)
from ragflow_agent.knowledge.ports.uow import KnowledgeUnitOfWorkFactory
from ragflow_agent.shared.ports.identity import IdGenerator
from ragflow_agent.shared.ports.time import Clock


class CreateKnowledgeBaseCommand(KnowledgeModel):
    """Create one tenant-scoped knowledge base owned by the actor."""

    context: AuthorizationContext
    name: NonEmptyStr
    description: str = ""
    visibility: Visibility = Visibility.PRIVATE


class RegisterDocumentCommand(KnowledgeModel):
    """Register one logical document and immutable source version."""

    context: AuthorizationContext
    knowledge_base_id: NonEmptyStr
    name: NonEmptyStr
    object_key: NonEmptyStr
    media_type: NonEmptyStr
    content_hash: NonEmptyStr
    content_hash_algorithm: NonEmptyStr = "sha256"
    size_bytes: int = Field(ge=0)
    visibility: Visibility | None = None

    @model_validator(mode="after")
    def source_key_is_tenant_namespaced(self) -> RegisterDocumentCommand:
        expected = f"tenants/{self.context.tenant_id}/"
        if not self.object_key.startswith(expected):
            raise ValueError("document object_key must use the context tenant namespace")
        return self


class RegisteredDocument(KnowledgeModel):
    """Atomic output of document and first-version registration."""

    document: Document
    version: DocumentVersion


class KnowledgeService:
    """Permission-first command boundary over tenant-scoped repositories."""

    def __init__(
        self,
        *,
        unit_of_work_factory: KnowledgeUnitOfWorkFactory,
        permission_checker: PermissionChecker,
        id_generator: IdGenerator,
        clock: Clock,
        trace: KnowledgeTracePort,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._permission_checker = permission_checker
        self._id_generator = id_generator
        self._clock = clock
        self._trace = trace

    async def create_knowledge_base(
        self,
        command: CreateKnowledgeBaseCommand,
    ) -> KnowledgeBase:
        now = self._clock.now()
        knowledge_base = KnowledgeBase(
            id=self._id_generator.new_id(),
            tenant_id=command.context.tenant_id,
            owner_id=command.context.actor_id,
            name=command.name,
            description=command.description,
            visibility=command.visibility,
            created_at=now,
            updated_at=now,
        )
        async with self._unit_of_work_factory() as unit_of_work:
            await unit_of_work.knowledge_bases.add(
                tenant_id=command.context.tenant_id,
                entity=knowledge_base,
            )
            await unit_of_work.commit()
        await self._record(
            context=command.context,
            kind=KnowledgeTraceKind.KNOWLEDGE_BASE,
            action="created",
            resource_type="knowledge_base",
            resource_id=knowledge_base.id,
        )
        return knowledge_base

    async def get_knowledge_base(
        self,
        context: AuthorizationContext,
        knowledge_base_id: str,
    ) -> KnowledgeBase:
        async with self._unit_of_work_factory() as unit_of_work:
            knowledge_base = await unit_of_work.knowledge_bases.get(
                tenant_id=context.tenant_id,
                resource_id=knowledge_base_id,
            )
        if knowledge_base is None:
            raise KnowledgeNotFoundError(
                "knowledge_base",
                knowledge_base_id,
                trace_id=context.request_id,
            )
        self._permission_checker.require(
            context,
            knowledge_base.authorization,
            PermissionAction.READ,
        )
        return knowledge_base

    async def register_document(
        self,
        command: RegisterDocumentCommand,
    ) -> RegisteredDocument:
        now = self._clock.now()
        async with self._unit_of_work_factory() as unit_of_work:
            knowledge_base = await unit_of_work.knowledge_bases.get(
                tenant_id=command.context.tenant_id,
                resource_id=command.knowledge_base_id,
            )
            if knowledge_base is None:
                raise KnowledgeNotFoundError(
                    "knowledge_base",
                    command.knowledge_base_id,
                    trace_id=command.context.request_id,
                )
            self._permission_checker.require(
                command.context,
                knowledge_base.authorization,
                PermissionAction.WRITE,
            )
            document_id = self._id_generator.new_id()
            version_id = self._id_generator.new_id()
            visibility = command.visibility or knowledge_base.visibility
            document = Document(
                id=document_id,
                tenant_id=command.context.tenant_id,
                knowledge_base_id=knowledge_base.id,
                owner_id=command.context.actor_id,
                name=command.name,
                visibility=visibility,
                created_at=now,
                updated_at=now,
            )
            version = DocumentVersion(
                id=version_id,
                tenant_id=command.context.tenant_id,
                knowledge_base_id=knowledge_base.id,
                document_id=document.id,
                created_by=command.context.actor_id,
                object_key=command.object_key,
                media_type=command.media_type,
                content_hash=command.content_hash,
                content_hash_algorithm=command.content_hash_algorithm,
                size_bytes=command.size_bytes,
                created_at=now,
                updated_at=now,
            )
            await unit_of_work.documents.add(
                tenant_id=command.context.tenant_id,
                entity=document,
            )
            await unit_of_work.document_versions.add(
                tenant_id=command.context.tenant_id,
                entity=version,
            )
            await unit_of_work.commit()
        await self._record(
            context=command.context,
            kind=KnowledgeTraceKind.DOCUMENT,
            action="registered",
            resource_type="document",
            resource_id=document.id,
        )
        return RegisteredDocument(document=document, version=version)

    async def _record(
        self,
        *,
        context: AuthorizationContext,
        kind: KnowledgeTraceKind,
        action: str,
        resource_type: str,
        resource_id: str,
    ) -> None:
        await self._trace.record(
            KnowledgeTraceEvent(
                trace_id=context.request_id,
                request_id=context.request_id,
                tenant_id=context.tenant_id,
                actor_id=context.actor_id,
                kind=kind,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                occurred_at=self._clock.now(),
            )
        )


class KnowledgeQueryService:
    """Single permission-first retrieval entry for fixed RAG and Agent Tool."""

    def __init__(
        self,
        *,
        unit_of_work_factory: KnowledgeUnitOfWorkFactory,
        permission_checker: PermissionChecker,
        retriever: RetrieverPort,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._permission_checker = permission_checker
        self._retriever = retriever

    async def retrieve(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
    ) -> RetrievalResult:
        if query.tenant_id != context.tenant_id:
            raise KnowledgeAuthorizationError(
                reason_code="tenant_mismatch",
                trace_id=context.request_id,
            )
        async with self._unit_of_work_factory() as unit_of_work:
            for knowledge_base_id in query.knowledge_base_ids:
                knowledge_base = await unit_of_work.knowledge_bases.get(
                    tenant_id=context.tenant_id,
                    resource_id=knowledge_base_id,
                )
                if knowledge_base is None:
                    raise KnowledgeNotFoundError(
                        "knowledge_base",
                        knowledge_base_id,
                        trace_id=context.request_id,
                    )
                self._permission_checker.require(
                    context,
                    knowledge_base.authorization,
                    PermissionAction.READ,
                )
        result = await self._retriever.retrieve(context, query)
        if not result.trace.authorization_applied:
            raise KnowledgeConflictError(
                "retrieval trace must record authorization",
                error_code="retrieval_authorization_trace_missing",
                trace_id=context.request_id,
            )
        return result
