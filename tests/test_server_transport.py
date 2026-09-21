"""Tests for MCP HTTP server startup, transport, and protocol handshake.

Verifies:
- Starlette app mounting and route paths
- MCP initialization handshake and protocol version
- Tool discovery (28 tools registered, 8 blocked tools absent)
- Tool invocation over StreamableHTTP transport
- Authorization header forwarding and multi-client isolation
- Safe error handling over MCP protocol
"""

import asyncio
import socket
import threading
import time

import httpx
import pytest
import respx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.server import create_app, mcp


def get_free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def http_server():
    """Start an in-process uvicorn server running StreamableHTTP."""
    import uvicorn

    port = get_free_port()
    app = create_app(path="/mcp", host="127.0.0.1")
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="error",
        access_log=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server to accept connections
    deadline = time.time() + 5.0
    while time.time() < deadline:
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=0.5)
            s.close()
            break
        except (OSError, ConnectionRefusedError):
            time.sleep(0.05)

    base_url = f"http://127.0.0.1:{port}"
    endpoint = f"{base_url}/mcp"

    yield {"port": port, "base_url": base_url, "endpoint": endpoint}

    server.should_exit = True
    thread.join(timeout=3.0)


class TestServerAppStructure:
    def test_mcp_route_mounted(self):
        app = create_app(path="/mcp", host="127.0.0.1")
        routes = [r.path for r in app.routes]
        assert "/mcp" in routes

    def test_custom_path_mounted(self):
        app = create_app(path="/custom-mcp", host="127.0.0.1")
        routes = [r.path for r in app.routes]
        assert "/custom-mcp" in routes


class TestMCPProtocolHandshake:
    @pytest.mark.asyncio
    async def test_initialization_handshake(self, http_server):
        async with streamable_http_client(http_server["endpoint"]) as (read, write):
            async with ClientSession(read, write) as session:
                init = await session.initialize()
                assert init.server_info.name == "ChroniQ"
                assert init.protocol_version is not None

    @pytest.mark.asyncio
    async def test_tool_discovery_count_and_blocked(self, http_server):
        async with streamable_http_client(http_server["endpoint"]) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_res = await session.list_tools()
                tool_names = {t.name for t in tools_res.tools}

                # Exactly 28 tools
                assert len(tool_names) == 28

                # 8 blocked tools must NOT be present
                blocked = [
                    "reschedule_appointment",
                    "check_in_appointment",
                    "get_patient_queue_status",
                    "get_department_queue_board",
                    "delete_medical_document",
                    "request_account_deletion",
                    "cancel_account_deletion",
                    "export_patient_data",
                ]
                for b in blocked:
                    assert b not in tool_names

    @pytest.mark.asyncio
    async def test_invoke_discovery_tool_over_protocol(self, http_server):
        with respx.mock(assert_all_called=False) as respx_mock:
            respx_mock.route(host="127.0.0.1", port=http_server["port"]).pass_through()
            respx_mock.get("http://127.0.0.1:8000/specialties").respond(
                200, json=["Cardiology", "Dermatology", "Neurology"]
            )

            async with streamable_http_client(http_server["endpoint"]) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool("list_specialties", {})
                    assert result.is_error is False
                    assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_invoke_unknown_tool_returns_error(self, http_server):
        async with streamable_http_client(http_server["endpoint"]) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("nonexistent_tool", {})
                assert result.is_error is True


class TestAuthForwardingOverHTTP:
    @pytest.mark.asyncio
    async def test_bearer_token_forwarded_from_client(self, http_server):
        with respx.mock(assert_all_called=False) as respx_mock:
            respx_mock.route(host="127.0.0.1", port=http_server["port"]).pass_through()
            route = respx_mock.get("http://127.0.0.1:8000/appointments/me").respond(
                200, json=[{"id": "apt1", "doctor_name": "Dr. Smith"}]
            )

            custom_client = httpx.AsyncClient(
                headers={"Authorization": "Bearer patient-jwt-token-99"}
            )
            async with streamable_http_client(
                http_server["endpoint"], http_client=custom_client
            ) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool("list_my_appointments", {})
                    assert result.is_error is False
                    assert len(route.calls) == 1
                    sent_auth = route.calls[0].request.headers.get("authorization")
                    assert sent_auth == "Bearer patient-jwt-token-99"

    @pytest.mark.asyncio
    async def test_unauthenticated_request_has_no_token(self, http_server):
        with respx.mock(assert_all_called=False) as respx_mock:
            respx_mock.route(host="127.0.0.1", port=http_server["port"]).pass_through()
            route = respx_mock.get("http://127.0.0.1:8000/specialties").respond(
                200, json=["Pediatrics"]
            )

            custom_client = httpx.AsyncClient()
            async with streamable_http_client(
                http_server["endpoint"], http_client=custom_client
            ) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool("list_specialties", {})
                    assert result.is_error is False
                    assert len(route.calls) == 1
                    # In dev without CHRONIQ_AUTH_TOKEN set, no authorization header should be sent
                    assert "authorization" not in route.calls[0].request.headers

    @pytest.mark.asyncio
    async def test_concurrent_requests_patient_isolation(self, http_server):
        with respx.mock(assert_all_called=False) as respx_mock:
            respx_mock.route(host="127.0.0.1", port=http_server["port"]).pass_through()
            route_a = respx_mock.get("http://127.0.0.1:8000/appointments/me").respond(
                200, json=[{"id": "apt_a"}]
            )
            route_b = respx_mock.get("http://127.0.0.1:8000/patients/me/profile").respond(
                200, json={"full_name": "Patient B"}
            )

            async def call_client_a():
                client_a = httpx.AsyncClient(
                    headers={"Authorization": "Bearer token-patient-AAA"}
                )
                async with streamable_http_client(
                    http_server["endpoint"], http_client=client_a
                ) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        await asyncio.sleep(0.05)
                        return await session.call_tool("list_my_appointments", {})

            async def call_client_b():
                client_b = httpx.AsyncClient(
                    headers={"Authorization": "Bearer token-patient-BBB"}
                )
                async with streamable_http_client(
                    http_server["endpoint"], http_client=client_b
                ) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        return await session.call_tool("get_patient_profile", {})

            res_a, res_b = await asyncio.gather(call_client_a(), call_client_b())
            assert res_a.is_error is False
            assert res_b.is_error is False

            assert route_a.calls[0].request.headers.get("authorization") == "Bearer token-patient-AAA"
            assert route_b.calls[0].request.headers.get("authorization") == "Bearer token-patient-BBB"

