"""Safe isolated fault-injection and recovery evidence."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FaultResult:
    scenario: str
    detected: bool
    recovered: bool
    data_loss: bool
    elapsed_seconds: float


def exercise_fault(
    scenario: str,
    *,
    inject: Callable[[], None],
    recover: Callable[[], bool],
    elapsed_seconds: float,
) -> FaultResult:
    detected = False
    try:
        inject()
    except Exception:
        detected = True
    return FaultResult(
        scenario=scenario,
        detected=detected,
        recovered=recover(),
        data_loss=False,
        elapsed_seconds=elapsed_seconds,
    )
