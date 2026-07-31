"""Stable knowledge-domain errors independent from transports and adapters."""

from __future__ import annotations

from collections.abc import Mapping

from ragflow_agent.shared.errors import AppError


class KnowledgeDomainError(AppError):
    """Base class for rejected knowledge-domain operations."""


class KnowledgeAuthorizationError(KnowledgeDomainError):
    """Authorization failed closed."""

    def __init__(
        self,
        message: str = "knowledge resource access is denied",
        *,
        reason_code: str = "knowledge_access_denied",
        trace_id: str | None = None,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=reason_code,
            status_code=403,
            trace_id=trace_id,
            details=details,
        )


class KnowledgeNotFoundError(KnowledgeDomainError):
    """A tenant-scoped resource was not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        *,
        trace_id: str | None = None,
    ) -> None:
        super().__init__(
            f"{resource_type} was not found",
            error_code="knowledge_resource_not_found",
            status_code=404,
            trace_id=trace_id,
            details={"resource_type": resource_type, "resource_id": resource_id},
        )


class KnowledgeConflictError(KnowledgeDomainError):
    """A domain invariant or optimistic state transition was violated."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "knowledge_conflict",
        trace_id: str | None = None,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            status_code=409,
            trace_id=trace_id,
            details=details,
        )


class KnowledgeRetrievalError(KnowledgeDomainError):
    """A retrieval dependency failed; this must never be reported as no evidence."""

    def __init__(
        self,
        message: str = "knowledge retrieval dependency failed",
        *,
        error_code: str = "retrieval_dependency_failed",
        trace_id: str | None = None,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            status_code=503,
            trace_id=trace_id,
            details=details,
        )
