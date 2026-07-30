"""Data-minimized lifecycle trace sink."""

import logging

from ragflow_agent.knowledge.ports.trace import KnowledgeTraceEvent


class LoggingKnowledgeTrace:
    """Record identifiers and actions without logging source text."""

    def __init__(self) -> None:
        self._logger = logging.getLogger("ragflow_agent.knowledge")

    async def record(self, event: KnowledgeTraceEvent) -> None:
        self._logger.info(
            "knowledge_event",
            extra={
                "trace_id": event.trace_id,
                "request_id": event.request_id,
                "tenant_id": event.tenant_id,
                "actor_id": event.actor_id,
                "kind": event.kind.value,
                "action": event.action,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
            },
        )
