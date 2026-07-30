"""AgentState versioning, safety, and identity tests."""

import pytest
from pydantic import ValidationError

from ragflow_agent.agent.domain import (
    AgentCheckpointError,
    AgentResumeRequest,
    AgentResumeToken,
    AgentState,
    AgentStateVersionError,
    ModelDecision,
    ToolCall,
)
from ragflow_agent.agent.domain.state import (
    graph_state_from_model,
    migrate_state_payload,
    model_from_graph_state,
)
from tests.fakes.agent import agent_identity


def test_state_serialization_round_trip_is_deterministic() -> None:
    state = AgentState.initial(agent_identity(), "inspect status")

    restored = model_from_graph_state(graph_state_from_model(state))

    assert restored == state
    assert restored.checkpoint_payload() == state.checkpoint_payload()


def test_known_v0_payload_migrates_to_v1() -> None:
    payload = AgentState.initial(agent_identity(), "legacy").checkpoint_payload()
    payload["version"] = 0
    for field in (
        "route",
        "pending_tool_call",
        "tool_results",
        "current_node",
        "step_count",
        "retry_count",
        "final_answer",
        "error_code",
        "termination_reason",
        "event_sequence",
    ):
        payload.pop(field)

    migrated = migrate_state_payload(payload)

    assert AgentState.model_validate(migrated).version == 1


def test_unknown_state_version_is_rejected() -> None:
    payload = AgentState.initial(agent_identity(), "future").checkpoint_payload()
    payload["version"] = 99

    with pytest.raises(AgentStateVersionError) as captured:
        model_from_graph_state(payload)

    assert captured.value.error_code == "agent_state_version_unsupported"


def test_checkpoint_rejects_secret_like_tool_fields() -> None:
    with pytest.raises(ValidationError, match="checkpoint-safe"):
        ToolCall(call_id="call", name="unsafe", arguments={"api_key": "must-not-persist"})


def test_model_decision_requires_a_valid_branch() -> None:
    with pytest.raises(ValidationError, match="require content"):
        ModelDecision(kind="final")
    with pytest.raises(ValidationError, match="require tool_name"):
        ModelDecision(kind="tool")


def test_resume_token_is_tenant_and_run_bound() -> None:
    identity = agent_identity()
    token = AgentResumeToken.from_identity(identity)
    other_tenant = agent_identity(tenant_id="tenant-b")

    AgentResumeRequest(identity=identity, resume_token=token)
    with pytest.raises(AgentCheckpointError, match="does not own"):
        AgentResumeRequest(identity=other_tenant, resume_token=token)
