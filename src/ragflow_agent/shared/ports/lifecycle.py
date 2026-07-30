"""Lifecycle contract shared by external infrastructure adapters."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class LifecyclePort(Protocol):
    """Minimal lifecycle without assuming a vendor client."""

    async def open(self) -> None: ...

    async def close(self) -> None: ...

    async def is_ready(self) -> bool: ...
