"""ARQ process entry and persisted ingestion dispatch."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from arq import Retry, create_pool
from arq.connections import RedisSettings
from arq.cron import cron
from arq.typing import StartupShutdown, WorkerCoroutine
from arq.worker import Worker

from ragflow_agent.agent.application.memory import LongTermMemoryService
from ragflow_agent.agent.infrastructure.database import SqlAlchemyMemoryRepository
from ragflow_agent.config import AppSettings
from ragflow_agent.infrastructure.database import create_session_factory
from ragflow_agent.knowledge.application.ingestion import RetryableIngestionError
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.ingestion import IngestionEnvelope
from ragflow_agent.knowledge.infrastructure.queue import arq_deserialize, arq_serialize
from ragflow_agent.knowledge.runtime import MinimumRagRuntime, build_minimum_rag_runtime
from ragflow_agent.shared.ports.identity import Uuid4Generator
from ragflow_agent.shared.ports.time import SystemClock


async def process_ingestion(context: dict[Any, Any], envelope_json: str) -> str:
    """Validate a JSON envelope and execute one persisted pipeline delivery."""
    runtime = context.get("minimum_rag_runtime")
    if not isinstance(runtime, MinimumRagRuntime):
        raise RuntimeError("ARQ worker runtime is not initialized")
    envelope = IngestionEnvelope.model_validate_json(envelope_json)
    delivery_attempt = int(context.get("job_try", 1))
    try:
        job = await runtime.ingestion_pipeline.handle(
            envelope,
            delivery_attempt=delivery_attempt,
        )
    except RetryableIngestionError as error:
        raise Retry(defer=min(2**delivery_attempt, 30)) from error
    return job.id


async def dispatch_lifecycle_outbox(
    context: dict[Any, Any], tenant_id: str, request_id: str
) -> int:
    """Dispatch one tenant's due outbox rows; duplicate jobs remain harmless."""
    runtime = context.get("minimum_rag_runtime")
    if not isinstance(runtime, MinimumRagRuntime):
        raise RuntimeError("ARQ worker runtime is not initialized")
    return await runtime.lifecycle_outbox.dispatch_due(
        AuthorizationContext(
            tenant_id=tenant_id,
            actor_id="lifecycle-worker",
            request_id=request_id,
        )
    )


async def reconcile_lifecycle(context: dict[Any, Any], tenant_id: str, request_id: str) -> int:
    """Run a bounded dry-run reconciliation for a declared tenant scope."""
    runtime = context.get("minimum_rag_runtime")
    if not isinstance(runtime, MinimumRagRuntime):
        raise RuntimeError("ARQ worker runtime is not initialized")
    report = await runtime.lifecycle_reconciler.run(
        AuthorizationContext(
            tenant_id=tenant_id,
            actor_id="lifecycle-worker",
            request_id=request_id,
        ),
        stale_before=datetime.now(UTC) - timedelta(hours=1),
        dry_run=True,
    )
    return len(report.findings)


async def cleanup_agent_memories(context: dict[Any, Any]) -> int:
    """Physically delete expired governed memories on a bounded six-hour schedule."""
    runtime = context.get("minimum_rag_runtime")
    settings = context.get("settings")
    if not isinstance(runtime, MinimumRagRuntime) or not isinstance(settings, AppSettings):
        raise RuntimeError("ARQ worker runtime is not initialized")
    service = LongTermMemoryService(
        repository=SqlAlchemyMemoryRepository(create_session_factory(runtime.engine)),
        id_generator=Uuid4Generator(),
        clock=SystemClock(),
        ttl_days=settings.agentic_rag.memory_ttl_days,
    )
    return await service.cleanup_expired()


async def run_arq_ingestion_worker(
    settings: AppSettings,
    *,
    burst: bool = False,
) -> None:
    """Run the independent ARQ Worker with explicit resource ownership."""
    redis_pool = await create_pool(
        RedisSettings.from_dsn(settings.queue.url.get_secret_value()),
        default_queue_name=settings.queue.queue_name,
        job_serializer=arq_serialize,
        job_deserializer=arq_deserialize,
    )
    runtime = build_minimum_rag_runtime(settings)

    async def startup(context: dict[Any, Any]) -> None:
        await runtime.open(open_queue=False)
        context["minimum_rag_runtime"] = runtime
        context["settings"] = settings

    async def shutdown(context: dict[Any, Any]) -> None:
        context.pop("minimum_rag_runtime", None)
        context.pop("settings", None)
        await runtime.close()

    worker = Worker(
        functions=[
            cast(WorkerCoroutine, process_ingestion),
            cast(WorkerCoroutine, dispatch_lifecycle_outbox),
            cast(WorkerCoroutine, reconcile_lifecycle),
            cast(WorkerCoroutine, cleanup_agent_memories),
        ],
        cron_jobs=[
            cron(
                cast(WorkerCoroutine, cleanup_agent_memories),
                name="cleanup_agent_memories",
                hour={0, 6, 12, 18},
                minute=0,
                unique=True,
                max_tries=1,
            )
        ],
        queue_name=settings.queue.queue_name,
        redis_pool=redis_pool,
        burst=burst,
        on_startup=cast(StartupShutdown, startup),
        on_shutdown=cast(StartupShutdown, shutdown),
        job_timeout=settings.worker.job_timeout_seconds,
        max_tries=settings.worker.max_tries,
        retry_jobs=True,
        allow_abort_jobs=True,
        job_serializer=arq_serialize,
        job_deserializer=arq_deserialize,
        ctx={},
    )
    await worker.async_run()
