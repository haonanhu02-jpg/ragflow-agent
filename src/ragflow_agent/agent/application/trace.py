"""Content-free observability for non-blocking Agent run trace failures."""

from __future__ import annotations

import logging


class LoggingAgentRunTraceMetrics:
    def __init__(self) -> None:
        self.write_failure_count = 0
        self._logger = logging.getLogger("ragflow_agent.agentic.trace")

    def record_write_failure(self, *, tenant_id: str, reason: str) -> None:
        self.write_failure_count += 1
        self._logger.warning(
            "agent_run_trace_write_failed",
            extra={"tenant_id": tenant_id, "reason": reason},
        )
