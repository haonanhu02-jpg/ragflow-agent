"""Worker-facing cooperative cancellation export."""

from ragflow_agent.knowledge.domain.lifecycle import require_not_cancelled

__all__ = ["require_not_cancelled"]
