"""Create Phase 08 Agent run, approval, and governed memory tables.

Revision ID: 20260731_0005
Revises: 20260731_0004
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260731_0005"
down_revision: str | None = "20260731_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("thread_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "run_id"),
    )
    op.create_index(
        "ix_agent_runs_tenant_thread",
        "agent_runs",
        ["tenant_id", "thread_id", "updated_at"],
    )
    op.create_table(
        "agent_approval_requests",
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("approval_id", sa.String(length=128), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "approval_id"),
    )
    op.create_index(
        "uq_agent_approval_tenant_idempotency",
        "agent_approval_requests",
        ["tenant_id", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_agent_approval_status_expiry",
        "agent_approval_requests",
        ["status", "expires_at"],
    )
    op.create_table(
        "agent_memory_consents",
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "user_id"),
    )
    op.create_table(
        "agent_long_term_memories",
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("memory_id", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "user_id", "memory_id"),
    )
    op.create_index(
        "ix_agent_memory_tenant_user_expiry",
        "agent_long_term_memories",
        ["tenant_id", "user_id", "expires_at"],
    )
    op.create_index(
        "ix_agent_memory_expiry",
        "agent_long_term_memories",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_memory_expiry", table_name="agent_long_term_memories")
    op.drop_index(
        "ix_agent_memory_tenant_user_expiry",
        table_name="agent_long_term_memories",
    )
    op.drop_table("agent_long_term_memories")
    op.drop_table("agent_memory_consents")
    op.drop_index(
        "ix_agent_approval_status_expiry",
        table_name="agent_approval_requests",
    )
    op.drop_index(
        "uq_agent_approval_tenant_idempotency",
        table_name="agent_approval_requests",
    )
    op.drop_table("agent_approval_requests")
    op.drop_index("ix_agent_runs_tenant_thread", table_name="agent_runs")
    op.drop_table("agent_runs")
