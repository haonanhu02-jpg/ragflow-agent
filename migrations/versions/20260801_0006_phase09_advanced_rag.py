"""Create Phase 09 versioned advanced artifact and build tables.

Revision ID: 20260801_0006
Revises: 20260731_0005
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260801_0006"
down_revision: str | None = "20260731_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_advanced_artifacts",
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=128), nullable=False),
        sa.Column("document_id", sa.String(length=128), nullable=False),
        sa.Column("document_version_id", sa.String(length=128), nullable=False),
        sa.Column("capability", sa.String(length=32), nullable=False),
        sa.Column("build_version", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
    )
    op.create_index(
        "ix_advanced_artifacts_tenant_version",
        "knowledge_advanced_artifacts",
        ["tenant_id", "document_version_id", "capability"],
    )
    op.create_table(
        "knowledge_advanced_builds",
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=128), nullable=False),
        sa.Column("capability", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
    )
    op.create_index(
        "uq_advanced_builds_tenant_idempotency",
        "knowledge_advanced_builds",
        ["tenant_id", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_advanced_builds_status_updated",
        "knowledge_advanced_builds",
        ["status", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_advanced_builds_status_updated", table_name="knowledge_advanced_builds")
    op.drop_index("uq_advanced_builds_tenant_idempotency", table_name="knowledge_advanced_builds")
    op.drop_table("knowledge_advanced_builds")
    op.drop_index("ix_advanced_artifacts_tenant_version", table_name="knowledge_advanced_artifacts")
    op.drop_table("knowledge_advanced_artifacts")
