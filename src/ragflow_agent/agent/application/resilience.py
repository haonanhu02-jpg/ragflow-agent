"""Bounded retry, timeout, and cancellation for external node operations."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import cast

from ragflow_agent.agent.domain.errors import (
    AgentCancelledError,
    AgentError,
    AgentModelError,
    AgentRetryExhaustedError,
    AgentTimeoutError,
    AgentTransientError,
)
from ragflow_agent.agent.domain.limits import CancellationToken, RuntimeLimits


@dataclass(frozen=True, slots=True)
class OperationResult[T]:
    value: T
    retries: int


async def run_operation[T](
    operation_name: str,
    operation: Callable[[], Awaitable[T]],
    *,
    timeout_seconds: float,
    limits: RuntimeLimits,
    cancellation: CancellationToken,
) -> OperationResult[T]:
    """Run an operation with finite transient retries and cooperative cancellation."""
    delay = limits.retry_initial_seconds
    for attempt in range(1, limits.max_attempts + 1):
        cancellation.raise_if_cancelled()
        try:
            value = await _run_once(
                operation_name,
                operation,
                timeout_seconds=timeout_seconds,
                cancellation=cancellation,
            )
            return OperationResult(value=value, retries=attempt - 1)
        except AgentTransientError as exc:
            if attempt >= limits.max_attempts:
                raise AgentRetryExhaustedError(operation_name, attempt, exc) from exc
            await _interruptible_delay(delay, cancellation)
            delay *= limits.retry_backoff_factor
        except AgentError:
            raise
        except Exception as exc:
            raise AgentModelError(
                f"{operation_name} failed permanently",
                details={"exception_type": type(exc).__name__},
            ) from exc
    raise AssertionError("finite retry loop exited unexpectedly")


async def _run_once[T](
    operation_name: str,
    operation: Callable[[], Awaitable[T]],
    *,
    timeout_seconds: float,
    cancellation: CancellationToken,
) -> T:
    operation_task = cast(asyncio.Future[object], asyncio.ensure_future(operation()))
    cancellation_task = cast(
        asyncio.Future[object],
        asyncio.create_task(cancellation.wait()),
    )
    try:
        done, _ = await asyncio.wait(
            {operation_task, cancellation_task},
            timeout=timeout_seconds,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if cancellation_task in done:
            operation_task.cancel()
            await _await_cancelled(operation_task)
            raise AgentCancelledError(cancellation.reason)
        if operation_task not in done:
            operation_task.cancel()
            await _await_cancelled(operation_task)
            raise AgentTimeoutError(operation_name, timeout_seconds)
        return cast(T, await operation_task)
    finally:
        cancellation_task.cancel()
        await _await_cancelled(cancellation_task)


async def _interruptible_delay(delay: float, cancellation: CancellationToken) -> None:
    sleep_task = cast(asyncio.Future[object], asyncio.create_task(asyncio.sleep(delay)))
    cancellation_task = cast(
        asyncio.Future[object],
        asyncio.create_task(cancellation.wait()),
    )
    try:
        done, _ = await asyncio.wait(
            {sleep_task, cancellation_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if cancellation_task in done:
            sleep_task.cancel()
            await _await_cancelled(sleep_task)
            raise AgentCancelledError(cancellation.reason)
    finally:
        cancellation_task.cancel()
        await _await_cancelled(cancellation_task)


async def _await_cancelled(task: asyncio.Future[object]) -> None:
    with suppress(asyncio.CancelledError):
        await task
