"""Single Phase 06 online retrieval pipeline shared by fixed RAG and Agent Tool."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from time import perf_counter

from pydantic import Field, model_validator

from ragflow_agent.knowledge.application.query.clean import CleanResult, clean_candidates
from ragflow_agent.knowledge.application.query.fallback import RetrievalAttempt, fallback_attempts
from ragflow_agent.knowledge.application.query.filters import filter_summary
from ragflow_agent.knowledge.application.query.fusion import reciprocal_rank_fusion
from ragflow_agent.knowledge.application.query.preprocess import QueryPreprocessor
from ragflow_agent.knowledge.application.query.rerank import rerank_with_fallback
from ragflow_agent.knowledge.application.query.trace import SafeRetrievalTraceRecorder
from ragflow_agent.knowledge.application.query.transforms import QueryVariantBuilder
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.errors import (
    KnowledgeAuthorizationError,
    KnowledgeRetrievalError,
)
from ragflow_agent.knowledge.domain.retrieval import (
    QueryVariant,
    QueryVariantKind,
    RetrievalCandidate,
    RetrievalCandidateTrace,
    RetrievalEmptyReason,
    RetrievalFallbackStep,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStage,
    RetrievalTrace,
    RetrievalTraceEvent,
    RetrievalTraceStatus,
    TraceAttribute,
)
from ragflow_agent.knowledge.ports.search import RerankerPort, SearchChannelPort
from ragflow_agent.shared.ports.time import Clock


class OnlineRetrievalProfile(KnowledgeModel):
    """Frozen algorithm, budget, and retention profile for one deployment."""

    config_version: NonEmptyStr = "retrieval-v2"
    rrf_k: int = Field(default=60, ge=1)
    candidate_top_k: int = Field(default=100, ge=1, le=10_000)
    rerank_candidate_count: int = Field(default=30, ge=1)
    final_top_k: int = Field(default=10, ge=1)
    fusion_threshold: float = Field(default=0, ge=0)
    fallback_threshold_floor: float = Field(default=0, ge=0)
    max_fallback_attempts: int = Field(default=4, ge=0, le=4)
    fallback_candidate_multiplier: int = Field(default=2, ge=1, le=10)
    per_document_limit: int = Field(default=4, ge=1)
    reranker_timeout_seconds: float = Field(default=5, gt=0)
    trace_retention_days: int = Field(default=30, ge=1)
    provider_ids: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_windows(self) -> OnlineRetrievalProfile:
        if self.final_top_k > self.rerank_candidate_count:
            raise ValueError("final_top_k cannot exceed rerank candidate count")
        if self.rerank_candidate_count > self.candidate_top_k:
            raise ValueError("rerank candidate count cannot exceed candidate top_k")
        if self.fallback_threshold_floor > self.fusion_threshold:
            raise ValueError("fallback threshold floor cannot exceed normal threshold")
        return self


@dataclass(frozen=True, slots=True)
class _AttemptOutcome:
    selected: tuple[RetrievalCandidate, ...]
    fused: tuple[RetrievalCandidate, ...]
    reranked: tuple[RetrievalCandidate, ...]
    clean: CleanResult
    text_count: int
    vector_count: int
    errors: tuple[str, ...]
    reranker_applied: bool
    reranker_fallback: str | None
    elapsed_ms: float


class OnlineRetrievalService:
    """Permission-preserving transform → retrieve → fuse → rerank → fallback flow."""

    def __init__(
        self,
        *,
        search: SearchChannelPort,
        reranker: RerankerPort,
        variants: QueryVariantBuilder,
        preprocessor: QueryPreprocessor,
        trace_recorder: SafeRetrievalTraceRecorder,
        clock: Clock,
        profile: OnlineRetrievalProfile,
    ) -> None:
        self._search = search
        self._reranker = reranker
        self._variants = variants
        self._preprocessor = preprocessor
        self._trace_recorder = trace_recorder
        self._clock = clock
        self._profile = profile

    async def retrieve(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
    ) -> RetrievalResult:
        if context.tenant_id != query.tenant_id:
            raise KnowledgeAuthorizationError(
                reason_code="tenant_mismatch",
                trace_id=context.request_id,
            )
        started_at = self._clock.now()
        started = perf_counter()
        processed = self._preprocessor.process(query.text)
        transformed = await self._variants.build(
            context,
            processed=processed,
            history=query.history,
            target_languages=query.target_languages,
            trace_id=query.trace_id,
        )
        effective_query = query.model_copy(
            update={
                "text": processed.canonical_text,
                "top_k": min(query.top_k, self._profile.candidate_top_k),
                "top_n": min(query.top_n, self._profile.final_top_k),
                "request_id": query.request_id or context.request_id,
            }
        )
        events = [
            RetrievalTraceEvent(
                sequence=0,
                stage=RetrievalStage.AUTHORIZATION,
                elapsed_ms=0,
                candidate_count=0,
                attributes=(
                    TraceAttribute(name="tenant_filter", value=True),
                    TraceAttribute(name="acl_filter", value=True),
                    TraceAttribute(name="scope_filter", value=True),
                    TraceAttribute(name="document_state_filter", value=True),
                ),
            ),
            RetrievalTraceEvent(
                sequence=1,
                stage=RetrievalStage.PREPROCESS,
                elapsed_ms=(perf_counter() - started) * 1000,
                candidate_count=len(transformed.variants),
                attributes=(
                    TraceAttribute(name="language", value=processed.language),
                    TraceAttribute(name="transform_version", value=processed.transform_version),
                ),
            ),
        ]
        if transformed.failures:
            events.append(
                RetrievalTraceEvent(
                    sequence=len(events),
                    stage=RetrievalStage.REWRITE,
                    elapsed_ms=(perf_counter() - started) * 1000,
                    candidate_count=len(transformed.variants),
                    attributes=(
                        TraceAttribute(
                            name="provider_fallbacks",
                            value=len(transformed.failures),
                        ),
                    ),
                )
            )
        stage_by_kind = {
            QueryVariantKind.REWRITE: RetrievalStage.REWRITE,
            QueryVariantKind.TRANSLATION: RetrievalStage.TRANSLATE,
            QueryVariantKind.KEYWORD: RetrievalStage.EXPAND,
        }
        for kind, stage in stage_by_kind.items():
            kind_variants = tuple(item for item in transformed.variants if item.kind == kind)
            if kind_variants:
                events.append(
                    RetrievalTraceEvent(
                        sequence=len(events),
                        stage=stage,
                        elapsed_ms=(perf_counter() - started) * 1000,
                        candidate_count=len(kind_variants),
                        attributes=(
                            TraceAttribute(
                                name="provider_backed",
                                value=sum(item.provider is not None for item in kind_variants),
                            ),
                        ),
                    )
                )
        attempts = (
            RetrievalAttempt(
                number=0,
                mode="hybrid",
                query=effective_query,
                threshold=self._profile.fusion_threshold,
                inferred_filter_removed=False,
            ),
            *fallback_attempts(
                effective_query,
                normal_threshold=self._profile.fusion_threshold,
                threshold_floor=self._profile.fallback_threshold_floor,
                candidate_multiplier=self._profile.fallback_candidate_multiplier,
                maximum_attempts=self._profile.max_fallback_attempts,
            ),
        )
        fallback_trace: list[RetrievalFallbackStep] = []
        last: _AttemptOutcome | None = None
        for attempt in attempts:
            outcome = await self._run_attempt(
                context,
                attempt=attempt,
                variants=transformed.variants,
            )
            last = outcome
            events.extend(self._attempt_events(events, attempt, outcome))
            if attempt.number > 0:
                fallback_trace.append(
                    RetrievalFallbackStep(
                        attempt=attempt.number,
                        mode=attempt.mode,
                        reason=(
                            "recovered_evidence"
                            if outcome.selected
                            else "no_candidates_after_selection"
                        ),
                        candidate_top_k=attempt.query.top_k,
                        threshold=attempt.threshold,
                        inferred_filter_removed=attempt.inferred_filter_removed,
                        result_count=len(outcome.selected),
                    )
                )
            if outcome.selected:
                trace = self._build_trace(
                    context=context,
                    original_query=query,
                    effective_query=effective_query,
                    canonical=processed.canonical_text,
                    query_variants=transformed.variants,
                    events=events,
                    candidates=outcome,
                    fallbacks=fallback_trace,
                    started_at=started_at,
                    status=RetrievalTraceStatus.SUCCESS,
                )
                await self._trace_recorder.record(trace)
                return RetrievalResult(
                    query=query,
                    candidates=outcome.selected,
                    trace=trace,
                )
            if outcome.errors:
                trace = self._build_trace(
                    context=context,
                    original_query=query,
                    effective_query=effective_query,
                    canonical=processed.canonical_text,
                    query_variants=transformed.variants,
                    events=events,
                    candidates=outcome,
                    fallbacks=fallback_trace,
                    started_at=started_at,
                    status=RetrievalTraceStatus.FAILED,
                    error_code="retrieval_dependency_failed",
                )
                await self._trace_recorder.record(trace)
                raise KnowledgeRetrievalError(
                    trace_id=query.trace_id,
                    details={"failed_components": list(outcome.errors)},
                )
        assert last is not None
        trace = self._build_trace(
            context=context,
            original_query=query,
            effective_query=effective_query,
            canonical=processed.canonical_text,
            query_variants=transformed.variants,
            events=events,
            candidates=last,
            fallbacks=fallback_trace,
            started_at=started_at,
            status=RetrievalTraceStatus.NO_EVIDENCE,
        )
        await self._trace_recorder.record(trace)
        return RetrievalResult(
            query=query,
            candidates=(),
            trace=trace,
            empty_reason=RetrievalEmptyReason.NO_EVIDENCE,
        )

    async def _run_attempt(
        self,
        context: AuthorizationContext,
        *,
        attempt: RetrievalAttempt,
        variants: tuple[QueryVariant, ...],
    ) -> _AttemptOutcome:
        started = perf_counter()
        text: tuple[RetrievalCandidate, ...] = ()
        vector: tuple[RetrievalCandidate, ...] = ()
        errors: list[str] = []
        if attempt.mode != "vector_only":
            try:
                text = await self._collect_channel(
                    context,
                    attempt.query,
                    variants,
                    channel="full_text",
                )
            except Exception as error:
                errors.append(f"full_text:{type(error).__name__}")
        if attempt.mode != "full_text_only":
            try:
                vector = await self._collect_channel(
                    context,
                    attempt.query,
                    variants,
                    channel="vector",
                )
            except Exception as error:
                errors.append(f"vector:{type(error).__name__}")
        expected_channels = 1 if attempt.mode in {"full_text_only", "vector_only"} else 2
        if len(errors) == expected_channels:
            return _AttemptOutcome(
                selected=(),
                fused=(),
                reranked=(),
                clean=CleanResult(candidates=(), excluded=()),
                text_count=0,
                vector_count=0,
                errors=tuple(errors),
                reranker_applied=False,
                reranker_fallback=None,
                elapsed_ms=(perf_counter() - started) * 1000,
            )
        fused = reciprocal_rank_fusion(text, vector, k=self._profile.rrf_k)
        rerank_window = fused[: min(len(fused), self._profile.rerank_candidate_count)]
        rerank = await rerank_with_fallback(
            self._reranker,
            context,
            attempt.query,
            rerank_window,
            timeout_seconds=self._profile.reranker_timeout_seconds,
        )
        clean = clean_candidates(
            rerank.candidates,
            threshold=attempt.threshold,
            per_document_limit=self._profile.per_document_limit,
            final_top_k=attempt.query.top_n,
        )
        return _AttemptOutcome(
            selected=clean.candidates,
            fused=fused,
            reranked=rerank.candidates,
            clean=clean,
            text_count=len(text),
            vector_count=len(vector),
            errors=tuple(errors),
            reranker_applied=rerank.applied,
            reranker_fallback=rerank.fallback_reason,
            elapsed_ms=(perf_counter() - started) * 1000,
        )

    async def _collect_channel(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
        variants: tuple[QueryVariant, ...],
        *,
        channel: str,
    ) -> tuple[RetrievalCandidate, ...]:
        merged: dict[str, RetrievalCandidate] = {}
        for variant in variants:
            variant_query = query.model_copy(update={"text": variant.text})
            if channel == "full_text":
                candidates = await self._search.retrieve_full_text(context, variant_query)
            else:
                candidates = await self._search.retrieve_vector(context, variant_query)
            for candidate in candidates:
                existing = merged.get(candidate.chunk_id)
                is_better = existing is None or self._channel_score(
                    candidate, channel
                ) > self._channel_score(existing, channel)
                if is_better:
                    merged[candidate.chunk_id] = candidate
        return tuple(
            sorted(
                merged.values(),
                key=lambda item: (-self._channel_score(item, channel), item.chunk_id),
            )[: query.top_k]
        )

    @staticmethod
    def _channel_score(candidate: RetrievalCandidate, channel: str) -> float:
        if channel == "full_text":
            return candidate.score.full_text_score or 0.0
        return candidate.score.vector_score or 0.0

    def _attempt_events(
        self,
        existing: list[RetrievalTraceEvent],
        attempt: RetrievalAttempt,
        outcome: _AttemptOutcome,
    ) -> list[RetrievalTraceEvent]:
        base = len(existing)
        common = (
            TraceAttribute(name="attempt", value=attempt.number),
            TraceAttribute(name="mode", value=attempt.mode),
        )
        events = [
            RetrievalTraceEvent(
                sequence=base,
                stage=RetrievalStage.FULL_TEXT,
                elapsed_ms=outcome.elapsed_ms,
                candidate_count=outcome.text_count,
                attributes=common,
            ),
            RetrievalTraceEvent(
                sequence=base + 1,
                stage=RetrievalStage.VECTOR,
                elapsed_ms=outcome.elapsed_ms,
                candidate_count=outcome.vector_count,
                attributes=common,
            ),
            RetrievalTraceEvent(
                sequence=base + 2,
                stage=RetrievalStage.FUSION,
                elapsed_ms=outcome.elapsed_ms,
                candidate_count=len(outcome.fused),
                attributes=(
                    *common,
                    TraceAttribute(name="rrf_k", value=self._profile.rrf_k),
                ),
            ),
            RetrievalTraceEvent(
                sequence=base + 3,
                stage=RetrievalStage.RERANK,
                elapsed_ms=outcome.elapsed_ms,
                candidate_count=len(outcome.clean.candidates),
                attributes=(
                    *common,
                    TraceAttribute(name="applied", value=outcome.reranker_applied),
                    TraceAttribute(
                        name="fallback",
                        value=outcome.reranker_fallback or "none",
                    ),
                ),
            ),
            RetrievalTraceEvent(
                sequence=base + 4,
                stage=(RetrievalStage.SELECT if outcome.selected else RetrievalStage.FALLBACK),
                elapsed_ms=outcome.elapsed_ms,
                candidate_count=len(outcome.selected),
                attributes=(
                    *common,
                    TraceAttribute(name="threshold", value=attempt.threshold),
                    TraceAttribute(
                        name="inferred_filter_removed",
                        value=attempt.inferred_filter_removed,
                    ),
                    TraceAttribute(name="component_errors", value=len(outcome.errors)),
                ),
            ),
        ]
        return events

    def _build_trace(
        self,
        *,
        context: AuthorizationContext,
        original_query: RetrievalQuery,
        effective_query: RetrievalQuery,
        canonical: str,
        query_variants: tuple[QueryVariant, ...],
        events: list[RetrievalTraceEvent],
        candidates: _AttemptOutcome,
        fallbacks: list[RetrievalFallbackStep],
        started_at: datetime,
        status: RetrievalTraceStatus,
        error_code: str | None = None,
    ) -> RetrievalTrace:
        completed_at = self._clock.now()
        selected_ids = {candidate.chunk_id for candidate in candidates.selected}
        selected = {candidate.chunk_id: candidate for candidate in candidates.selected}
        excluded = {item.chunk_id: reason for item, reason in candidates.clean.excluded}
        reranked = {item.chunk_id: item for item in candidates.reranked}
        candidate_traces = tuple(
            RetrievalCandidateTrace(
                knowledge_base_id=ranked.knowledge_base_id,
                document_id=ranked.document_id,
                document_version_id=ranked.document_version_id,
                chunk_id=ranked.chunk_id,
                full_text_rank=ranked.score.full_text_rank,
                full_text_score=ranked.score.full_text_score,
                vector_rank=ranked.score.vector_rank,
                vector_score=ranked.score.vector_score,
                fusion_rank=ranked.score.fusion_rank,
                fusion_score=ranked.score.fusion_score,
                rerank_rank=ranked.score.rerank_rank,
                rerank_score=ranked.score.rerank_score,
                final_rank=(selected_item.score.final_rank if selected_item is not None else None),
                selected=item.chunk_id in selected_ids,
                exclusion_reason=excluded.get(item.chunk_id),
            )
            for item in candidates.fused
            for ranked in (reranked.get(item.chunk_id, item),)
            for selected_item in (selected.get(item.chunk_id),)
        )
        return RetrievalTrace(
            trace_id=original_query.trace_id,
            request_id=effective_query.request_id,
            tenant_id=context.tenant_id,
            original_query=original_query.text,
            canonical_query=canonical,
            rewritten_queries=(),
            query_variant_digests=tuple(
                f"{variant.kind.value}:{sha256(variant.text.encode('utf-8')).hexdigest()}"
                for variant in query_variants
            ),
            authorization_applied=True,
            events=tuple(events),
            knowledge_base_ids=original_query.knowledge_base_ids,
            index_version_ids=original_query.index_version_ids,
            config_version=self._profile.config_version,
            provider_ids=self._profile.provider_ids,
            filter_summary=filter_summary(original_query),
            candidates=candidate_traces,
            fallback_steps=tuple(fallbacks),
            status=status,
            error_code=error_code,
            started_at=started_at,
            completed_at=completed_at,
            expires_at=completed_at + timedelta(days=self._profile.trace_retention_days),
        )
