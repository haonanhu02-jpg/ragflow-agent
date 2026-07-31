"""Server-owned Agentic RAG budget ledger and finite-stop policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ragflow_agent.agent.domain.agentic import BudgetLimits, BudgetUsage, CostStatus
from ragflow_agent.agent.domain.errors import AgentError


class BudgetDimension(StrEnum):
    AGENT_ITERATIONS = "agent_iterations"
    MODEL_CALLS = "model_calls"
    RETRIEVAL_ROUNDS = "retrieval_rounds"
    TOOL_ATTEMPTS = "tool_attempts"
    TOTAL_TOKENS = "total_tokens"
    GENERATED_TOKENS = "generated_tokens"
    ACTIVE_RUNTIME = "active_runtime_seconds"
    KNOWN_COST = "known_cost_usd"


class AgentBudgetExceeded(AgentError):
    def __init__(self, dimension: BudgetDimension) -> None:
        super().__init__(
            "Agentic RAG budget exhausted",
            error_code="agent_budget_exhausted",
            status_code=409,
            details={"dimension": dimension.value},
        )


@dataclass(slots=True)
class BudgetLedger:
    """Mutable application helper whose persisted value is immutable BudgetUsage."""

    limits: BudgetLimits
    usage: BudgetUsage = field(default_factory=BudgetUsage)

    def consume_iteration(self, count: int = 1) -> None:
        if count < 1:
            raise ValueError("Agent iteration count must be positive")
        updated = self.usage.agent_iterations + count
        if updated > self.limits.max_agent_iterations:
            raise AgentBudgetExceeded(BudgetDimension.AGENT_ITERATIONS)
        self._replace(agent_iterations=updated)

    def begin_model_call(self) -> None:
        """Reserve one model attempt before invoking an external provider."""
        updated = self.usage.model_calls + 1
        if updated > self.limits.max_model_calls:
            raise AgentBudgetExceeded(BudgetDimension.MODEL_CALLS)
        self._replace(model_calls=updated)

    def record_model_usage(
        self,
        *,
        input_tokens: int,
        generated_tokens: int,
        cost_usd: float | None = None,
        cost_status: CostStatus | None = None,
    ) -> None:
        """Record usage after a call already reserved by ``begin_model_call``."""
        if input_tokens < 0 or generated_tokens < 0:
            raise ValueError("model token usage cannot be negative")
        if cost_usd is not None and cost_usd < 0:
            raise ValueError("model cost cannot be negative")
        if self.usage.model_calls < 1:
            raise ValueError("model usage cannot be recorded before a model call begins")
        resolved_status = cost_status
        resolved_cost = cost_usd
        if resolved_status is None:
            input_rate = self.limits.model_input_cost_per_million_tokens_usd
            output_rate = self.limits.model_output_cost_per_million_tokens_usd
            if input_rate is not None and output_rate is not None:
                resolved_cost = (
                    input_tokens * input_rate + generated_tokens * output_rate
                ) / 1_000_000
                resolved_status = CostStatus.KNOWN
            else:
                resolved_status = CostStatus.UNKNOWN
        previous_calls = self.usage.model_calls - 1
        aggregate_status = _merge_cost_status(
            self.usage.cost_status,
            resolved_status,
            previous_calls=previous_calls,
        )
        self._replace(
            total_tokens=self.usage.total_tokens + input_tokens + generated_tokens,
            generated_tokens=self.usage.generated_tokens + generated_tokens,
            known_cost_usd=(
                self.usage.known_cost_usd + (resolved_cost or 0)
                if resolved_status is CostStatus.KNOWN
                else self.usage.known_cost_usd
            ),
            cost_status=aggregate_status,
        )
        for dimension in (
            BudgetDimension.TOTAL_TOKENS,
            BudgetDimension.GENERATED_TOKENS,
            BudgetDimension.KNOWN_COST,
        ):
            self._enforce(dimension)

    def consume_model(
        self,
        *,
        input_tokens: int,
        generated_tokens: int,
        cost_usd: float | None = None,
        cost_status: CostStatus = CostStatus.UNKNOWN,
    ) -> None:
        self.begin_model_call()
        self.record_model_usage(
            input_tokens=input_tokens,
            generated_tokens=generated_tokens,
            cost_usd=cost_usd,
            cost_status=cost_status,
        )

    def consume_retrieval(self) -> None:
        updated = self.usage.retrieval_rounds + 1
        if updated > self.limits.max_retrieval_rounds:
            raise AgentBudgetExceeded(BudgetDimension.RETRIEVAL_ROUNDS)
        self._replace(retrieval_rounds=updated)

    def consume_tool(self) -> None:
        updated = self.usage.tool_attempts + 1
        if updated > self.limits.max_tool_attempts:
            raise AgentBudgetExceeded(BudgetDimension.TOOL_ATTEMPTS)
        self._replace(tool_attempts=updated)

    def add_active_runtime(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("active runtime cannot decrease")
        self._replace(active_runtime_seconds=self.usage.active_runtime_seconds + seconds)
        self._enforce(BudgetDimension.ACTIVE_RUNTIME)

    @property
    def can_finalize(self) -> bool:
        return (
            self.usage.total_tokens + self.limits.finalization_token_reserve
            <= self.limits.max_total_tokens
            and self.usage.generated_tokens + self.limits.finalization_token_reserve
            <= self.limits.max_generated_tokens
        )

    def _replace(self, **updates: object) -> None:
        self.usage = self.usage.model_copy(update=updates)

    def _enforce(self, dimension: BudgetDimension) -> None:
        exceeded = {
            BudgetDimension.AGENT_ITERATIONS: (
                self.usage.agent_iterations > self.limits.max_agent_iterations
            ),
            BudgetDimension.MODEL_CALLS: self.usage.model_calls > self.limits.max_model_calls,
            BudgetDimension.RETRIEVAL_ROUNDS: (
                self.usage.retrieval_rounds > self.limits.max_retrieval_rounds
            ),
            BudgetDimension.TOOL_ATTEMPTS: (
                self.usage.tool_attempts > self.limits.max_tool_attempts
            ),
            BudgetDimension.TOTAL_TOKENS: (self.usage.total_tokens > self.limits.max_total_tokens),
            BudgetDimension.GENERATED_TOKENS: (
                self.usage.generated_tokens > self.limits.max_generated_tokens
            ),
            BudgetDimension.ACTIVE_RUNTIME: (
                self.usage.active_runtime_seconds > self.limits.max_active_runtime_seconds
            ),
            BudgetDimension.KNOWN_COST: (
                self.usage.known_cost_usd > self.limits.max_known_cost_usd
            ),
        }[dimension]
        if exceeded:
            raise AgentBudgetExceeded(dimension)


def _merge_cost_status(
    current: CostStatus,
    incoming: CostStatus,
    *,
    previous_calls: int,
) -> CostStatus:
    if previous_calls == 0:
        return incoming
    if CostStatus.UNKNOWN in {current, incoming}:
        return CostStatus.UNKNOWN
    if CostStatus.KNOWN in {current, incoming}:
        return CostStatus.KNOWN
    return CostStatus.LOCAL
