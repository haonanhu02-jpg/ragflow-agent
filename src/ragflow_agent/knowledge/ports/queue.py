"""Domain queue publishing contract for ingestion tasks."""

from typing import Protocol, runtime_checkable

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.ingestion import IngestionEnvelope


class QueueReceipt(KnowledgeModel):
    """Transport-neutral acknowledgement of a published envelope."""

    message_id: NonEmptyStr
    transport_reference: NonEmptyStr


@runtime_checkable
class IngestionQueuePort(Protocol):
    """Publish a versioned envelope; delivery processing remains adapter-owned."""

    async def publish(
        self,
        context: AuthorizationContext,
        envelope: IngestionEnvelope,
    ) -> QueueReceipt: ...
