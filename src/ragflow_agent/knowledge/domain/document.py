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
    DELETE_PENDING = "delete_pending"
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
    DocumentVersionStatus.SUPERSEDED: frozenset(
        {DocumentVersionStatus.READY, DocumentVersionStatus.DELETED}
    ),
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
    revision: int = Field(default=0, ge=0)
    deleted_at: datetime | None = None
    purge_after: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", "deleted_at", "purge_after")
    @classmethod
    def timestamps_are_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("document timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_document(self) -> Document:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot precede created_at")
        if self.status is not DocumentStatus.ACTIVE and self.current_version_id is not None:
            raise ValueError("non-active documents cannot expose a current version")
        if self.status is DocumentStatus.ACTIVE and self.deleted_at is not None:
            raise ValueError("active documents cannot carry deleted_at")
        if self.status is not DocumentStatus.ACTIVE and self.deleted_at is None:
            raise ValueError("deleted or delete-pending documents require deleted_at")
        if self.purge_after is not None and self.deleted_at is None:
            raise ValueError("purge_after requires deleted_at")
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
    revision: int = Field(default=0, ge=0)
    index_version_id: str | None = None
    activated_at: datetime | None = None
    retired_at: datetime | None = None
    purge_after: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator(
        "created_at",
        "updated_at",
        "activated_at",
        "retired_at",
        "purge_after",
    )
    @classmethod
    def timestamps_are_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
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
            "revision": version.revision + 1,
            "updated_at": changed_at,
        }
    )


def activate_document_version(
    document: Document,
    version: DocumentVersion,
    *,
    changed_at: datetime,
    expected_revision: int | None = None,
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
    if document.status is not DocumentStatus.ACTIVE:
        raise KnowledgeConflictError(
            "deleted documents cannot activate versions",
            error_code="document_deleted",
        )
    if expected_revision is not None and document.revision != expected_revision:
        raise KnowledgeConflictError(
            "document revision changed before activation",
            error_code="document_revision_conflict",
            details={"expected": expected_revision, "actual": document.revision},
        )
    return Document.model_validate(
        {
            **document.model_dump(),
            "current_version_id": version.id,
            "revision": document.revision + 1,
            "updated_at": changed_at,
        }
    )
