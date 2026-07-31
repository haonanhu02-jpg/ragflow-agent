"""Agent-specific infrastructure adapters."""

from ragflow_agent.agent.infrastructure.sql import SqlAlchemyReadOnlyExecutor

__all__ = ["SqlAlchemyReadOnlyExecutor"]
