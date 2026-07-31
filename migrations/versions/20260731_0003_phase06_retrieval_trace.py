"""Create the Phase 06 minimized retrieval trace table.

Revision ID: 20260731_0003
Revises: 20260730_0002
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260731_0003"
down_revision: str | None = "20260730_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create tenant-isolated content-minimized retrieval trace storage."""
    op.create_table(
        "knowledge_retrieval_traces",
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("trace_id", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "trace_id"),
    )
    op.create_index(
        "ix_retrieval_traces_tenant_expires",
        "knowledge_retrieval_traces",
        ["tenant_id", "expires_at"],
    )
    op.create_index(
        "ix_retrieval_traces_expires",
        "knowledge_retrieval_traces",
        ["expires_at"],
    )


def downgrade() -> None:
    """Drop only the Phase 06 trace storage."""
    op.drop_index("ix_retrieval_traces_expires", table_name="knowledge_retrieval_traces")
    op.drop_index(
        "ix_retrieval_traces_tenant_expires",
        table_name="knowledge_retrieval_traces",
    )
    op.drop_table("knowledge_retrieval_traces")
