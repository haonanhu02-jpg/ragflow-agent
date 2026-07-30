"""Create the Phase 04 tenant-scoped knowledge persistence tables.

Revision ID: 20260730_0002
Revises: 20260730_0001
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260730_0002"
down_revision: str | None = "20260730_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create knowledge, document-version, job, and task fact tables."""
    op.create_table(
        "knowledge_bases",
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
    )
    op.create_table(
        "knowledge_documents",
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
    )
    op.create_index(
        "ix_knowledge_documents_tenant_kb",
        "knowledge_documents",
        ["tenant_id", "knowledge_base_id"],
    )
    op.create_table(
        "knowledge_document_versions",
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=128), nullable=False),
        sa.Column("document_id", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
    )
    op.create_index(
        "ix_document_versions_tenant_document",
        "knowledge_document_versions",
        ["tenant_id", "document_id"],
    )
    op.create_table(
        "knowledge_ingestion_jobs",
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=128), nullable=False),
        sa.Column("document_id", sa.String(length=128), nullable=False),
        sa.Column("document_version_id", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
    )
    op.create_index(
        "uq_ingestion_jobs_tenant_idempotency",
        "knowledge_ingestion_jobs",
        ["tenant_id", "idempotency_key"],
        unique=True,
    )
    op.create_table(
        "knowledge_ingestion_tasks",
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("job_id", sa.String(length=128), nullable=False),
        sa.Column("document_version_id", sa.String(length=128), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
    )
    op.create_index(
        "ix_ingestion_tasks_tenant_job",
        "knowledge_ingestion_tasks",
        ["tenant_id", "job_id"],
    )


def downgrade() -> None:
    """Drop Phase 04 knowledge tables in dependency-safe order."""
    op.drop_index("ix_ingestion_tasks_tenant_job", table_name="knowledge_ingestion_tasks")
    op.drop_table("knowledge_ingestion_tasks")
    op.drop_index(
        "uq_ingestion_jobs_tenant_idempotency",
        table_name="knowledge_ingestion_jobs",
    )
    op.drop_table("knowledge_ingestion_jobs")
    op.drop_index(
        "ix_document_versions_tenant_document",
        table_name="knowledge_document_versions",
    )
    op.drop_table("knowledge_document_versions")
    op.drop_index(
        "ix_knowledge_documents_tenant_kb",
        table_name="knowledge_documents",
    )
    op.drop_table("knowledge_documents")
    op.drop_table("knowledge_bases")
