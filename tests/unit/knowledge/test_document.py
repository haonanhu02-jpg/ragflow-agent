"""KnowledgeBase, Document, and DocumentVersion invariant tests."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ragflow_agent.knowledge.domain.authorization import Visibility
from ragflow_agent.knowledge.domain.document import (
    Document,
    DocumentVersion,
    DocumentVersionStatus,
    activate_document_version,
    transition_document_version,
)
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.domain.knowledge_base import KnowledgeBase

NOW = datetime(2026, 7, 30, 8, 0, tzinfo=UTC)


def _document(**overrides: object) -> Document:
    values: dict[str, object] = {
        "id": "document-1",
        "tenant_id": "tenant-a",
        "knowledge_base_id": "kb-1",
        "owner_id": "owner-a",
        "name": "manual.pdf",
        "visibility": Visibility.PRIVATE,
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return Document.model_validate(values)


def _version(**overrides: object) -> DocumentVersion:
    values: dict[str, object] = {
        "id": "version-1",
        "tenant_id": "tenant-a",
        "knowledge_base_id": "kb-1",
        "document_id": "document-1",
        "created_by": "owner-a",
        "object_key": "tenant-a/kb-1/document-1/version-1/source",
        "media_type": "application/pdf",
        "content_hash": "abc123",
        "size_bytes": 128,
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return DocumentVersion.model_validate(values)


def test_knowledge_base_and_document_expose_authorization_attributes() -> None:
    knowledge_base = KnowledgeBase(
        id="kb-1",
        tenant_id="tenant-a",
        owner_id="owner-a",
        name="Operations",
        visibility=Visibility.TENANT,
        created_at=NOW,
        updated_at=NOW,
    )
    document = _document(visibility=Visibility.TENANT)

    assert knowledge_base.authorization.tenant_id == "tenant-a"
    assert knowledge_base.authorization.visibility is Visibility.TENANT
    assert document.authorization.owner_id == "owner-a"


def test_domain_timestamps_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError):
        _document(created_at=datetime(2026, 7, 30), updated_at=NOW)


def test_document_version_uses_explicit_content_and_scope_identity() -> None:
    version = _version()

    assert version.tenant_id == "tenant-a"
    assert version.document_id == "document-1"
    assert version.content_hash_algorithm == "sha256"
    assert version.status is DocumentVersionStatus.REGISTERED


def test_document_version_allows_only_declared_state_edges() -> None:
    ingesting = transition_document_version(
        _version(),
        DocumentVersionStatus.INGESTING,
        changed_at=NOW + timedelta(seconds=1),
    )
    ready = transition_document_version(
        ingesting,
        DocumentVersionStatus.READY,
        changed_at=NOW + timedelta(seconds=2),
    )

    assert ready.status is DocumentVersionStatus.READY
    with pytest.raises(KnowledgeConflictError) as captured:
        transition_document_version(
            ready,
            DocumentVersionStatus.INGESTING,
            changed_at=NOW + timedelta(seconds=3),
        )
    assert captured.value.error_code == "document_version_transition_invalid"


def test_document_version_timestamp_cannot_move_backwards() -> None:
    version = _version(updated_at=NOW + timedelta(seconds=1))

    with pytest.raises(KnowledgeConflictError) as captured:
        transition_document_version(
            version,
            DocumentVersionStatus.INGESTING,
            changed_at=NOW,
        )
    assert captured.value.error_code == "document_version_timestamp_regression"


def test_repeated_version_transition_is_idempotent() -> None:
    version = _version()

    assert (
        transition_document_version(
            version,
            DocumentVersionStatus.REGISTERED,
            changed_at=NOW + timedelta(seconds=1),
        )
        is version
    )


def test_only_ready_same_scope_version_can_be_activated() -> None:
    document = _document()
    ready = _version(status=DocumentVersionStatus.READY)

    activated = activate_document_version(
        document,
        ready,
        changed_at=NOW + timedelta(seconds=1),
    )

    assert activated.current_version_id == "version-1"
    assert document.current_version_id is None

    with pytest.raises(KnowledgeConflictError):
        activate_document_version(
            document,
            _version(tenant_id="tenant-b", status=DocumentVersionStatus.READY),
            changed_at=NOW,
        )
    with pytest.raises(KnowledgeConflictError):
        activate_document_version(document, _version(), changed_at=NOW)
