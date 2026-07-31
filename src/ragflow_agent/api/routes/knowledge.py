"""Phase 04 knowledge upload, job, and fixed-RAG HTTP routes."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, File, Header, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from ragflow_agent.api.security import require_trusted_identity
from ragflow_agent.knowledge.application.fixed_rag import FixedRagRequest
from ragflow_agent.knowledge.application.knowledge_service import CreateKnowledgeBaseCommand
from ragflow_agent.knowledge.application.lifecycle.update import (
    ReparseDocumentCommand,
    UpdateDocumentCommand,
)
from ragflow_agent.knowledge.application.upload import UploadDocumentCommand
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, Visibility
from ragflow_agent.knowledge.domain.ingestion import IngestionJob
from ragflow_agent.knowledge.domain.knowledge_base import KnowledgeBase
from ragflow_agent.knowledge.domain.lifecycle import (
    LifecycleBatch,
    LifecycleOperation,
    LifecycleOperationKind,
)
from ragflow_agent.knowledge.domain.retrieval import MetadataFilter, MetadataFilterGroup
from ragflow_agent.knowledge.runtime import MinimumRagRuntime
from ragflow_agent.observability import current_trace_context, new_correlation_id


class ApiModel(BaseModel):
    """Strict transport DTO base."""

    model_config = ConfigDict(extra="forbid")


class CreateKnowledgeBaseBody(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    visibility: Visibility = Visibility.PRIVATE


class UploadAccepted(ApiModel):
    job_id: str
    document_id: str
    document_version_id: str
    status: str
    duplicate: bool


class FixedRagBody(ApiModel):
    question: str = Field(min_length=1, max_length=8000)
    knowledge_base_ids: tuple[str, ...] = Field(min_length=1)
    top_k: int = Field(default=20, ge=1, le=1000)
    top_n: int = Field(default=5, ge=1, le=50)
    history: tuple[str, ...] = Field(default=(), max_length=16)
    target_languages: tuple[str, ...] = Field(default=(), max_length=4)
    filters: tuple[MetadataFilter, ...] = ()
    filter_expression: MetadataFilterGroup | None = None


class LifecycleReasonBody(ApiModel):
    reason: str = Field(min_length=1, max_length=1000)


class RollbackBody(LifecycleReasonBody):
    target_version_id: str = Field(min_length=1, max_length=128)


class BatchBody(ApiModel):
    knowledge_base_id: str = Field(min_length=1, max_length=128)
    kind: LifecycleOperationKind
    operation_ids: tuple[str, ...] = Field(min_length=1, max_length=1000)
    concurrency: int | None = Field(default=None, ge=1, le=100)


def _runtime(request: Request) -> MinimumRagRuntime:
    runtime = getattr(request.app.state, "minimum_rag_runtime", None)
    if runtime is None:
        raise RuntimeError("minimum RAG runtime is not configured")
    return cast(MinimumRagRuntime, runtime)


def _context(request: Request) -> AuthorizationContext:
    identity = require_trusted_identity(request)
    trace = current_trace_context()
    request_id = trace.trace_id if trace is not None else new_correlation_id()
    return AuthorizationContext(
        tenant_id=identity.tenant_id,
        actor_id=identity.subject_id,
        request_id=request_id,
        roles=identity.roles,
    )


def build_knowledge_router() -> APIRouter:
    """Build the Phase 04 business routes."""
    router = APIRouter(prefix="/v1", tags=["knowledge"])

    @router.post("/knowledge-bases", response_model=KnowledgeBase, status_code=201)
    async def create_knowledge_base(
        request: Request,
        body: CreateKnowledgeBaseBody,
    ) -> KnowledgeBase:
        runtime = _runtime(request)
        return await runtime.knowledge_service.create_knowledge_base(
            CreateKnowledgeBaseCommand(
                context=_context(request),
                name=body.name,
                description=body.description,
                visibility=body.visibility,
            )
        )

    @router.post(
        "/knowledge-bases/{knowledge_base_id}/documents",
        response_model=UploadAccepted,
        status_code=202,
    )
    async def upload_document(
        request: Request,
        knowledge_base_id: str,
        file: Annotated[UploadFile, File()],
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    ) -> UploadAccepted:
        runtime = _runtime(request)
        content = await file.read(request.app.state.settings.ingestion.max_upload_bytes + 1)
        submitted = await runtime.upload_service.submit(
            UploadDocumentCommand(
                context=_context(request),
                knowledge_base_id=knowledge_base_id,
                file_name=file.filename or "source",
                media_type=file.content_type or "application/octet-stream",
                content=content,
                idempotency_key=idempotency_key,
            )
        )
        return UploadAccepted(
            job_id=submitted.job.id,
            document_id=submitted.job.document_id,
            document_version_id=submitted.job.document_version_id,
            status=submitted.job.status.value,
            duplicate=submitted.duplicate,
        )

    @router.get("/ingestion-jobs/{job_id}", response_model=IngestionJob)
    async def get_ingestion_job(request: Request, job_id: str) -> IngestionJob:
        return await _runtime(request).upload_service.get_job(_context(request), job_id)

    @router.put(
        "/documents/{document_id}/content",
        response_model=LifecycleOperation,
        status_code=202,
    )
    async def update_document(
        request: Request,
        document_id: str,
        file: Annotated[UploadFile, File()],
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
        reason: Annotated[str, Header(alias="X-Lifecycle-Reason")],
    ) -> LifecycleOperation:
        content = await file.read(request.app.state.settings.ingestion.max_upload_bytes + 1)
        submitted = await _runtime(request).document_updates.update(
            UpdateDocumentCommand(
                context=_context(request),
                document_id=document_id,
                file_name=file.filename or "source",
                media_type=file.content_type or "application/octet-stream",
                content=content,
                idempotency_key=idempotency_key,
                reason=reason,
            )
        )
        await _runtime(request).lifecycle_outbox.dispatch_due(_context(request))
        return submitted.operation

    @router.post(
        "/documents/{document_id}/reparse",
        response_model=LifecycleOperation,
        status_code=202,
    )
    async def reparse_document(
        request: Request,
        document_id: str,
        body: LifecycleReasonBody,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    ) -> LifecycleOperation:
        submitted = await _runtime(request).document_updates.reparse(
            ReparseDocumentCommand(
                context=_context(request),
                document_id=document_id,
                idempotency_key=idempotency_key,
                reason=body.reason,
            )
        )
        await _runtime(request).lifecycle_outbox.dispatch_due(_context(request))
        return submitted.operation

    @router.delete(
        "/documents/{document_id}",
        response_model=LifecycleOperation,
        status_code=202,
    )
    async def delete_document(
        request: Request,
        document_id: str,
        body: LifecycleReasonBody,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    ) -> LifecycleOperation:
        return await _runtime(request).document_deletions.request_delete(
            _context(request),
            document_id=document_id,
            idempotency_key=idempotency_key,
            reason=body.reason,
        )

    @router.post(
        "/documents/{document_id}/restore",
        response_model=LifecycleOperation,
    )
    async def restore_document(
        request: Request,
        document_id: str,
        body: LifecycleReasonBody,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    ) -> LifecycleOperation:
        return await _runtime(request).document_deletions.restore(
            _context(request),
            document_id=document_id,
            idempotency_key=idempotency_key,
            reason=body.reason,
        )

    @router.post(
        "/documents/{document_id}/rollback",
        response_model=LifecycleOperation,
    )
    async def rollback_document(
        request: Request,
        document_id: str,
        body: RollbackBody,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    ) -> LifecycleOperation:
        return await _runtime(request).version_publisher.rollback(
            _context(request),
            document_id=document_id,
            target_version_id=body.target_version_id,
            idempotency_key=idempotency_key,
            reason=body.reason,
        )

    @router.get("/lifecycle-operations/{operation_id}", response_model=LifecycleOperation)
    async def get_lifecycle_operation(request: Request, operation_id: str) -> LifecycleOperation:
        return await _runtime(request).lifecycle_control.get(_context(request), operation_id)

    @router.post(
        "/lifecycle-operations/{operation_id}/cancel",
        response_model=LifecycleOperation,
    )
    async def cancel_lifecycle_operation(request: Request, operation_id: str) -> LifecycleOperation:
        return await _runtime(request).lifecycle_control.cancel(_context(request), operation_id)

    @router.post("/lifecycle-batches", response_model=LifecycleBatch, status_code=202)
    async def create_lifecycle_batch(
        request: Request,
        body: BatchBody,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    ) -> LifecycleBatch:
        return await _runtime(request).lifecycle_batches.create(
            _context(request),
            knowledge_base_id=body.knowledge_base_id,
            kind=body.kind,
            operation_ids=body.operation_ids,
            idempotency_key=idempotency_key,
            concurrency=body.concurrency,
        )

    @router.get("/lifecycle-batches/{batch_id}", response_model=LifecycleBatch)
    async def get_lifecycle_batch(request: Request, batch_id: str) -> LifecycleBatch:
        return await _runtime(request).lifecycle_batches.refresh(_context(request), batch_id)

    @router.post("/rag/query")
    async def fixed_rag(request: Request, body: FixedRagBody) -> dict[str, object]:
        answer = await _runtime(request).fixed_rag_service.answer(
            FixedRagRequest(
                context=_context(request),
                question=body.question,
                knowledge_base_ids=body.knowledge_base_ids,
                top_k=body.top_k,
                top_n=body.top_n,
                history=body.history,
                target_languages=body.target_languages,
                filters=body.filters,
                filter_expression=body.filter_expression,
            )
        )
        return answer.model_dump(mode="json")

    @router.get("/retrieval-traces/{trace_id}")
    async def get_retrieval_trace(request: Request, trace_id: str) -> dict[str, object]:
        trace = await _runtime(request).retrieval_trace_access.get_detailed(
            _context(request),
            trace_id,
        )
        if trace is None:
            return {"trace_id": trace_id, "found": False}
        return {"found": True, **trace.model_dump(mode="json")}

    return router
