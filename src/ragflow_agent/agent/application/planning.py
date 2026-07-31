"""Bounded query planning with an optional LangChain structured-output adapter."""

from __future__ import annotations

from typing import Protocol

from langchain_core.language_models.chat_models import BaseChatModel

from ragflow_agent.agent.domain.agentic import PlanStep, QueryPlan


class QueryPlannerPort(Protocol):
    async def plan(self, question: str) -> QueryPlan: ...


class ConservativeQueryPlanner:
    """Deterministic fallback used when no real planner model is configured."""

    uses_model = False

    async def plan(self, question: str) -> QueryPlan:
        normalized = question.strip()
        if not normalized:
            raise ValueError("question must not be blank")
        complex_markers = ("并且", "以及", "比较", "对比", "分别", " and ", " compare ")
        is_simple = not any(marker in normalized.lower() for marker in complex_markers)
        if is_simple:
            return QueryPlan(
                is_simple=True,
                steps=(PlanStep(step_id="q1", question=normalized),),
            )
        parts = [part.strip(" ,;") for part in re_split(normalized) if part.strip()]
        if len(parts) < 2:
            parts = [normalized, f"核对并补充: {normalized}"]
        steps = tuple(
            PlanStep(step_id=f"q{index}", question=part, critical=True)
            for index, part in enumerate(parts[:3], start=1)
        )
        return QueryPlan(is_simple=False, steps=steps)


class LangChainStructuredQueryPlanner:
    """Use LangChain structured output while retaining server-side validation."""

    uses_model = True

    def __init__(
        self,
        model: BaseChatModel,
        *,
        allowed_tools: tuple[str, ...] = ("knowledge_base",),
    ) -> None:
        self._model = model.with_structured_output(QueryPlan)
        self._allowed_tools = frozenset(allowed_tools)

    async def plan(self, question: str) -> QueryPlan:
        result = await self._model.ainvoke(
            "将问题拆为最多三个关键子问题。只能选择服务端允许的Tool, 不要生成tenant, "
            f"凭据、URL或Tool权限。允许的Tool: {sorted(self._allowed_tools)}\n问题: {question}"
        )
        plan = QueryPlan.model_validate(result)
        if any(step.preferred_tool not in self._allowed_tools for step in plan.steps):
            raise ValueError("planner selected a Tool outside the server allowlist")
        return plan


def re_split(question: str) -> list[str]:
    import re

    normalized = question.replace("\uff0c", ",").replace("\uff1b", ";")
    return re.split(r"(?:并且|以及|同时|;|,)", normalized)
