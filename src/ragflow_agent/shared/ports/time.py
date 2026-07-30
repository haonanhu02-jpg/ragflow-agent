"""Time boundary."""

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """Return timezone-aware current time."""

    def now(self) -> datetime: ...


class SystemClock:
    """UTC system clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)
