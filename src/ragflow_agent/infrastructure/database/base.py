"""Declarative metadata root; Phase 01 intentionally defines no business tables."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for future SQLAlchemy mappings."""
