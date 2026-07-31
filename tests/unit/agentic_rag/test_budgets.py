import pytest

from ragflow_agent.agent.application.budgets import AgentBudgetExceeded, BudgetLedger
from ragflow_agent.agent.domain.agentic import BudgetLimits, BudgetUsage, CostStatus


@pytest.mark.parametrize(
    ("operation", "usage"),
    [
        (lambda ledger: ledger.consume_iteration(), BudgetUsage(agent_iterations=1)),
        (lambda ledger: ledger.consume_retrieval(), BudgetUsage(retrieval_rounds=1)),
        (lambda ledger: ledger.consume_tool(), BudgetUsage(tool_attempts=1)),
        (lambda ledger: ledger.add_active_runtime(1), BudgetUsage(active_runtime_seconds=1)),
    ],
)
def test_each_server_budget_is_a_hard_limit(operation: object, usage: BudgetUsage) -> None:
    limits = BudgetLimits(
        max_agent_iterations=1,
        max_retrieval_rounds=1,
        max_tool_attempts=1,
        max_active_runtime_seconds=1,
    )
    ledger = BudgetLedger(limits, usage)

    with pytest.raises(AgentBudgetExceeded):
        operation(ledger)  # type: ignore[operator]


def test_token_generated_and_known_cost_budgets_are_server_owned() -> None:
    ledger = BudgetLedger(
        BudgetLimits(
            max_model_calls=1,
            max_total_tokens=10,
            max_generated_tokens=5,
            finalization_token_reserve=1,
        )
    )
    ledger.consume_model(
        input_tokens=5,
        generated_tokens=5,
        cost_usd=0.25,
        cost_status=CostStatus.KNOWN,
    )

    with pytest.raises(AgentBudgetExceeded):
        ledger.consume_model(
            input_tokens=1,
            generated_tokens=1,
            cost_usd=0.01,
            cost_status=CostStatus.KNOWN,
        )


def test_resume_uses_persisted_usage_instead_of_resetting() -> None:
    ledger = BudgetLedger(
        BudgetLimits(max_tool_attempts=2),
        BudgetUsage(tool_attempts=2),
    )

    with pytest.raises(AgentBudgetExceeded):
        ledger.consume_tool()


def test_model_call_is_blocked_before_provider_and_usage_does_not_increase() -> None:
    ledger = BudgetLedger(BudgetLimits(max_model_calls=1), BudgetUsage(model_calls=1))

    with pytest.raises(AgentBudgetExceeded):
        ledger.begin_model_call()

    assert ledger.usage.model_calls == 1


def test_unknown_call_does_not_disable_known_cost_cap() -> None:
    ledger = BudgetLedger(BudgetLimits(max_model_calls=3, max_known_cost_usd=0.10))
    ledger.consume_model(
        input_tokens=1,
        generated_tokens=1,
        cost_usd=0.10,
        cost_status=CostStatus.KNOWN,
    )
    ledger.consume_model(
        input_tokens=1,
        generated_tokens=1,
        cost_status=CostStatus.UNKNOWN,
    )

    with pytest.raises(AgentBudgetExceeded):
        ledger.consume_model(
            input_tokens=1,
            generated_tokens=1,
            cost_usd=0.01,
            cost_status=CostStatus.KNOWN,
        )

    assert ledger.usage.cost_status is CostStatus.UNKNOWN


def test_negative_provider_usage_cannot_reduce_budget() -> None:
    ledger = BudgetLedger(BudgetLimits())
    ledger.begin_model_call()

    with pytest.raises(ValueError, match="cannot be negative"):
        ledger.record_model_usage(input_tokens=-1, generated_tokens=0)
