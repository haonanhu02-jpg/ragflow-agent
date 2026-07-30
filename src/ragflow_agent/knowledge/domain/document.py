"""Logical Document and immutable DocumentVersion aggregates."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from ragflow_agent.knowledge.domain.authorization import ResourceAuthorization, Visibility
from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError


class DocumentStatus(StrEnum):
    """Logical document lifecycle visible to application services."""

    ACTIVE = "active"
    DELETED = "deleted"


class DocumentVersionStatus(StrEnum):
    """Content-version processing state."""

    REGISTERED = "registered"
    INGESTING = "ingesting"
    READY = "ready"
    FAILED = "failed"
    SUPERSEDED = "superseded"
    DELETED = "deleted"


_VERSION_TRANSITIONS: dict[DocumentVersionStatus, frozenset[DocumentVersionStatus]] = {
    DocumentVersionStatus.REGISTERED: frozenset(
        {DocumentVersionStatus.INGESTING, DocumentVersionStatus.DELETED}
    ),
    DocumentVersionStatus.INGESTING: frozenset(
        {
            DocumentVersionStatus.READY,
            DocumentVersionStatus.FAILED,
            DocumentVersionStatus.DELETED,
        }
    ),
    DocumentVersionStatus.READY: frozenset(
        {DocumentVersionStatus.SUPERSEDED, DocumentVersionStatus.DELETED}
    ),
    DocumentVersionStatus.FAILED: frozenset(
        {DocumentVersionStatus.INGESTING, DocumentVersionStatus.DELETED}
    ),
    DocumentVersionStatus.SUPERSEDED: frozenset({DocumentVersionStatus.DELETED}),
    DocumentVersionStatus.DELETED: frozenset(),
}


class Document(KnowledgeModel):
    """Logical document whose current content is an explicit version reference."""

    id: NonEmptyStr
    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    owner_id: NonEmptyStr
    name: NonEmptyStr
    visibility: Visibility = Visibility.PRIVATE
    status: DocumentStatus = DocumentStatus.ACTIVE
    current_version_id: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def timestamps_are_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("document timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_document(self) -> Document:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot precede created_at")
        if self.status is DocumentStatus.DELETED and self.current_version_id is not None:
            raise ValueError("deleted documents cannot expose a current version")
        return self

    @property
    def authorization(self) -> ResourceAuthorization:
        return ResourceAuthorization(
            tenant_id=self.tenant_id,
            owner_id=self.owner_id,
            visibility=self.visibility,
        )


class DocumentVersion(KnowledgeModel):
    """Immutable content identity with an explicit processing state."""

    id: NonEmptyStr
    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    document_id: NonEmptyStr
    created_by: NonEmptyStr
    object_key: NonEmptyStr
    media_type: NonEmptyStr
    content_hash: NonEmptyStr
    content_hash_algorithm: NonEmptyStr = "sha256"
    size_bytes: int = Field(ge=0)
    status: DocumentVersionStatus = DocumentVersionStatus.REGISTERED
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def timestamps_are_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("document-version timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_version(self) -> DocumentVersion:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot precede created_at")
        return self


def transition_document_version(
    version: DocumentVersion,
    target: DocumentVersionStatus,
    *,
    changed_at: datetime,
) -> DocumentVersion:
    """Return a new version state after validating the lifecycle edge."""
    if changed_at < version.updated_at:
        raise KnowledgeConflictError(
            "document version timestamp cannot move backwards",
            error_code="document_version_timestamp_regression",
        )
    if target is version.status:
        return version
    if target not in _VERSION_TRANSITIONS[version.status]:
        raise KnowledgeConflictError(
            "document version transition is not allowed",
            error_code="document_version_transition_invalid",
            details={"current": version.status.value, "target": target.value},
        )
    return DocumentVersion.model_validate(
        {
            **version.model_dump(),
            "status": target,
            "updated_at": changed_at,
        }
    )


def activate_document_version(
    document: Document,
    version: DocumentVersion,
    *,
    changed_at: datetime,
) -> Document:
    """Set a ready, same-document version as the logical document's current version."""
    if changed_at < document.updated_at:
        raise KnowledgeConflictError(
            "document timestamp cannot move backwards",
            error_code="document_timestamp_regression",
        )
    expected = (
        document.tenant_id,
        document.knowledge_base_id,
        document.id,
    )
    actual = (
        version.tenant_id,
        version.knowledge_base_id,
        version.document_id,
    )
    if expected != actual:
        raise KnowledgeConflictError(
            "document version belongs to a different aggregate",
            error_code="document_version_scope_mismatch",
        )
    if version.status is not DocumentVersionStatus.READY:
        raise KnowledgeConflictError(
            "only a ready document version can be activated",
            error_code="document_version_not_ready",
        )
    if document.status is DocumentStatus.DELETED:
        raise KnowledgeConflictError(
            "deleted documents cannot activate versions",
            error_code="document_deleted",
        )
    return Document.model_validate(
        {
            **document.model_dump(),
            "current_version_id": version.id,
            "updated_at": changed_at,
        }
    )
