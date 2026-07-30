"""HTTP middleware shared by Phase 01 API routes."""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ragflow_agent.observability import TraceContext, use_trace_context


class TraceContextMiddleware:
    """Bind a trace context and expose its ID on every HTTP response."""

    def __init__(self, app: ASGIApp, *, service_name: str) -> None:
        self._app = app
        self._service_name = service_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        context = TraceContext.create(
            service=self._service_name,
            trace_id=headers.get("x-trace-id"),
            request_id=headers.get("x-request-id"),
        )

        async def send_with_trace(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"x-trace-id"
                ]
                response_headers.append((b"x-trace-id", context.trace_id.encode("ascii")))
                message["headers"] = response_headers
            await send(message)

        with use_trace_context(context):
            await self._app(scope, receive, send_with_trace)
