"""Transactional-outbox dispatcher to the reliable ingestion queue."""

from datetime import timedelta
from typing import Protocol

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.ingestion import IngestionEnvelope
from ragflow_agent.knowledge.domain.lifecycle import OutboxStatus
from ragflow_agent.knowledge.ports.queue import IngestionQueuePort
from ragflow_agent.knowledge.ports.uow import KnowledgeUnitOfWorkFactory
from ragflow_agent.shared.ports.time import Clock
from ragflow_agent.worker.retry import RetryPolicy, classify_failure, may_retry


class DueDocumentPurger(Protocol):
    async def purge_due(
        self,
        context: AuthorizationContext,
        *,
        document_id: str,
        reason: str,
    ) -> object: ...


class LifecycleOutboxDispatcher:
    def __init__(
        self,
        *,
        unit_of_work_factory: KnowledgeUnitOfWorkFactory,
        queue: IngestionQueuePort,
        clock: Clock,
        retry_policy: RetryPolicy,
        document_purger: DueDocumentPurger | None = None,
    ) -> None:
        self._uow = unit_of_work_factory
        self._queue = queue
        self._clock = clock
        self._policy = retry_policy
        self._document_purger = document_purger

    async def dispatch_due(self, context: AuthorizationContext, *, limit: int = 100) -> int:
        async with self._uow() as unit_of_work:
            events = await unit_of_work.lifecycle_outbox.list_due(
                tenant_id=context.tenant_id, now=self._clock.now(), limit=limit
            )
        published = 0
        for event in events:
            try:
                if event.event_type == "ingestion.requested":
                    envelope = IngestionEnvelope.model_validate(event.payload["envelope"])
                    await self._queue.publish(context, envelope)
                elif event.event_type == "document.cleanup.requested":
                    if self._document_purger is None:
                        raise RuntimeError("document purger is not configured")
                    document_id = event.payload.get("document_id")
                    if not isinstance(document_id, str) or not document_id:
                        raise ValueError("cleanup outbox event has no document_id")
                    await self._document_purger.purge_due(
                        context,
                        document_id=document_id,
                        reason="soft-delete retention elapsed",
                    )
                else:
                    raise ValueError(f"unsupported lifecycle event type: {event.event_type}")
                now = self._clock.now()
                updated = event.model_copy(
                    update={
                        "status": OutboxStatus.PUBLISHED,
                        "attempts": event.attempts + 1,
                        "published_at": now,
                        "last_error": None,
                        "updated_at": now,
                    }
                )
                published += 1
            except Exception as error:
                decision = classify_failure(error)
                attempt = event.attempts + 1
                now = self._clock.now()
                if may_retry(decision, attempt=attempt, policy=self._policy):
                    delay = self._policy.delay_seconds(
                        attempt, retry_after=decision.retry_after_seconds
                    )
                    updated = event.model_copy(
                        update={
                            "attempts": attempt,
                            "available_at": now + timedelta(seconds=delay),
                            "last_error": str(error),
                            "updated_at": now,
                        }
                    )
                else:
                    updated = event.model_copy(
                        update={
                            "status": OutboxStatus.DEAD_LETTER,
                            "attempts": attempt,
                            "last_error": str(error),
                            "updated_at": now,
                        }
                    )
            async with self._uow() as unit_of_work:
                await unit_of_work.lifecycle_outbox.save(
                    tenant_id=context.tenant_id, entity=updated
                )
                await unit_of_work.commit()
        return published
