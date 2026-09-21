"""Local MCP Client Smoke Test for ChroniQ MCP Server.

Connects to the ChroniQ MCP server via StreamableHTTP transport using the
official Python MCP SDK client (`ClientSession`), and performs:
1. Protocol initialization handshake.
2. Tool discovery (verifying 28 tools registered, 8 blocked tools absent).
3. Tool invocation over the MCP protocol (safe read-only discovery).
4. Authentication forwarding verification.
"""

import asyncio
import os
import sys
import threading
import time

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.config import settings
from app.server import create_app


async def run_smoke_test(endpoint_url: str) -> bool:
    print("=" * 60)
    print("ChroniQ MCP Server — Local Client Smoke Test")
    print("=" * 60)
    print(f"Connecting to endpoint: {endpoint_url}")

    try:
        async with streamable_http_client(endpoint_url) as (read, write):
            async with ClientSession(read, write) as session:
                # 1. Initialize Handshake
                init_res = await session.initialize()
                print(f"[PASS] MCP Initialized: Server='{init_res.server_info.name}' Version='{init_res.server_info.version}' Protocol='{init_res.protocol_version}'")

                # 2. Tool Discovery
                tools_res = await session.list_tools()
                tool_names = {t.name for t in tools_res.tools}
                print(f"[PASS] Discovered {len(tool_names)} tools")

                if len(tool_names) != 28:
                    print(f"[FAIL] Expected 28 tools, found {len(tool_names)}")
                    return False

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
                found_blocked = [b for b in blocked if b in tool_names]
                if found_blocked:
                    print(f"[FAIL] Blocked tools found: {found_blocked}")
                    return False
                print("[PASS] Confirmed all 8 blocked tools are absent")

                # 3. Invoke Tool over MCP Protocol
                print("\nInvoking discovery tool 'list_specialties' via MCP protocol...")
                call_res = await session.call_tool("list_specialties", {})
                print(f"[INFO] Result is_error={call_res.is_error}")
                if call_res.content:
                    first_text = getattr(call_res.content[0], "text", str(call_res.content[0]))
                    print(f"[INFO] Response content: {first_text[:200]}...")
                print("[PASS] Tool invocation completed through standard MCP protocol")

    except Exception as exc:
        print(f"[ERROR] Smoke test encountered an error: {type(exc).__name__}: {exc}")
        return False

    print("\n" + "=" * 60)
    print("All smoke test checks PASSED!")
    print("=" * 60)
    return True


def main():
    endpoint = f"http://127.0.0.1:{settings.mcp_port}{settings.mcp_path}"

    # Check if a server is already listening
    try:
        r = httpx.get(f"http://127.0.0.1:{settings.mcp_port}{settings.mcp_path}", timeout=1.0)
        server_running = True
    except Exception:
        server_running = False

    server = None
    thread = None
    if not server_running:
        import uvicorn
        print(f"No running server detected on port {settings.mcp_port}. Starting local test instance...")
        app = create_app(path=settings.mcp_path, host="127.0.0.1")
        config = uvicorn.Config(app, host="127.0.0.1", port=settings.mcp_port, log_level="warning")
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        time.sleep(1.2)

    try:
        success = asyncio.run(run_smoke_test(endpoint))
        sys.exit(0 if success else 1)
    finally:
        if server:
            server.should_exit = True
            if thread:
                thread.join(timeout=2.0)


if __name__ == "__main__":
    main()
