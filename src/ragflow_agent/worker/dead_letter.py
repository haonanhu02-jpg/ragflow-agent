"""Persistent dead-letter transition helpers."""

from datetime import datetime

from ragflow_agent.knowledge.domain.lifecycle import (
    LifecycleError,
    LifecycleOperation,
    LifecycleOperationStatus,
)


def move_to_dead_letter(
    operation: LifecycleOperation,
    error: LifecycleError,
    *,
    changed_at: datetime,
) -> LifecycleOperation:
    """Return an auditable terminal operation after retry exhaustion."""
    return operation.model_copy(
        update={
            "status": LifecycleOperationStatus.DEAD_LETTER,
            "attempts": operation.attempts + 1,
            "error": error,
            "next_attempt_at": None,
            "updated_at": changed_at,
        }
    )
