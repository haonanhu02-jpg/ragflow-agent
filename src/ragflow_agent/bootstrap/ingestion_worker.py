"""Independent ingestion-worker process entrypoint."""

from __future__ import annotations

import argparse
import asyncio
import signal
from contextlib import suppress

from ragflow_agent.config import AppSettings, WorkerSettings, load_settings
from ragflow_agent.infrastructure.queue import DevelopmentIdleQueue, UnconfiguredQueue
from ragflow_agent.shared.ports import QueuePort
from ragflow_agent.worker import IngestionWorker, WorkerState
from ragflow_agent.worker.arq_worker import run_arq_ingestion_worker


def build_worker(
    settings: WorkerSettings | None = None,
    *,
    queue: QueuePort | None = None,
) -> IngestionWorker:
    """Wire the Phase 01 shell without selecting deferred queue semantics."""
    worker_settings = settings or load_settings().worker
    return IngestionWorker(queue=queue or UnconfiguredQueue(), settings=worker_settings)


def check_bootstrap() -> None:
    """Validate process wiring without opening infrastructure."""
    worker = build_worker(WorkerSettings())
    if worker.state is not WorkerState.STOPPED:
        raise RuntimeError("new worker must be stopped")
    if not isinstance(worker.queue, QueuePort):
        raise RuntimeError("worker queue does not satisfy QueuePort")


async def run_worker(
    settings: AppSettings,
    *,
    development_idle: bool = False,
) -> None:
    if development_idle and settings.environment != "development":
        raise RuntimeError("--development-idle is restricted to the development environment")
    if not development_idle:
        await run_arq_ingestion_worker(settings)
        return
    queue: QueuePort = DevelopmentIdleQueue()
    worker = build_worker(settings.worker, queue=queue)
    loop = asyncio.get_running_loop()
    for signal_name in ("SIGINT", "SIGTERM"):
        shutdown_signal = getattr(signal, signal_name, None)
        if shutdown_signal is not None:
            with suppress(NotImplementedError):
                loop.add_signal_handler(shutdown_signal, worker.request_stop)
    await worker.run()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ragflow-agent ingestion worker")
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate process wiring without opening infrastructure",
    )
    parser.add_argument(
        "--development-idle",
        action="store_true",
        help="run a non-consuming worker shell; development environment only",
    )
    args = parser.parse_args()
    if args.check:
        check_bootstrap()
        print("Ingestion worker bootstrap check passed")
        return
    asyncio.run(run_worker(load_settings(), development_idle=args.development_idle))


if __name__ == "__main__":
    main()
