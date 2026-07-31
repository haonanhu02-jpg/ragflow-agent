import pytest
from pydantic import ValidationError

from ragflow_agent.agent.application.planning import ConservativeQueryPlanner
from ragflow_agent.agent.domain.agentic import PlanStep, QueryPlan


@pytest.mark.asyncio
async def test_simple_question_skips_decomposition() -> None:
    plan = await ConservativeQueryPlanner().plan("设备复位步骤是什么")

    assert plan.is_simple is True
    assert tuple(step.step_id for step in plan.steps) == ("q1",)


@pytest.mark.asyncio
async def test_complex_question_is_bounded_and_contains_no_security_context() -> None:
    plan = await ConservativeQueryPlanner().plan("比较A设备和B设备, 以及各自维护周期")

    assert plan.is_simple is False
    assert 2 <= len(plan.steps) <= 3
    assert "tenant" not in plan.model_dump_json().lower()


def test_plan_rejects_forward_dependencies_and_too_many_steps() -> None:
    with pytest.raises(ValidationError):
        QueryPlan(
            is_simple=False,
            steps=(PlanStep(step_id="q1", question="x", depends_on=("q2",)),),
        )
