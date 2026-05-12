from __future__ import annotations

import argparse
import hmac
import json
import os
import sys
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alexandria_harness.engine_client import DogfoodHttpClient, EngineClientError


SERVER_NAME = "alexandria-d-acca"
SERVER_VERSION = "alexandria.mcp.v0.1"
MCP_PROTOCOL_VERSION = "2025-06-18"
DEFAULT_ENGINE_BASE_URL = "http://127.0.0.1:8767"
DEFAULT_DATA_ROOT = Path(r"C:\ivy-data\alexandria")
DEFAULT_AUDIT_LOG = DEFAULT_DATA_ROOT / "logs" / "mcp_audit.jsonl"
MAX_BODY_BYTES = 2_000_000
MAX_IMPORT_ITEMS = 100
MAX_TEXT_CHARS = 12_000
VALID_STRATEGIES = {"d-acca", "helper-lazy"}
VALID_SOURCE_FAMILIES = {
    "doc_memory",
    "runbook",
    "benchmark_artifact",
    "safety_policy",
    "workflow_trace",
    "debug_failure",
    "source_code",
    "distractor",
}
VALID_AUTHORITIES = {"high", "medium", "low", "decoy"}
VALID_STALENESS = {"current", "stale", "unknown", "decoy"}


class RpcError(Exception):
    def __init__(self, code: int, message: str, data: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class AuthError(Exception):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def safe_int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def coerce_strings(value: Any, *, lowercase: bool = False, limit: int = 24) -> list[str]:
    if value is None:
        raw_values: list[Any] = []
    elif isinstance(value, list):
        raw_values = value
    else:
        raw_values = [value]
    out: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        text = str(raw).strip()
        if not text:
            continue
        if lowercase:
            text = text.lower()
        if text in seen:
            continue
        seen.add(text)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def first_nonempty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def redact_path(path: str, auth: "AuthConfig") -> str:
    redacted = path
    for secret in auth.path_secrets:
        if secret:
            redacted = redacted.replace(secret, "<path-secret>")
    return redacted


@dataclass(frozen=True)
class AuthConfig:
    bearer_tokens: tuple[str, ...]
    path_secrets: tuple[str, ...]
    allow_no_auth: bool = False

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "AuthConfig":
        bearer_tokens: list[str] = []
        path_secrets: list[str] = []

        if args.secrets_file:
            path = Path(args.secrets_file)
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8-sig"))
                for key in ("mcp_bearer_token", "bearer_token"):
                    value = str(data.get(key) or "").strip()
                    if value:
                        bearer_tokens.append(value)
                for key in ("mcp_path_secret", "path_secret"):
                    value = str(data.get(key) or "").strip().strip("/")
                    if value:
                        path_secrets.append(value)

        if args.bearer_token:
            bearer_tokens.append(args.bearer_token.strip())
        if args.bearer_token_env:
            env_value = str(os.environ.get(args.bearer_token_env, "")).strip()
            if env_value:
                bearer_tokens.append(env_value)
        if args.path_secret:
            path_secrets.append(args.path_secret.strip().strip("/"))

        bearer_tokens = [token for token in bearer_tokens if token]
        path_secrets = [secret for secret in path_secrets if secret]
        return cls(tuple(dict.fromkeys(bearer_tokens)), tuple(dict.fromkeys(path_secrets)), bool(args.allow_no_auth))

    def authorize(self, path: str, headers: Any) -> str:
        if self.allow_no_auth:
            return "no_auth"

        path_secret = self._path_secret(path)
        if path_secret and any(hmac.compare_digest(path_secret, secret) for secret in self.path_secrets):
            return "path_secret"

        header = str(headers.get("Authorization") or "").strip()
        if header.lower().startswith("bearer "):
            token = header.split(" ", 1)[1].strip()
            if any(hmac.compare_digest(token, expected) for expected in self.bearer_tokens):
                return "bearer"

        raise AuthError("missing or invalid Alexandria MCP authorization")

    @staticmethod
    def _path_secret(path: str) -> str:
        parts = [part for part in urllib.parse.urlparse(path).path.split("/") if part]
        if len(parts) == 2 and parts[0] == "mcp":
            return parts[1]
        return ""


class AuditLogger:
    def __init__(self, path: Path | None, *, log_payloads: bool = False) -> None:
        self.path = path
        self.log_payloads = log_payloads

    def write(self, event: str, **fields: Any) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {"time": utc_now(), "event": event, **fields}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


TOOLS: list[dict[str, Any]] = [
    {
        "name": "alexandria_status",
        "title": "Show Alexandria status",
        "description": "Use this when the user wants to check whether Alexandria is live, how many memories are stored, and which D-ACCA hooks are available.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "alexandria_import_memories",
        "title": "Import selected memories",
        "description": "Use this when the user asks to save selected memories from a ChatGPT, Codex, OpenCode, or agent conversation into Alexandria. Pass one explicit memory per item. Do not invent memories.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": MAX_IMPORT_ITEMS,
                    "items": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "text": {"type": "string"},
                                    "memory": {"type": "string"},
                                    "content": {"type": "string"},
                                    "title": {"type": "string"},
                                    "tags": {"type": "array", "items": {"type": "string"}},
                                    "aliases": {"type": "array", "items": {"type": "string"}},
                                    "source_family": {"type": "string"},
                                    "authority": {"type": "string"},
                                    "staleness": {"type": "string"},
                                    "project": {"type": "string"},
                                    "source": {"type": "string"},
                                    "why": {"type": "string"},
                                },
                                "additionalProperties": True,
                            },
                        ]
                    },
                },
                "conversation_title": {"type": "string"},
                "conversation_url": {"type": "string"},
                "agent": {"type": "string", "default": "chatgpt"},
                "project": {"type": "string"},
                "source": {"type": "string"},
            },
            "required": ["items"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "alexandria_pick_memories",
        "title": "Pick relevant memories",
        "description": "Use this when the user asks Alexandria to retrieve the most relevant stored memories or build a context packet for the current task. Returns the model-visible packet plus route id and proof summary.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The user task or question that needs memory context."},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 8, "default": 5},
                "strategy": {"type": "string", "enum": sorted(VALID_STRATEGIES), "default": "helper-lazy"},
                "include_proof": {"type": "boolean", "default": True},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "alexandria_search_memories",
        "title": "Search memories",
        "description": "Use this when the user wants a lightweight search over stored Alexandria memories without building a full context packet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                "include_text": {"type": "boolean", "default": False},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "alexandria_list_memories",
        "title": "List memories",
        "description": "Use this when the user asks to inspect recently stored Alexandria memories. Prefer search or pick for task-specific recall.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
                "offset": {"type": "integer", "minimum": 0, "default": 0},
                "include_text": {"type": "boolean", "default": False},
            },
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "alexandria_get_proof",
        "title": "Get route proof",
        "description": "Use this when the user asks why Alexandria selected a memory packet or wants the D-ACCA route proof for a route id returned by alexandria_pick_memories.",
        "inputSchema": {
            "type": "object",
            "properties": {"route_id": {"type": "string"}},
            "required": ["route_id"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "alexandria_feedback",
        "title": "Record packet feedback",
        "description": "Use this when the user confirms, rejects, or corrects a recalled memory packet. This writes feedback only; it does not delete memories.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "route_id": {"type": "string"},
                "rating": {"type": "string", "enum": ["useful", "wrong", "partial", "stale", "unsafe"]},
                "note": {"type": "string"},
                "expected_ids": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["route_id", "rating"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
    },
]


class AlexandriaMcpBridge:
    def __init__(self, client: DogfoodHttpClient, audit: AuditLogger) -> None:
        self.client = client
        self.audit = audit

    def handle_json_rpc(self, payload: Any, *, auth_mode: str) -> tuple[int, Any | None]:
        if isinstance(payload, list):
            responses = [response for request in payload if (response := self._handle_one(request, auth_mode=auth_mode)) is not None]
            return (200, responses) if responses else (202, None)
        response = self._handle_one(payload, auth_mode=auth_mode)
        return (200, response) if response is not None else (202, None)

    def _handle_one(self, request: Any, *, auth_mode: str) -> dict[str, Any] | None:
        request_id = None
        started = time.perf_counter()
        method = "<invalid>"
        try:
            if not isinstance(request, dict):
                raise RpcError(-32600, "JSON-RPC request must be an object")
            request_id = request.get("id")
            method = str(request.get("method") or "")
            params = request.get("params") if isinstance(request.get("params"), dict) else {}
            result = self._dispatch(method, params, auth_mode=auth_mode)
            latency_ms = round((time.perf_counter() - started) * 1000, 3)
            self.audit.write("rpc_ok", method=method, has_id=request_id is not None, auth_mode=auth_mode, latency_ms=latency_ms)
            if request_id is None:
                return None
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except RpcError as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 3)
            self.audit.write(
                "rpc_error",
                method=method,
                has_id=request_id is not None,
                auth_mode=auth_mode,
                code=exc.code,
                message=exc.message,
                latency_ms=latency_ms,
            )
            if request_id is None:
                return None
            error: dict[str, Any] = {"code": exc.code, "message": exc.message}
            if exc.data is not None:
                error["data"] = exc.data
            return {"jsonrpc": "2.0", "id": request_id, "error": error}

    def _dispatch(self, method: str, params: dict[str, Any], *, auth_mode: str) -> Any:
        if method == "initialize":
            return {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}, "resources": {}, "prompts": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": (
                    "Alexandria is a private D-ACCA context and memory bridge. "
                    "Use alexandria_import_memories only for explicit user-approved memories. "
                    "Use alexandria_pick_memories before answering tasks that need prior project context."
                ),
            }
        if method in {"notifications/initialized", "logging/setLevel"}:
            return {}
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": TOOLS}
        if method == "resources/list":
            return {"resources": []}
        if method == "prompts/list":
            return {"prompts": []}
        if method == "tools/call":
            name = str(params.get("name") or "")
            arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            return self._call_tool(name, arguments, auth_mode=auth_mode)
        raise RpcError(-32601, f"unsupported method: {method}")

    def _call_tool(self, name: str, arguments: dict[str, Any], *, auth_mode: str) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            if name == "alexandria_status":
                result = self._status()
                summary = f"Alexandria is live with {result['health'].get('memory_count', 0)} stored memories."
            elif name == "alexandria_import_memories":
                result = self._import_memories(arguments)
                summary = f"Imported {result.get('ingested', 0)} memories into Alexandria."
            elif name == "alexandria_pick_memories":
                result = self._pick_memories(arguments)
                summary = (
                    f"Selected {len(result.get('selected_ids', []))} memories for route "
                    f"{result.get('route_id')} at confidence {result.get('confidence')}."
                )
            elif name == "alexandria_search_memories":
                result = self._search_memories(arguments)
                summary = f"Found {result.get('count', 0)} matching memories."
            elif name == "alexandria_list_memories":
                result = self._list_memories(arguments)
                summary = f"Listed {len(result.get('items', []))} of {result.get('total', 0)} stored memories."
            elif name == "alexandria_get_proof":
                result = self._get_proof(arguments)
                summary = f"Loaded route proof for {result.get('route_id')}."
            elif name == "alexandria_feedback":
                result = self._feedback(arguments)
                summary = f"Recorded feedback for route {result.get('feedback', {}).get('route_id')}."
            else:
                raise RpcError(-32602, f"unknown tool: {name}")

            latency_ms = round((time.perf_counter() - started) * 1000, 3)
            self.audit.write(
                "tool_ok",
                tool=name,
                auth_mode=auth_mode,
                latency_ms=latency_ms,
                summary=self._argument_summary(name, arguments, result),
            )
            return {"content": [{"type": "text", "text": summary}], "structuredContent": result}
        except EngineClientError as exc:
            raise RpcError(-32000, str(exc), {"path": exc.path, "status": exc.status, "body": exc.body[:500]}) from exc

    def _status(self) -> dict[str, Any]:
        return {"server": {"name": SERVER_NAME, "version": SERVER_VERSION}, "health": self.client.health(), "hooks": self.client.hooks()}

    def _import_memories(self, args: dict[str, Any]) -> dict[str, Any]:
        raw_items = args.get("items")
        if not isinstance(raw_items, list) or not raw_items:
            raise RpcError(-32602, "items must be a non-empty array")
        if len(raw_items) > MAX_IMPORT_ITEMS:
            raise RpcError(-32602, f"items exceeds max import count of {MAX_IMPORT_ITEMS}")

        agent = first_nonempty(args.get("agent"), "chatgpt")
        source = first_nonempty(args.get("source"), args.get("conversation_title"), f"{agent}_conversation")
        conversation_title = first_nonempty(args.get("conversation_title"))
        conversation_url = first_nonempty(args.get("conversation_url"))
        project = first_nonempty(args.get("project"), "alexandria")

        normalized = []
        for index, raw in enumerate(raw_items):
            item = self._normalize_import_item(
                raw,
                index=index,
                agent=agent,
                source=source,
                project=project,
                conversation_title=conversation_title,
                conversation_url=conversation_url,
            )
            if item:
                normalized.append(item)
        if not normalized:
            raise RpcError(-32602, "no import items contained non-empty memory text")

        response = self.client.ingest({"items": normalized, "source": source, "project": project})
        return {
            "imported_at": utc_now(),
            "agent": agent,
            "conversation_title": conversation_title,
            "conversation_url": conversation_url,
            **response,
        }

    def _normalize_import_item(
        self,
        raw: Any,
        *,
        index: int,
        agent: str,
        source: str,
        project: str,
        conversation_title: str,
        conversation_url: str,
    ) -> dict[str, Any] | None:
        if isinstance(raw, str):
            item: dict[str, Any] = {"text": raw}
        elif isinstance(raw, dict):
            item = dict(raw)
        else:
            item = {"text": str(raw)}

        text = first_nonempty(item.get("text"), item.get("memory"), item.get("content"))
        if not text:
            return None
        text = text[:MAX_TEXT_CHARS]

        title = first_nonempty(item.get("title"))
        why = first_nonempty(item.get("why"))
        if title and not text.lower().startswith(title.lower()):
            text = f"{title}: {text}"
        if why:
            text = f"{text}\n\nWhy this matters: {why[:1200]}"

        source_family = first_nonempty(item.get("source_family"), "workflow_trace")
        if source_family not in VALID_SOURCE_FAMILIES:
            source_family = "workflow_trace"
        authority = first_nonempty(item.get("authority"), "medium")
        if authority not in VALID_AUTHORITIES:
            authority = "medium"
        staleness = first_nonempty(item.get("staleness"), "current")
        if staleness not in VALID_STALENESS:
            staleness = "current"

        tags = coerce_strings(item.get("tags"), lowercase=True, limit=12)
        tags.extend(["alexandria_import", f"agent:{agent}", source_family])
        if conversation_title:
            tags.append("conversation")

        provenance = item.get("provenance") if isinstance(item.get("provenance"), dict) else {}
        provenance = {
            **provenance,
            "generator": "alexandria_mcp_server",
            "source_agent": agent,
            "source_conversation_title": conversation_title,
            "source_conversation_url": conversation_url,
            "record_index": index,
        }
        provenance = {key: value for key, value in provenance.items() if value not in ("", [], None)}

        return {
            "id": first_nonempty(item.get("id")),
            "text": text,
            "source": first_nonempty(item.get("source"), source),
            "project": first_nonempty(item.get("project"), project),
            "source_family": source_family,
            "authority": authority,
            "staleness": staleness,
            "tags": coerce_strings(tags, lowercase=True, limit=16),
            "aliases": coerce_strings(item.get("aliases") or tags, limit=24),
            "provenance": provenance,
        }

    def _pick_memories(self, args: dict[str, Any]) -> dict[str, Any]:
        query = first_nonempty(args.get("query"))
        if not query:
            raise RpcError(-32602, "query is required")
        strategy = first_nonempty(args.get("strategy"), "helper-lazy")
        if strategy not in VALID_STRATEGIES:
            raise RpcError(-32602, f"strategy must be one of {sorted(VALID_STRATEGIES)}")
        top_k = safe_int(args.get("top_k"), 5, minimum=1, maximum=8)
        include_proof = bool(args.get("include_proof", True))
        response = self.client.packet(
            {
                "query": query,
                "strategy": strategy,
                "include_proof": include_proof,
                "max_evidence_items": top_k,
            }
        )
        return {
            "model_visible_packet": response.get("packet", {}),
            "route_id": response.get("route_id"),
            "strategy": response.get("strategy"),
            "decision": response.get("decision"),
            "confidence": response.get("confidence"),
            "selected_ids": response.get("selected_ids", []),
            "latency_ms": response.get("latency_ms"),
            "route_summary": response.get("route_summary", {}),
            "route_proof": response.get("route_proof"),
            "artifact_errors": response.get("artifact_errors", []),
        }

    def _search_memories(self, args: dict[str, Any]) -> dict[str, Any]:
        query = first_nonempty(args.get("query"))
        if not query:
            raise RpcError(-32602, "query is required")
        return self.client.search(
            query,
            limit=safe_int(args.get("limit"), 10, minimum=1, maximum=50),
            include_text=bool(args.get("include_text", False)),
        )

    def _list_memories(self, args: dict[str, Any]) -> dict[str, Any]:
        return self.client.memories(
            limit=safe_int(args.get("limit"), 25, minimum=1, maximum=100),
            offset=safe_int(args.get("offset"), 0, minimum=0, maximum=1_000_000),
            include_text=bool(args.get("include_text", False)),
        )

    def _get_proof(self, args: dict[str, Any]) -> dict[str, Any]:
        route_id = first_nonempty(args.get("route_id"))
        if not route_id:
            raise RpcError(-32602, "route_id is required")
        return self.client.proof(route_id)

    def _feedback(self, args: dict[str, Any]) -> dict[str, Any]:
        route_id = first_nonempty(args.get("route_id"))
        rating = first_nonempty(args.get("rating")).lower()
        if not route_id or not rating:
            raise RpcError(-32602, "route_id and rating are required")
        return self.client.feedback(
            {
                "route_id": route_id,
                "rating": rating,
                "note": first_nonempty(args.get("note")),
                "expected_ids": coerce_strings(args.get("expected_ids"), lowercase=True),
                "tags": coerce_strings(args.get("tags"), lowercase=True),
            }
        )

    @staticmethod
    def _argument_summary(name: str, args: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        if name == "alexandria_import_memories":
            return {"items": len(args.get("items") or []), "ingested": result.get("ingested", 0)}
        if name == "alexandria_pick_memories":
            return {"query_chars": len(str(args.get("query") or "")), "selected": len(result.get("selected_ids", []))}
        if name == "alexandria_search_memories":
            return {"query_chars": len(str(args.get("query") or "")), "count": result.get("count", 0)}
        return {"keys": sorted(args)}


def make_handler(bridge: AlexandriaMcpBridge, auth: AuthConfig) -> type[BaseHTTPRequestHandler]:
    class AlexandriaMcpHandler(BaseHTTPRequestHandler):
        server_version = "AlexandriaMcp/0.1"

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self._write_cors_headers()
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            if path == "/health":
                self._write_json(200, {"ok": True, "server": SERVER_NAME, "version": SERVER_VERSION, "time": utc_now()})
                return
            if path == "/ready":
                try:
                    self._write_json(200, {"ok": True, "engine": bridge.client.health(), "time": utc_now()})
                except Exception as exc:
                    self._write_json(503, {"ok": False, "error": type(exc).__name__, "message": str(exc)})
                return
            if self._is_mcp_path(path):
                self._write_json(405, {"error": "method_not_allowed", "message": "POST JSON-RPC to this MCP endpoint."})
                return
            self._write_json(404, {"error": "not_found", "path": path})

        def do_POST(self) -> None:  # noqa: N802
            started = time.perf_counter()
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            if not self._is_mcp_path(path):
                self._write_json(404, {"error": "not_found", "path": redact_path(path, auth)})
                return
            try:
                auth_mode = auth.authorize(path, self.headers)
                payload = self._read_json_body()
                status, response = bridge.handle_json_rpc(payload, auth_mode=auth_mode)
                latency_ms = round((time.perf_counter() - started) * 1000, 3)
                bridge.audit.write("http_ok", path=redact_path(path, auth), auth_mode=auth_mode, status=status, latency_ms=latency_ms)
                if response is None:
                    self.send_response(status)
                    self._write_cors_headers()
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                else:
                    self._write_json(status, response)
            except AuthError as exc:
                bridge.audit.write("http_auth_error", path=redact_path(path, auth), message=str(exc))
                self._write_json(401, {"error": "unauthorized", "message": str(exc)})
            except Exception as exc:
                bridge.audit.write("http_error", path=redact_path(path, auth), error=type(exc).__name__, message=str(exc))
                self._write_json(400, {"error": type(exc).__name__, "message": str(exc)})

        def _is_mcp_path(self, path: str) -> bool:
            parts = [part for part in path.split("/") if part]
            return parts == ["mcp"] or (len(parts) == 2 and parts[0] == "mcp")

        def _read_json_body(self) -> Any:
            length = int(self.headers.get("Content-Length") or "0")
            if length > MAX_BODY_BYTES:
                raise ValueError(f"body too large; max {MAX_BODY_BYTES} bytes")
            raw = self.rfile.read(length)
            if not raw:
                raise ValueError("empty request body")
            return json.loads(raw.decode("utf-8"))

        def _write_json(self, status: int, payload: Any) -> None:
            body = json_bytes(payload)
            self.send_response(status)
            self._write_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _write_cors_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, Mcp-Session-Id, Mcp-Protocol-Version")
            self.send_header("Access-Control-Max-Age", "600")

        def log_message(self, format: str, *args: Any) -> None:
            return

    return AlexandriaMcpHandler


def serve(args: argparse.Namespace) -> int:
    auth = AuthConfig.from_args(args)
    if not auth.allow_no_auth and not auth.bearer_tokens and not auth.path_secrets:
        raise SystemExit("Refusing to start without --secrets-file, --bearer-token/--bearer-token-env, --path-secret, or --allow-no-auth.")

    audit_path = None if args.audit_log == "" else Path(args.audit_log)
    client = DogfoodHttpClient(args.engine_base_url, timeout=args.engine_timeout)
    bridge = AlexandriaMcpBridge(client, AuditLogger(audit_path, log_payloads=args.log_payloads))
    server = ThreadingHTTPServer((args.host, args.port), make_handler(bridge, auth))
    print(f"Alexandria MCP listening on http://{args.host}:{args.port}/mcp")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Alexandria MCP bridge for D-ACCA dogfood hooks.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8790)
    parser.add_argument("--engine-base-url", default=DEFAULT_ENGINE_BASE_URL)
    parser.add_argument("--engine-timeout", type=float, default=10.0)
    parser.add_argument("--secrets-file", default="")
    parser.add_argument("--bearer-token", default="")
    parser.add_argument("--bearer-token-env", default="ALEXANDRIA_MCP_TOKEN")
    parser.add_argument("--path-secret", default="")
    parser.add_argument("--allow-no-auth", action="store_true")
    parser.add_argument("--audit-log", default=str(DEFAULT_AUDIT_LOG))
    parser.add_argument("--log-payloads", action="store_true")
    return serve(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
