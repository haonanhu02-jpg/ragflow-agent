"""Bounded-label Prometheus metrics for API, jobs, RAG, Agent, and operations."""

from time import perf_counter

from prometheus_client import Counter, Gauge, Histogram
from starlette.types import ASGIApp, Message, Receive, Scope, Send

HTTP_REQUESTS = Counter(
    "ragflow_agent_http_requests_total",
    "HTTP requests by route class and status",
    ("method", "route", "status"),
)
HTTP_DURATION = Histogram(
    "ragflow_agent_http_request_duration_seconds",
    "HTTP request duration",
    ("method", "route"),
)
DEPENDENCY_FAILURES = Counter(
    "ragflow_agent_dependency_failures_total",
    "Dependency failures that did not become no-evidence",
    ("component",),
)
WORK_BACKLOG = Gauge(
    "ragflow_agent_work_backlog_seconds",
    "Age of oldest pending outbox, DLQ, cleanup, or memory item",
    ("queue",),
)
OPERATION_DURATION = Histogram(
    "ragflow_agent_operation_duration_seconds",
    "Duration of bounded internal operation classes",
    ("component", "outcome"),
)
OPERATION_TOTAL = Counter(
    "ragflow_agent_operations_total",
    "Bounded internal operations by component and outcome",
    ("component", "outcome"),
)


def _route_label(scope: Scope) -> str:
    route = scope.get("route")
    path = getattr(route, "path", None)
    return str(path) if path else "unmatched"


class MetricsMiddleware:
    """Record bounded HTTP latency/status labels without tenant or user cardinality."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        started = perf_counter()
        status = 500

        async def observe(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = int(message["status"])
            await send(message)

        app = scope.get("app")
        provider = getattr(getattr(app, "state", None), "tracer_provider", None)
        tracer = provider.get_tracer("ragflow_agent.api") if provider is not None else None
        from ragflow_agent.observability.instrumentation import observe_operation

        try:
            with observe_operation("api", tracer=tracer):
                await self._app(scope, receive, observe)
        finally:
            method = str(scope.get("method", "UNKNOWN"))
            route = _route_label(scope)
            HTTP_REQUESTS.labels(method, route, str(status)).inc()
            HTTP_DURATION.labels(method, route).observe(perf_counter() - started)
