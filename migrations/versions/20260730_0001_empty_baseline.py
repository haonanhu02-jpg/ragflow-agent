"""Establish an empty Phase 01 migration baseline.

Revision ID: 20260730_0001
Revises:
Create Date: 2026-07-30
"""

from collections.abc import Sequence

revision: str = "20260730_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create no business tables in Phase 01."""


def downgrade() -> None:
    """Remove no business tables in Phase 01."""
