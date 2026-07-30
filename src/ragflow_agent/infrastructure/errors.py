"""Errors raised by infrastructure wiring."""

from ragflow_agent.shared.errors import AppError


class InfrastructureNotConfiguredError(AppError):
    """Raised instead of pretending an unavailable adapter is operational."""

    def __init__(self, component: str) -> None:
        super().__init__(
            f"{component} adapter is not configured",
            error_code="infrastructure_not_configured",
            status_code=503,
            details={"component": component},
        )
