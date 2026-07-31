"""Phase 04 knowledge upload, job, and fixed-RAG HTTP routes."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, File, Header, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from ragflow_agent.api.security import require_trusted_identity
from ragflow_agent.knowledge.application.fixed_rag import FixedRagRequest
from ragflow_agent.knowledge.application.knowledge_service import CreateKnowledgeBaseCommand
from ragflow_agent.knowledge.application.upload import UploadDocumentCommand
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, Visibility
from ragflow_agent.knowledge.domain.ingestion import IngestionJob
from ragflow_agent.knowledge.domain.knowledge_base import KnowledgeBase
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
