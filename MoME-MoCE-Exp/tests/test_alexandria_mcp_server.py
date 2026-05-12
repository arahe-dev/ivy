from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from alexandria_harness.engine_client import DogfoodHooksObjectClient
from scripts.alexandria_mcp_server import AlexandriaMcpBridge, AuditLogger, AuthConfig, make_handler
from scripts.d_acca_dogfood_service import DogfoodHooks


def test_mcp_requires_auth_for_plain_endpoint(tmp_path) -> None:
    server, base_url = start_mcp(tmp_path)
    try:
        request = urllib.request.Request(
            f"{base_url}/mcp",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 401
        else:
            raise AssertionError("plain MCP endpoint accepted a request without auth")
    finally:
        stop_server(server)


def test_mcp_initialize_and_tool_flow_with_bearer(tmp_path) -> None:
    server, base_url = start_mcp(tmp_path)
    try:
        init = rpc(
            f"{base_url}/mcp",
            "initialize",
            {},
            token="test-token",
        )
        assert init["result"]["serverInfo"]["name"] == "alexandria-d-acca"

        tools = rpc(f"{base_url}/mcp", "tools/list", {}, token="test-token")
        names = {tool["name"] for tool in tools["result"]["tools"]}
        assert "alexandria_import_memories" in names
        assert "alexandria_pick_memories" in names

        imported = rpc(
            f"{base_url}/mcp",
            "tools/call",
            {
                "name": "alexandria_import_memories",
                "arguments": {
                    "agent": "chatgpt",
                    "conversation_title": "Alexandria MCP smoke",
                    "items": [
                        {
                            "text": "Alexandria imports selected ChatGPT memories and exposes them through D-ACCA packets.",
                            "tags": ["alexandria", "mcp"],
                            "authority": "high",
                        }
                    ],
                },
            },
            token="test-token",
        )
        assert imported["result"]["structuredContent"]["ingested"] == 1

        packet = rpc(
            f"{base_url}/mcp",
            "tools/call",
            {
                "name": "alexandria_pick_memories",
                "arguments": {"query": "How do I import ChatGPT memories into Alexandria?", "top_k": 3},
            },
            token="test-token",
        )
        content = packet["result"]["structuredContent"]
        assert content["selected_ids"]
        assert content["model_visible_packet"]["evidence"]
    finally:
        stop_server(server)


def test_mcp_path_secret_allows_chatgpt_style_no_header_endpoint(tmp_path) -> None:
    server, base_url = start_mcp(tmp_path)
    try:
        init = rpc(f"{base_url}/mcp/chatgpt-secret", "initialize", {})
        assert init["result"]["protocolVersion"]
    finally:
        stop_server(server)


def test_mcp_audit_log_redacts_path_secret(tmp_path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    server, base_url = start_mcp(tmp_path, audit_path=audit_path)
    try:
        rpc(f"{base_url}/mcp/chatgpt-secret", "initialize", {})
        log_text = audit_path.read_text(encoding="utf-8")
        assert "chatgpt-secret" not in log_text
        assert "<path-secret>" in log_text
    finally:
        stop_server(server)


def start_mcp(tmp_path, audit_path=None):
    hooks = DogfoodHooks(tmp_path / "dogfood")
    client = DogfoodHooksObjectClient(hooks)
    audit = AuditLogger(audit_path)
    bridge = AlexandriaMcpBridge(client, audit)
    auth = AuthConfig(bearer_tokens=("test-token",), path_secrets=("chatgpt-secret",))
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(bridge, auth))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    server._test_thread = thread
    return server, f"http://127.0.0.1:{server.server_port}"


def stop_server(server) -> None:
    server.shutdown()
    server.server_close()
    server._test_thread.join(timeout=5)


def rpc(url: str, method: str, params: dict, *, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        url,
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))
