"""Framework-independent Agent domain contracts."""

from ragflow_agent.agent.domain.errors import (
    AgentCancelledError,
    AgentCheckpointError,
    AgentError,
    AgentRetryExhaustedError,
    AgentStateVersionError,
    AgentStepLimitError,
    AgentTimeoutError,
    AgentTransientError,
)
from ragflow_agent.agent.domain.events import AgentEvent, AgentEventType
from ragflow_agent.agent.domain.limits import CancellationToken, RuntimeLimits
from ragflow_agent.agent.domain.state import (
    AgentAuthorizationContext,
    AgentMessage,
    AgentResumeRequest,
    AgentResumeToken,
    AgentRunIdentity,
    AgentRunRequest,
    AgentRunResult,
    AgentState,
    ModelDecision,
    ToolCall,
    ToolExecutionResult,
)

__all__ = [
    "AgentAuthorizationContext",
    "AgentCancelledError",
    "AgentCheckpointError",
    "AgentError",
    "AgentEvent",
    "AgentEventType",
    "AgentMessage",
    "AgentResumeRequest",
    "AgentResumeToken",
    "AgentRetryExhaustedError",
    "AgentRunIdentity",
    "AgentRunRequest",
    "AgentRunResult",
    "AgentState",
    "AgentStateVersionError",
    "AgentStepLimitError",
    "AgentTimeoutError",
    "AgentTransientError",
    "CancellationToken",
    "ModelDecision",
    "RuntimeLimits",
    "ToolCall",
    "ToolExecutionResult",
]
