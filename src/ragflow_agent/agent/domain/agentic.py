"""Checkpoint-safe Phase 08 Agentic RAG domain contracts."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AgenticModel(BaseModel):
    """Strict immutable base for policy and checkpoint DTOs."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class AgenticRunStatus(StrEnum):
    COMPLETED = "completed"
    PARTIAL_EVIDENCE = "partial_evidence"
    NO_EVIDENCE = "no_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    APPROVAL_REQUIRED = "approval_required"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    BUDGET_EXHAUSTED = "budget_exhausted"
    FAILED = "failed"


class EvidenceStatus(StrEnum):
    SUFFICIENT = "sufficient"
    PARTIAL_EVIDENCE = "partial_evidence"
    NO_EVIDENCE = "no_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"


class ToolEffect(StrEnum):
    READ_ONLY = "read_only"
    SIDE_EFFECTING = "side_effecting"


class ToolRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(StrEnum):
    APPROVAL_REQUIRED = "approval_required"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class CostStatus(StrEnum):
    KNOWN = "known"
    UNKNOWN = "unknown"
    LOCAL = "local"


class AgenticAuthorizationSnapshot(AgenticModel):
    tenant_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    roles: tuple[str, ...] = ()
    knowledge_base_ids: tuple[str, ...] = ()

    @field_validator("roles", "knowledge_base_ids")
    @classmethod
    def values_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("authorization collections must be unique")
        return value


class ToolAuthorizationContext(AgenticModel):
    """Trusted execution identity owned by the Agent boundary."""

    tenant_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    roles: tuple[str, ...] = ()


class KnowledgeCitation(AgenticModel):
    """Version-bound citation contract copied at the Tool boundary."""

    schema_version: int = 2
    tenant_id: str
    knowledge_base_id: str
    document_id: str
    document_version_id: str
    chunk_id: str
    quote: str
    page_number: int | None = None
    bounding_box: dict[str, object] | None = None
    source_uri: str | None = None
    media_kind: str | None = None
    time_start_seconds: float | None = Field(default=None, ge=0)
    time_end_seconds: float | None = Field(default=None, ge=0)
    observed_at: datetime | None = None


class DirectRagAnswer(AgenticModel):
    answer: str
    citations: tuple[KnowledgeCitation, ...]
    trace_id: str
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)


class ToolRegistration(AgenticModel):
    """Server-owned Tool metadata; model output can only select its name."""

    tool_name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str = ""
    input_schema: dict[str, object] = Field(default_factory=dict)
    output_schema: dict[str, object] = Field(default_factory=dict)
    effect: ToolEffect
    risk_level: ToolRiskLevel
    allowed_tenant_ids: tuple[str, ...] = ()
    allowed_roles: tuple[str, ...] = ()
    approval_roles: tuple[str, ...] = ()
    allowed_business_scopes: tuple[str, ...] = ()
    timeout_seconds: float = Field(default=15, gt=0, le=300)
    max_retries: int = Field(default=0, ge=0, le=5)
    max_output_bytes: int = Field(default=1_000_000, ge=1, le=20_000_000)
    idempotent: bool
    requires_hitl: bool
    sensitive_fields: tuple[str, ...] = ()

    @model_validator(mode="after")
    def approval_roles_are_explicit(self) -> ToolRegistration:
        if self.requires_hitl and not self.approval_roles:
            raise ValueError("HITL Tools require at least one approval role")
        if self.effect is ToolEffect.SIDE_EFFECTING and not self.idempotent:
            raise ValueError("side-effecting Tools must implement idempotent call IDs")
        return self


class ToolInvocation(AgenticModel):
    tool_call_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    tool_version: str = Field(min_length=1)
    arguments: dict[str, object] = Field(default_factory=dict)
    business_scope: str | None = None

    @property
    def argument_digest(self) -> str:
        material = json.dumps(self.arguments, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(material.encode("utf-8")).hexdigest()


class ToolCallSummary(AgenticModel):
    tool_call_id: str
    tool_name: str
    tool_version: str
    argument_digest: str
    status: str
    output_digest: str | None = None
    error_code: str | None = None
    retrieval_trace_id: str | None = None


class ToolExecutionOutcome(AgenticModel):
    status: Literal["success", "approval_required", "failed"]
    summary: ToolCallSummary
    output: object | None = None
    approval_reason: str | None = None
    required_roles: tuple[str, ...] = ()
    injection_detected: bool = False


class PlanStep(AgenticModel):
    step_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    critical: bool = True
    depends_on: tuple[str, ...] = ()
    preferred_tool: str = "knowledge_base"
    tool_version: str = "1"
    tool_arguments: dict[str, object] = Field(default_factory=dict)


class QueryPlan(AgenticModel):
    is_simple: bool
    steps: tuple[PlanStep, ...] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def dependencies_reference_earlier_steps(self) -> QueryPlan:
        seen: set[str] = set()
        for step in self.steps:
            if step.step_id in seen:
                raise ValueError("plan step IDs must be unique")
            if any(parent not in seen for parent in step.depends_on):
                raise ValueError("plan dependencies must reference earlier steps")
            seen.add(step.step_id)
        if self.is_simple and len(self.steps) != 1:
            raise ValueError("simple plans require exactly one step")
        return self


class EvidenceItem(AgenticModel):
    evidence_id: str
    step_id: str
    source_kind: Literal["knowledge", "sql", "api"]
    tenant_id: str
    knowledge_base_id: str | None = None
    excerpt: str = Field(max_length=2_000)
    normalized_score: float = Field(ge=0, le=1)
    citation: AgentEvidenceCitation | None = None
    authorized: bool = True
    active_version: bool = True
    injection_detected: bool = False
    fact_key: str | None = None
    stance: str | None = None


class EvidenceDecision(AgenticModel):
    status: EvidenceStatus
    covered_critical_steps: tuple[str, ...] = ()
    missing_critical_steps: tuple[str, ...] = ()
    conflicting_fact_keys: tuple[str, ...] = ()
    eligible_evidence_ids: tuple[str, ...] = ()
    reason: str


class AgentEvidenceCitation(AgenticModel):
    citation_id: str
    source_kind: Literal["knowledge", "sql", "api"]
    knowledge: KnowledgeCitation | None = None
    tool_name: str | None = None
    result_digest: str | None = None

    @model_validator(mode="after")
    def source_reference_is_complete(self) -> AgentEvidenceCitation:
        if self.source_kind == "knowledge" and self.knowledge is None:
            raise ValueError("knowledge evidence requires a version-bound Citation")
        if self.source_kind != "knowledge" and (not self.tool_name or not self.result_digest):
            raise ValueError("Tool evidence requires tool name and result digest")
        return self


class BudgetLimits(AgenticModel):
    max_agent_iterations: int = Field(default=8, ge=1)
    max_model_calls: int = Field(default=6, ge=1)
    max_retrieval_rounds: int = Field(default=3, ge=1)
    max_tool_attempts: int = Field(default=10, ge=1)
    max_total_tokens: int = Field(default=50_000, ge=1)
    max_generated_tokens: int = Field(default=8_000, ge=1)
    finalization_token_reserve: int = Field(default=1_500, ge=0)
    max_active_runtime_seconds: float = Field(default=120, gt=0)
    max_known_cost_usd: float = Field(default=0.50, ge=0)
    model_input_cost_per_million_tokens_usd: float | None = Field(default=None, ge=0)
    model_output_cost_per_million_tokens_usd: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def reserve_fits_total(self) -> BudgetLimits:
        if self.finalization_token_reserve > self.max_total_tokens:
            raise ValueError("finalization reserve exceeds total token budget")
        if (self.model_input_cost_per_million_tokens_usd is None) != (
            self.model_output_cost_per_million_tokens_usd is None
        ):
            raise ValueError("model input and output rates must be configured together")
        return self


class BudgetUsage(AgenticModel):
    agent_iterations: int = Field(default=0, ge=0)
    model_calls: int = Field(default=0, ge=0)
    retrieval_rounds: int = Field(default=0, ge=0)
    tool_attempts: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    generated_tokens: int = Field(default=0, ge=0)
    active_runtime_seconds: float = Field(default=0, ge=0)
    known_cost_usd: float = Field(default=0, ge=0)
    cost_status: CostStatus = CostStatus.UNKNOWN


class ApprovalRequest(AgenticModel):
    approval_id: str
    run_id: str
    thread_id: str
    tool_call_id: str
    tool_name: str
    tool_version: str
    argument_digest: str
    tenant_id: str
    user_id: str
    reason: str
    required_roles: tuple[str, ...]
    created_at: datetime
    expires_at: datetime
    idempotency_key: str
    status: ApprovalStatus = ApprovalStatus.APPROVAL_REQUIRED
    decided_by: str | None = None
    decided_at: datetime | None = None
    result_summary: ToolCallSummary | None = None
    revision: int = Field(default=0, ge=0)


class MemoryConsent(AgenticModel):
    tenant_id: str
    user_id: str
    enabled: bool = False
    consent_version: str | None = None
    consented_at: datetime | None = None
    revoked_at: datetime | None = None


class LongTermMemory(AgenticModel):
    memory_id: str
    tenant_id: str
    user_id: str
    content: str = Field(min_length=1, max_length=2_000)
    source: str
    consent_version: str
    consented_at: datetime
    created_at: datetime
    expires_at: datetime
    deleted_at: datetime | None = None


class AgenticState(AgenticModel):
    """Versioned LangGraph state containing only bounded, checkpoint-safe data."""

    VERSION: ClassVar[int] = 1
    version: Literal[1] = 1
    run_id: str
    thread_id: str
    request_id: str
    authorization: AgenticAuthorizationSnapshot
    question: str
    route: Literal["direct_rag", "agent"] = "agent"
    plan: QueryPlan | None = None
    current_step: int = Field(default=0, ge=0)
    iteration: int = Field(default=0, ge=0)
    evidence: tuple[EvidenceItem, ...] = ()
    citations: tuple[AgentEvidenceCitation, ...] = ()
    retrieval_trace_ids: tuple[str, ...] = ()
    model_provider_ids: tuple[str, ...] = ()
    tool_calls: tuple[ToolCallSummary, ...] = ()
    pending_tool_invocation: ToolInvocation | None = None
    approval_id: str | None = None
    hitl_status: ApprovalStatus | None = None
    memory_consent: bool = False
    budget_limits: BudgetLimits = Field(default_factory=BudgetLimits)
    budget_usage: BudgetUsage = Field(default_factory=BudgetUsage)
    final_status: AgenticRunStatus | None = None
    final_answer: str | None = None
    stop_reason: str | None = None


class AgentRunTrace(AgenticModel):
    """Content-minimized Agent trace persisted separately from checkpoints."""

    run_id: str
    thread_id: str
    request_id: str
    tenant_id: str
    user_id: str
    status: AgenticRunStatus | None
    retrieval_trace_ids: tuple[str, ...]
    model_provider_ids: tuple[str, ...]
    tool_calls: tuple[ToolCallSummary, ...]
    budget_limits: BudgetLimits
    budget_usage: BudgetUsage
    stop_reason: str | None
    started_at: datetime
    updated_at: datetime


class AgenticRunRequest(AgenticModel):
    run_id: str
    thread_id: str
    context: AgenticAuthorizationSnapshot
    question: str = Field(min_length=1, max_length=8_000)
    budget_limits: BudgetLimits = Field(default_factory=BudgetLimits)
    model_provider_ids: tuple[str, ...] = ()


class AgenticResumeRequest(AgenticModel):
    run_id: str
    thread_id: str
    approval_id: str
    tenant_id: str
    approver_id: str
    approver_request_id: str
    approver_roles: tuple[str, ...]
    decision: Literal["approve", "reject", "cancel"]


class AgenticRunResult(AgenticModel):
    state: AgenticState
    interrupted: bool = False
