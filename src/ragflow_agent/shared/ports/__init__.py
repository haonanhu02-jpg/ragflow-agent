"""Provider-neutral foundation ports.

Knowledge-base and retrieval protocols intentionally belong to Phase 03 and
are not defined here.
"""

from ragflow_agent.shared.ports.identity import IdGenerator, Uuid4Generator
from ragflow_agent.shared.ports.lifecycle import LifecyclePort
from ragflow_agent.shared.ports.model import ModelPort
from ragflow_agent.shared.ports.object_store import ObjectStorePort
from ragflow_agent.shared.ports.queue import QueueMessage, QueuePort
from ragflow_agent.shared.ports.search import SearchPort
from ragflow_agent.shared.ports.time import Clock, SystemClock

__all__ = [
    "Clock",
    "IdGenerator",
    "LifecyclePort",
    "ModelPort",
    "ObjectStorePort",
    "QueueMessage",
    "QueuePort",
    "SearchPort",
    "SystemClock",
    "Uuid4Generator",
]
