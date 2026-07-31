import pytest
from pydantic import ValidationError

from ragflow_agent.agent.domain.agentic import ToolAuthorizationContext, ToolInvocation
from ragflow_agent.agent.tools.api import AllowlistedApiTool, ApiEndpoint
from tests.fakes.agentic import FakeApiTransport, FakeSecretProvider


@pytest.mark.parametrize(
    ("base_url", "path", "method"),
    [
        ("file:///tmp", "/status", "GET"),
        ("https://api.example.test", "https://evil.test", "GET"),
        ("https://api.example.test", "/../admin", "GET"),
        ("https://api.example.test", "/status", "DELETE"),
    ],
)
def test_unregistered_origin_dynamic_path_and_method_are_rejected(
    base_url: str, path: str, method: str
) -> None:
    with pytest.raises(ValidationError):
        ApiEndpoint(tool_name="asset_api", base_url=base_url, path=path, method=method)


@pytest.mark.asyncio
async def test_api_tool_uses_only_registered_endpoint_and_server_credentials() -> None:
    transport = FakeApiTransport({"asset": "A", "secret": "do-not-copy"})
    tool = AllowlistedApiTool(
        endpoint=ApiEndpoint(
            tool_name="asset_api",
            base_url="https://api.example.test",
            path="/v1/assets",
            method="GET",
            credential_ref="asset-reader",
            sensitive_fields=("secret",),
        ),
        transport=transport,
        secrets=FakeSecretProvider({"authorization": "Bearer injected"}),
    )
    context = ToolAuthorizationContext(
        tenant_id="tenant-a", actor_id="user-a", request_id="request-a"
    )

    await tool.invoke(
        ToolInvocation(
            tool_call_id="api-1",
            tool_name="asset_api",
            tool_version="1",
            arguments={"query": {"asset_id": "A"}},
        ),
        context,
    )

    call = transport.calls[0]
    assert call["url"] == "https://api.example.test/v1/assets"
    headers = call["headers"]
    assert isinstance(headers, dict)
    assert headers["x-tenant-id"] == "tenant-a"
    assert headers["authorization"] == "Bearer injected"
