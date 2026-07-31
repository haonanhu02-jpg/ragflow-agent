"""Content-minimized trace recording, privileged reads, and TTL cleanup."""

from __future__ import annotations

import logging
from datetime import datetime

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.errors import KnowledgeAuthorizationError
from ragflow_agent.knowledge.domain.retrieval import RetrievalTrace
from ragflow_agent.knowledge.ports.trace import (
    RetrievalTraceMetricsPort,
    RetrievalTraceStorePort,
)


class LoggingRetrievalTraceMetrics:
    """Observable in-process failure counter with content-free warning logs."""

    def __init__(self) -> None:
        self.write_failure_count = 0
        self._logger = logging.getLogger("ragflow_agent.retrieval.trace")

    def record_write_failure(self, *, tenant_id: str, reason: str) -> None:
        self.write_failure_count += 1
        self._logger.warning(
            "retrieval_trace_write_failed",
            extra={"tenant_id": tenant_id, "reason": reason},
        )


class SafeRetrievalTraceRecorder:
    """Never let trace persistence failure break a successful retrieval."""

    def __init__(
        self,
        store: RetrievalTraceStorePort,
        metrics: RetrievalTraceMetricsPort,
    ) -> None:
        self._store = store
        self._metrics = metrics

    async def record(self, trace: RetrievalTrace) -> None:
        try:
            await self._store.save(trace)
        except Exception as error:
            self._metrics.record_write_failure(
                tenant_id=trace.tenant_id,
                reason=type(error).__name__,
            )


class RetrievalTraceAccessService:
    """Read detailed traces only for explicitly privileged tenant principals."""

    def __init__(
        self,
        store: RetrievalTraceStorePort,
        *,
        detailed_roles: tuple[str, ...],
    ) -> None:
        self._store = store
        self._detailed_roles = frozenset(detailed_roles)

    async def get_detailed(
        self,
        context: AuthorizationContext,
        trace_id: str,
    ) -> RetrievalTrace | None:
        if not self._detailed_roles.intersection(context.roles):
            raise KnowledgeAuthorizationError(
                reason_code="retrieval_trace_debug_role_required",
                trace_id=context.request_id,
            )
        return await self._store.get(context, trace_id)


class RetrievalTraceMaintenanceService:
    """Executable expiry cleanup boundary suitable for Worker scheduling."""

    def __init__(self, store: RetrievalTraceStorePort) -> None:
        self._store = store

    async def cleanup_expired(self, *, before: datetime) -> int:
        return await self._store.delete_expired(before=before)
