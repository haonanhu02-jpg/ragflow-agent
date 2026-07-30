"""Stable Agent error taxonomy used by nodes, adapters, and callers."""

from __future__ import annotations

from collections.abc import Mapping

from ragflow_agent.shared import AppError


class AgentError(AppError):
    """Base class for stable Agent runtime failures."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str,
        status_code: int = 500,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            status_code=status_code,
            details=details,
        )


class AgentStateVersionError(AgentError):
    """The checkpointed state cannot be interpreted by this runtime."""

    def __init__(self, version: object) -> None:
        super().__init__(
            "unsupported Agent state version",
            error_code="agent_state_version_unsupported",
            status_code=409,
            details={"version": version},
        )


class AgentCheckpointError(AgentError):
    """Checkpoint identity or persistence validation failed."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "agent_checkpoint_invalid",
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            status_code=409,
            details=details,
        )


class AgentTransientError(AgentError):
    """An operation may be retried without changing its input."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "agent_transient_failure",
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message, error_code=error_code, details=details)


class AgentRetryExhaustedError(AgentError):
    """A retryable operation exhausted its finite attempt budget."""

    def __init__(self, operation: str, attempts: int, cause: AgentError) -> None:
        super().__init__(
            f"{operation} exhausted its retry attempts",
            error_code="agent_retry_exhausted",
            details={
                "operation": operation,
                "attempts": attempts,
                "cause_error_code": cause.error_code,
            },
        )


class AgentTimeoutError(AgentError):
    """A node or complete graph exceeded its hard timeout."""

    def __init__(self, operation: str, timeout_seconds: float) -> None:
        super().__init__(
            f"{operation} timed out",
            error_code="agent_timeout",
            status_code=504,
            details={"operation": operation, "timeout_seconds": timeout_seconds},
        )


class AgentCancelledError(AgentError):
    """The caller requested cooperative cancellation."""

    def __init__(self, reason: str) -> None:
        super().__init__(
            "Agent execution was cancelled",
            error_code="agent_cancelled",
            status_code=409,
            details={"reason": reason},
        )


class AgentStepLimitError(AgentError):
    """The graph reached its technical recursion safety limit."""

    def __init__(self, max_steps: int) -> None:
        super().__init__(
            "Agent graph exceeded its maximum step count",
            error_code="agent_step_limit_exceeded",
            status_code=409,
            details={"max_steps": max_steps},
        )


class AgentModelError(AgentError):
    """The model adapter returned an invalid or permanent failure."""

    def __init__(self, message: str, *, details: Mapping[str, object] | None = None) -> None:
        super().__init__(
            message,
            error_code="agent_model_failure",
            status_code=502,
            details=details,
        )


class AgentToolError(AgentError):
    """Tool selection, policy, input, or execution failed."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "agent_tool_failure",
        status_code: int = 422,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            status_code=status_code,
            details=details,
        )
