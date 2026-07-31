"""Create Phase 07 lifecycle authority, outbox, batch, and revision fields.

Revision ID: 20260731_0004
Revises: 20260731_0003
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260731_0004"
down_revision: str | None = "20260731_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add PostgreSQL-authoritative document lifecycle records."""
    op.add_column(
        "knowledge_documents",
        sa.Column("current_version_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "knowledge_documents",
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
    )
    op.add_column(
        "knowledge_documents",
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_table(
        "knowledge_lifecycle_operations",
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=128), nullable=False),
        sa.Column("document_id", sa.String(length=128), nullable=False),
        sa.Column("version_id", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("batch_id", sa.String(length=128), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
    )
    op.create_index(
        "uq_lifecycle_operations_tenant_idempotency",
        "knowledge_lifecycle_operations",
        ["tenant_id", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_lifecycle_operations_tenant_document",
        "knowledge_lifecycle_operations",
        ["tenant_id", "document_id", "updated_at"],
    )
    op.create_index(
        "ix_lifecycle_operations_status_updated",
        "knowledge_lifecycle_operations",
        ["status", "updated_at"],
    )
    op.create_table(
        "knowledge_lifecycle_outbox",
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("operation_id", sa.String(length=128), nullable=False),
        sa.Column("aggregate_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
    )
    op.create_index(
        "uq_lifecycle_outbox_tenant_idempotency",
        "knowledge_lifecycle_outbox",
        ["tenant_id", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_lifecycle_outbox_due",
        "knowledge_lifecycle_outbox",
        ["status", "available_at"],
    )
    op.create_index(
        "ix_lifecycle_outbox_operation",
        "knowledge_lifecycle_outbox",
        ["tenant_id", "operation_id"],
    )
    op.create_table(
        "knowledge_lifecycle_batches",
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
    )
    op.create_index(
        "uq_lifecycle_batches_tenant_idempotency",
        "knowledge_lifecycle_batches",
        ["tenant_id", "idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    """Remove only Phase 07 lifecycle structures."""
    op.drop_index(
        "uq_lifecycle_batches_tenant_idempotency",
        table_name="knowledge_lifecycle_batches",
    )
    op.drop_table("knowledge_lifecycle_batches")
    op.drop_index("ix_lifecycle_outbox_operation", table_name="knowledge_lifecycle_outbox")
    op.drop_index("ix_lifecycle_outbox_due", table_name="knowledge_lifecycle_outbox")
    op.drop_index(
        "uq_lifecycle_outbox_tenant_idempotency",
        table_name="knowledge_lifecycle_outbox",
    )
    op.drop_table("knowledge_lifecycle_outbox")
    op.drop_index(
        "ix_lifecycle_operations_status_updated",
        table_name="knowledge_lifecycle_operations",
    )
    op.drop_index(
        "ix_lifecycle_operations_tenant_document",
        table_name="knowledge_lifecycle_operations",
    )
    op.drop_index(
        "uq_lifecycle_operations_tenant_idempotency",
        table_name="knowledge_lifecycle_operations",
    )
    op.drop_table("knowledge_lifecycle_operations")
    op.drop_column("knowledge_documents", "revision")
    op.drop_column("knowledge_documents", "status")
    op.drop_column("knowledge_documents", "current_version_id")
