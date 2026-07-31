"""Configure the optional model-backed planner behind the LangChain boundary."""

from langchain_openai import ChatOpenAI

from ragflow_agent.agent.application.planning import (
    ConservativeQueryPlanner,
    LangChainStructuredQueryPlanner,
    QueryPlannerPort,
)
from ragflow_agent.config import AppSettings


def build_query_planner(
    settings: AppSettings,
    *,
    allowed_tools: tuple[str, ...],
) -> QueryPlannerPort:
    """Use DeepSeek-compatible structured planning only when credentials exist."""
    if settings.models.chat_api_key is None:
        return ConservativeQueryPlanner()
    model = ChatOpenAI(
        model=settings.models.chat_model,
        base_url=settings.models.chat_base_url,
        api_key=settings.models.chat_api_key,
        timeout=settings.agentic_rag.model_timeout_seconds,
        max_completion_tokens=settings.agentic_rag.max_generated_tokens,
        temperature=0,
    )
    return LangChainStructuredQueryPlanner(model, allowed_tools=allowed_tools)
