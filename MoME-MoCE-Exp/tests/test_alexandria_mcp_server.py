from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

from jsonschema import validate

from alexandria_harness.engine_client import DogfoodHooksObjectClient
from scripts.alexandria_mcp_server import (
    MCP_CONTRACT_VERSION,
    TOOL_OUTPUT_SCHEMA_VERSION,
    AlexandriaMcpBridge,
    AuditLogger,
    AuthConfig,
    OAuthProvider,
    make_handler,
    sha256_b64url,
)
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
        assert init["result"]["serverInfo"]["contractVersion"] == MCP_CONTRACT_VERSION

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
        imported_content = imported["result"]["structuredContent"]
        assert imported_content["schema_version"] == TOOL_OUTPUT_SCHEMA_VERSION
        assert imported_content["contract_version"] == MCP_CONTRACT_VERSION
        assert imported_content["ingested"] == 1
        assert mirrored_content(imported) == imported_content

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
        assert mirrored_content(packet) == content
        assert content["selected_ids"]
        assert content["model_visible_packet"]["evidence"]
    finally:
        stop_server(server)


def test_mcp_tools_list_has_non_destructive_versioned_contracts(tmp_path) -> None:
    server, base_url = start_mcp(tmp_path)
    try:
        response = rpc(f"{base_url}/mcp", "tools/list", {}, token="test-token")
        tools = response["result"]["tools"]
        names = {tool["name"] for tool in tools}
        assert "alexandria_forget" not in names
        assert "forget" not in names

        for tool in tools:
            assert tool["annotations"]["destructiveHint"] is False
            assert "outputSchema" in tool
            output_schema = tool["outputSchema"]
            assert output_schema["type"] == "object"
            assert "schema_version" in output_schema["required"]
            assert "contract_version" in output_schema["required"]
            assert output_schema["properties"]["schema_version"]["const"] == TOOL_OUTPUT_SCHEMA_VERSION
            assert output_schema["properties"]["contract_version"]["const"] == MCP_CONTRACT_VERSION
            assert output_schema["properties"]["tool"]["const"] == tool["name"]

        import_tool = next(tool for tool in tools if tool["name"] == "alexandria_import_memories")
        assert "Do not import raw transcript dumps" in import_tool["description"]
        item_description = import_tool["inputSchema"]["properties"]["items"]["description"]
        assert "One memory candidate per array item" in item_description
    finally:
        stop_server(server)


def test_mcp_tool_output_validates_against_declared_schema(tmp_path) -> None:
    server, base_url = start_mcp(tmp_path)
    try:
        tools = rpc(f"{base_url}/mcp", "tools/list", {}, token="test-token")["result"]["tools"]
        schemas = {tool["name"]: tool["outputSchema"] for tool in tools}

        status = rpc(
            f"{base_url}/mcp",
            "tools/call",
            {"name": "alexandria_status", "arguments": {}},
            token="test-token",
        )
        content = status["result"]["structuredContent"]
        assert mirrored_content(status) == content
        validate(instance=content, schema=schemas["alexandria_status"])
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


def test_oauth_metadata_and_tool_challenge(tmp_path) -> None:
    server, base_url = start_mcp(tmp_path, oauth=True)
    try:
        protected = http_get_json(f"{base_url}/.well-known/oauth-protected-resource")
        assert protected["authorization_servers"] == [base_url]
        assert "alexandria.read" in protected["scopes_supported"]

        auth_metadata = http_get_json(f"{base_url}/.well-known/oauth-authorization-server")
        assert auth_metadata["issuer"] == base_url
        assert auth_metadata["authorization_endpoint"] == f"{base_url}/oauth/authorize"
        assert auth_metadata["token_endpoint"] == f"{base_url}/oauth/token"
        assert auth_metadata["registration_endpoint"] == f"{base_url}/oauth/register"
        assert "S256" in auth_metadata["code_challenge_methods_supported"]

        tools = rpc(f"{base_url}/mcp/chatgpt-secret", "tools/list", {})
        status_tool = next(tool for tool in tools["result"]["tools"] if tool["name"] == "alexandria_status")
        assert status_tool["securitySchemes"] == [{"type": "oauth2", "scopes": ["alexandria.read"]}]
        assert status_tool["_meta"]["securitySchemes"] == status_tool["securitySchemes"]

        challenged = rpc(
            f"{base_url}/mcp/chatgpt-secret",
            "tools/call",
            {"name": "alexandria_status", "arguments": {}},
        )
        assert challenged["result"]["isError"] is True
        assert challenged["result"]["structuredContent"]["error"] == "authentication_required"
        assert "mcp/www_authenticate" in challenged["result"]["_meta"]

        local_bearer = rpc(
            f"{base_url}/mcp",
            "tools/call",
            {"name": "alexandria_status", "arguments": {}},
            token="test-token",
        )
        assert local_bearer["result"]["isError"] is False
    finally:
        stop_server(server)


def test_oauth_authorization_code_pkce_flow_allows_tool_call(tmp_path) -> None:
    server, base_url = start_mcp(tmp_path, oauth=True)
    try:
        client = http_post_json(
            f"{base_url}/oauth/register",
            {
                "client_name": "ChatGPT Alexandria test",
                "redirect_uris": ["https://chatgpt.com/connector/oauth/test-callback"],
            },
            expected_status=201,
        )
        verifier = "test-verifier-for-pkce"
        location = http_post_form_no_redirect(
            f"{base_url}/oauth/authorize",
            {
                "pin": "123456",
                "response_type": "code",
                "client_id": client["client_id"],
                "redirect_uri": "https://chatgpt.com/connector/oauth/test-callback",
                "state": "abc",
                "scope": "alexandria.read",
                "resource": base_url,
                "code_challenge": sha256_b64url(verifier),
                "code_challenge_method": "S256",
            },
        )
        parsed = urllib.parse.urlparse(location)
        query = urllib.parse.parse_qs(parsed.query)
        assert query["state"] == ["abc"]

        token = http_post_form(
            f"{base_url}/oauth/token",
            {
                "grant_type": "authorization_code",
                "code": query["code"][0],
                "client_id": client["client_id"],
                "redirect_uri": "https://chatgpt.com/connector/oauth/test-callback",
                "code_verifier": verifier,
            },
        )
        assert token["token_type"] == "Bearer"
        assert token["scope"] == "alexandria.read"

        status = rpc(
            f"{base_url}/mcp/chatgpt-secret",
            "tools/call",
            {"name": "alexandria_status", "arguments": {}},
            token=token["access_token"],
        )
        assert status["result"]["isError"] is False
        assert status["result"]["structuredContent"]["tool"] == "alexandria_status"
    finally:
        stop_server(server)


def test_oauth_missing_scope_is_read_only_and_unknown_scope_is_rejected(tmp_path) -> None:
    server, base_url = start_mcp(tmp_path, oauth=True)
    try:
        client = http_post_json(
            f"{base_url}/oauth/register",
            {
                "client_name": "ChatGPT Alexandria test",
                "redirect_uris": ["https://chatgpt.com/connector/oauth/test-callback"],
            },
            expected_status=201,
        )
        verifier = "test-verifier-for-default-scope"
        location = http_post_form_no_redirect(
            f"{base_url}/oauth/authorize",
            {
                "pin": "123456",
                "response_type": "code",
                "client_id": client["client_id"],
                "redirect_uri": "https://chatgpt.com/connector/oauth/test-callback",
                "state": "default-scope",
                "resource": base_url,
                "code_challenge": sha256_b64url(verifier),
                "code_challenge_method": "S256",
            },
        )
        query = urllib.parse.parse_qs(urllib.parse.urlparse(location).query)
        token = http_post_form(
            f"{base_url}/oauth/token",
            {
                "grant_type": "authorization_code",
                "code": query["code"][0],
                "client_id": client["client_id"],
                "redirect_uri": "https://chatgpt.com/connector/oauth/test-callback",
                "code_verifier": verifier,
            },
        )
        assert token["scope"] == "alexandria.read"

        write_call = rpc(
            f"{base_url}/mcp/chatgpt-secret",
            "tools/call",
            {"name": "alexandria_import_memories", "arguments": {}},
            token=token["access_token"],
        )
        assert write_call["result"]["isError"] is True
        assert write_call["result"]["structuredContent"]["required_scopes"] == ["alexandria.write"]

        error = http_post_form_error(
            f"{base_url}/oauth/authorize",
            {
                "pin": "123456",
                "response_type": "code",
                "client_id": client["client_id"],
                "redirect_uri": "https://chatgpt.com/connector/oauth/test-callback",
                "scope": "alexandria.admin",
                "resource": base_url,
                "code_challenge": sha256_b64url("unknown-scope-verifier"),
                "code_challenge_method": "S256",
            },
        )
        assert error["error"] == "invalid_request"
        assert "unsupported OAuth scope" in error["error_description"]
    finally:
        stop_server(server)


def start_mcp(tmp_path, audit_path=None, *, oauth: bool = False):
    hooks = DogfoodHooks(tmp_path / "dogfood")
    client = DogfoodHooksObjectClient(hooks)
    audit = AuditLogger(audit_path)
    oauth_provider = OAuthProvider(enabled=oauth, require_for_tools=oauth, owner_pin="123456")
    bridge = AlexandriaMcpBridge(client, audit, oauth_provider)
    auth = AuthConfig(bearer_tokens=("test-token",), path_secrets=("chatgpt-secret",), oauth=oauth_provider)
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


def http_get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def http_post_json(url: str, payload: dict, *, expected_status: int = 200) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        assert response.status == expected_status
        return json.loads(response.read().decode("utf-8"))


def http_post_form(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(payload).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def http_post_form_no_redirect(url: str, payload: dict) -> str:
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(payload).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        opener.open(request, timeout=5)
    except urllib.error.HTTPError as exc:
        assert exc.code == 302
        return exc.headers["Location"]
    raise AssertionError("OAuth authorize did not redirect")


def http_post_form_error(url: str, payload: dict, *, expected_status: int = 400) -> dict:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(payload).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=5)
    except urllib.error.HTTPError as exc:
        assert exc.code == expected_status
        return json.loads(exc.read().decode("utf-8"))
    raise AssertionError("OAuth authorize unexpectedly succeeded")


def mirrored_content(response: dict) -> dict:
    content = response["result"]["content"]
    assert len(content) == 1
    assert content[0]["type"] == "text"
    return json.loads(content[0]["text"])
