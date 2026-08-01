"""Tenant-scoped SQLAlchemy rows storing strict domain snapshots."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ragflow_agent.infrastructure.database import Base


class KnowledgeBaseRow(Base):
    """Persistence row for one KnowledgeBase snapshot."""

    __tablename__ = "knowledge_bases"

    tenant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class DocumentRow(Base):
    """Persistence row for one logical Document snapshot."""

    __tablename__ = "knowledge_documents"

    tenant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    knowledge_base_id: Mapped[str] = mapped_column(String(128), nullable=False)
    current_version_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="active")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        Index(
            "ix_knowledge_documents_tenant_kb",
            "tenant_id",
            "knowledge_base_id",
        ),
    )


class DocumentVersionRow(Base):
    """Persistence row for one immutable source version."""

    __tablename__ = "knowledge_document_versions"

    tenant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    knowledge_base_id: Mapped[str] = mapped_column(String(128), nullable=False)
    document_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        Index(
            "ix_document_versions_tenant_document",
            "tenant_id",
            "document_id",
        ),
    )


class IngestionJobRow(Base):
    """Persistence row for an ingestion business job."""

    __tablename__ = "knowledge_ingestion_jobs"

    tenant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    knowledge_base_id: Mapped[str] = mapped_column(String(128), nullable=False)
    document_id: Mapped[str] = mapped_column(String(128), nullable=False)
    document_version_id: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        Index(
            "uq_ingestion_jobs_tenant_idempotency",
            "tenant_id",
            "idempotency_key",
            unique=True,
        ),
    )


class IngestionTaskRow(Base):
    """Persistence row for one retry-aware pipeline stage."""

    __tablename__ = "knowledge_ingestion_tasks"

    tenant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(128), nullable=False)
    document_version_id: Mapped[str] = mapped_column(String(128), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        Index(
            "ix_ingestion_tasks_tenant_job",
            "tenant_id",
            "job_id",
        ),
    )


class RetrievalTraceRow(Base):
    """Content-minimized Phase 06 trace with tenant and expiry indexes."""

    __tablename__ = "knowledge_retrieval_traces"

    tenant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        Index("ix_retrieval_traces_tenant_expires", "tenant_id", "expires_at"),
        Index("ix_retrieval_traces_expires", "expires_at"),
    )


class LifecycleOperationRow(Base):
    """Authoritative cross-store operation and persisted step state."""

    __tablename__ = "knowledge_lifecycle_operations"

    tenant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    knowledge_base_id: Mapped[str] = mapped_column(String(128), nullable=False)
    document_id: Mapped[str] = mapped_column(String(128), nullable=False)
    version_id: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)
    batch_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        Index(
            "uq_lifecycle_operations_tenant_idempotency",
            "tenant_id",
            "idempotency_key",
            unique=True,
        ),
        Index(
            "ix_lifecycle_operations_tenant_document",
            "tenant_id",
            "document_id",
            "updated_at",
        ),
        Index("ix_lifecycle_operations_status_updated", "status", "updated_at"),
    )


class LifecycleOutboxRow(Base):
    """Transactional outbox event awaiting idempotent queue publication."""

    __tablename__ = "knowledge_lifecycle_outbox"

    tenant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    operation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        Index(
            "uq_lifecycle_outbox_tenant_idempotency",
            "tenant_id",
            "idempotency_key",
            unique=True,
        ),
        Index("ix_lifecycle_outbox_due", "status", "available_at"),
        Index("ix_lifecycle_outbox_operation", "tenant_id", "operation_id"),
    )


class LifecycleBatchRow(Base):
    """Tenant-scoped batch whose status is recomputed from child operations."""

    __tablename__ = "knowledge_lifecycle_batches"

    tenant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    knowledge_base_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        Index(
            "uq_lifecycle_batches_tenant_idempotency",
            "tenant_id",
            "idempotency_key",
            unique=True,
        ),
    )


class AdvancedArtifactRow(Base):
    """Versioned advanced artifact with explicit tenant and source-version indexes."""

    __tablename__ = "knowledge_advanced_artifacts"

    tenant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    knowledge_base_id: Mapped[str] = mapped_column(String(128), nullable=False)
    document_id: Mapped[str] = mapped_column(String(128), nullable=False)
    document_version_id: Mapped[str] = mapped_column(String(128), nullable=False)
    capability: Mapped[str] = mapped_column(String(32), nullable=False)
    build_version: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        Index(
            "ix_advanced_artifacts_tenant_version",
            "tenant_id",
            "document_version_id",
            "capability",
        ),
    )


class AdvancedBuildRow(Base):
    """Idempotent, cancellable and resumable advanced build state."""

    __tablename__ = "knowledge_advanced_builds"

    tenant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    knowledge_base_id: Mapped[str] = mapped_column(String(128), nullable=False)
    capability: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        Index("uq_advanced_builds_tenant_idempotency", "tenant_id", "idempotency_key", unique=True),
        Index("ix_advanced_builds_status_updated", "status", "updated_at"),
    )
