from __future__ import annotations

import argparse
import base64
import hashlib
import html
import hmac
import json
import os
import secrets
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
MCP_CONTRACT_VERSION = "alexandria.mcp.contract.v0.2"
TOOL_OUTPUT_SCHEMA_VERSION = "alexandria.mcp.tool_output.v0.2"
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
OAUTH_READ_SCOPE = "alexandria.read"
OAUTH_WRITE_SCOPE = "alexandria.write"
OAUTH_SCOPES = (OAUTH_READ_SCOPE, OAUTH_WRITE_SCOPE)
TOOL_SCOPES: dict[str, tuple[str, ...]] = {
    "alexandria_status": (OAUTH_READ_SCOPE,),
    "alexandria_import_memories": (OAUTH_WRITE_SCOPE,),
    "alexandria_pick_memories": (OAUTH_READ_SCOPE,),
    "alexandria_search_memories": (OAUTH_READ_SCOPE,),
    "alexandria_list_memories": (OAUTH_READ_SCOPE,),
    "alexandria_get_proof": (OAUTH_READ_SCOPE,),
    "alexandria_feedback": (OAUTH_WRITE_SCOPE,),
}


class RpcError(Exception):
    def __init__(self, code: int, message: str, data: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class AuthError(Exception):
    def __init__(self, message: str, challenge: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.challenge = challenge


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


def token_urlsafe(bytes_count: int = 32) -> str:
    return secrets.token_urlsafe(bytes_count).rstrip("=")


def sha256_b64url(value: str) -> str:
    digest = hashlib.sha256(value.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def now_seconds() -> int:
    return int(time.time())


def parse_authorization_scopes(value: Any) -> tuple[str, ...]:
    raw = str(value or "").strip()
    if not raw:
        return (OAUTH_READ_SCOPE,)
    requested = coerce_strings(raw.replace(",", " ").split(), lowercase=True, limit=16)
    unknown = [scope for scope in requested if scope not in OAUTH_SCOPES]
    if unknown:
        raise ValueError(f"unsupported OAuth scope(s): {', '.join(unknown)}")
    if not requested:
        raise ValueError("scope must include at least one supported OAuth scope")
    return tuple(requested)


def parse_form_bytes(raw: bytes) -> dict[str, str]:
    parsed = urllib.parse.parse_qs(raw.decode("utf-8"), keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def redact_path(path: str, auth: "AuthConfig") -> str:
    redacted = path
    for secret in auth.path_secrets:
        if secret:
            redacted = redacted.replace(secret, "<path-secret>")
    return redacted


@dataclass(frozen=True)
class AuthResult:
    mode: str
    subject: str = ""
    scopes: tuple[str, ...] = ()

    def grants(self, required_scopes: tuple[str, ...]) -> bool:
        if self.mode in {"bearer", "no_auth"}:
            return True
        if self.mode != "oauth":
            return False
        return set(required_scopes).issubset(set(self.scopes))


@dataclass
class OAuthClient:
    client_id: str
    redirect_uris: tuple[str, ...]
    client_name: str
    created_at: int


@dataclass
class OAuthCode:
    code: str
    client_id: str
    redirect_uri: str
    code_challenge: str
    code_challenge_method: str
    scopes: tuple[str, ...]
    resource: str
    expires_at: int
    subject: str


@dataclass
class OAuthAccessToken:
    token_hash: str
    subject: str
    scopes: tuple[str, ...]
    resource: str
    expires_at: int


class OAuthProvider:
    def __init__(
        self,
        *,
        enabled: bool = False,
        require_for_tools: bool = False,
        owner_pin: str = "",
        public_base_url: str = "",
        code_ttl_seconds: int = 300,
        token_ttl_seconds: int = 86_400,
    ) -> None:
        self.enabled = enabled
        self.require_for_tools = require_for_tools
        self.owner_pin = owner_pin
        self.public_base_url = public_base_url.rstrip("/")
        self.code_ttl_seconds = code_ttl_seconds
        self.token_ttl_seconds = token_ttl_seconds
        self.clients: dict[str, OAuthClient] = {}
        self.codes: dict[str, OAuthCode] = {}
        self.tokens: dict[str, OAuthAccessToken] = {}

    @classmethod
    def disabled(cls) -> "OAuthProvider":
        return cls()

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "OAuthProvider":
        owner_pin = first_nonempty(args.oauth_owner_pin)
        if args.oauth_owner_pin_env:
            owner_pin = first_nonempty(owner_pin, os.environ.get(args.oauth_owner_pin_env))
        if args.secrets_file:
            path = Path(args.secrets_file)
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8-sig"))
                owner_pin = first_nonempty(owner_pin, data.get("mcp_oauth_owner_pin"), data.get("oauth_owner_pin"))
        return cls(
            enabled=bool(args.oauth_enabled),
            require_for_tools=bool(args.require_oauth_for_tools),
            owner_pin=owner_pin,
            public_base_url=first_nonempty(args.public_base_url),
            code_ttl_seconds=safe_int(args.oauth_code_ttl_seconds, 300, minimum=60, maximum=3600),
            token_ttl_seconds=safe_int(args.oauth_token_ttl_seconds, 86_400, minimum=300, maximum=2_592_000),
        )

    def origin(self, headers: Any) -> str:
        if self.public_base_url:
            return self.public_base_url
        host = first_nonempty(headers.get("X-Forwarded-Host"), headers.get("Host"), "127.0.0.1")
        proto = first_nonempty(headers.get("X-Forwarded-Proto"))
        if not proto:
            proto = "https" if not host.startswith(("127.0.0.1", "localhost")) else "http"
        return f"{proto}://{host}".rstrip("/")

    def protected_resource_metadata(self, headers: Any) -> dict[str, Any]:
        origin = self.origin(headers)
        return {
            "resource": origin,
            "authorization_servers": [origin],
            "scopes_supported": list(OAUTH_SCOPES),
            "resource_documentation": "https://developers.openai.com/apps-sdk/build/auth",
            "token_endpoint_auth_methods_supported": ["none"],
        }

    def authorization_server_metadata(self, headers: Any) -> dict[str, Any]:
        origin = self.origin(headers)
        return {
            "issuer": origin,
            "authorization_endpoint": f"{origin}/oauth/authorize",
            "token_endpoint": f"{origin}/oauth/token",
            "registration_endpoint": f"{origin}/oauth/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
            "scopes_supported": list(OAUTH_SCOPES),
        }

    def www_authenticate(
        self,
        headers: Any,
        scopes: tuple[str, ...] = OAUTH_SCOPES,
        *,
        error: str = "insufficient_scope",
        error_description: str = "OAuth login is required to use Alexandria.",
    ) -> str:
        metadata_url = f"{self.origin(headers)}/.well-known/oauth-protected-resource"
        scope = " ".join(scopes)
        return (
            f'Bearer resource_metadata="{metadata_url}", '
            f'scope="{scope}", error="{error}", error_description="{error_description}"'
        )

    def register_client(self, payload: dict[str, Any], headers: Any) -> dict[str, Any]:
        redirect_uris = tuple(coerce_strings(payload.get("redirect_uris"), limit=12))
        if not redirect_uris:
            raise ValueError("redirect_uris is required")
        client_id = f"{self.origin(headers)}/oauth/client/{token_urlsafe(18)}"
        client = OAuthClient(
            client_id=client_id,
            redirect_uris=redirect_uris,
            client_name=first_nonempty(payload.get("client_name"), "ChatGPT Alexandria connector"),
            created_at=now_seconds(),
        )
        self.clients[client_id] = client
        return {
            "client_id": client.client_id,
            "client_name": client.client_name,
            "redirect_uris": list(client.redirect_uris),
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        }

    def authorize_page(self, params: dict[str, str], headers: Any, *, error: str = "") -> bytes:
        escaped = {key: html.escape(str(value), quote=True) for key, value in params.items()}
        hidden = "\n".join(
            f'<input type="hidden" name="{html.escape(key, quote=True)}" value="{value}">'
            for key, value in escaped.items()
        )
        error_html = f'<p class="error">{html.escape(error)}</p>' if error else ""
        body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Authorize Alexandria</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 560px; margin: 56px auto; padding: 0 20px; }}
    label, input, button {{ display: block; width: 100%; box-sizing: border-box; }}
    input {{ margin: 8px 0 18px; padding: 10px; font-size: 16px; }}
    button {{ padding: 10px; font-size: 16px; }}
    .error {{ color: #b00020; }}
    .meta {{ color: #555; font-size: 14px; }}
  </style>
</head>
<body>
  <h1>Authorize Alexandria</h1>
  <p class="meta">This approves ChatGPT to use the local Alexandria MCP tools for this dogfood tunnel.</p>
  {error_html}
  <form method="post" action="/oauth/authorize">
    {hidden}
    <label for="pin">Owner PIN</label>
    <input id="pin" name="pin" type="password" autocomplete="one-time-code" autofocus>
    <button type="submit">Authorize</button>
  </form>
</body>
</html>"""
        return body.encode("utf-8")

    def approve_authorization(self, form: dict[str, str]) -> tuple[str, str]:
        if not self.owner_pin:
            raise ValueError("OAuth owner PIN is not configured")
        if not hmac.compare_digest(str(form.get("pin") or ""), self.owner_pin):
            raise PermissionError("Invalid owner PIN")
        if form.get("response_type") != "code":
            raise ValueError("response_type must be code")
        client_id = first_nonempty(form.get("client_id"))
        redirect_uri = first_nonempty(form.get("redirect_uri"))
        code_challenge = first_nonempty(form.get("code_challenge"))
        if not client_id or not redirect_uri or not code_challenge:
            raise ValueError("client_id, redirect_uri, and code_challenge are required")
        client = self.clients.get(client_id)
        if client is None:
            client = OAuthClient(client_id=client_id, redirect_uris=(redirect_uri,), client_name="ChatGPT CIMD client", created_at=now_seconds())
            self.clients[client_id] = client
        if redirect_uri not in client.redirect_uris:
            raise ValueError("redirect_uri is not registered for this client")
        method = first_nonempty(form.get("code_challenge_method"), "S256")
        if method != "S256":
            raise ValueError("code_challenge_method must be S256")
        scopes = parse_authorization_scopes(form.get("scope"))
        code = token_urlsafe(32)
        self.codes[code] = OAuthCode(
            code=code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=method,
            scopes=scopes,
            resource=first_nonempty(form.get("resource")),
            expires_at=now_seconds() + self.code_ttl_seconds,
            subject="alexandria-owner",
        )
        query = {"code": code}
        if form.get("state"):
            query["state"] = str(form["state"])
        return redirect_uri, f"{redirect_uri}?{urllib.parse.urlencode(query)}"

    def exchange_token(self, form: dict[str, str]) -> dict[str, Any]:
        if form.get("grant_type") != "authorization_code":
            raise ValueError("grant_type must be authorization_code")
        code_value = first_nonempty(form.get("code"))
        code = self.codes.pop(code_value, None)
        if code is None:
            raise PermissionError("invalid authorization code")
        if code.expires_at < now_seconds():
            raise PermissionError("authorization code expired")
        if first_nonempty(form.get("redirect_uri")) != code.redirect_uri:
            raise PermissionError("redirect_uri mismatch")
        if first_nonempty(form.get("client_id")) != code.client_id:
            raise PermissionError("client_id mismatch")
        verifier = first_nonempty(form.get("code_verifier"))
        if not verifier or sha256_b64url(verifier) != code.code_challenge:
            raise PermissionError("PKCE verification failed")

        token = token_urlsafe(40)
        token_record = OAuthAccessToken(
            token_hash=self._hash_token(token),
            subject=code.subject,
            scopes=code.scopes,
            resource=code.resource,
            expires_at=now_seconds() + self.token_ttl_seconds,
        )
        self.tokens[token_record.token_hash] = token_record
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": self.token_ttl_seconds,
            "scope": " ".join(code.scopes),
        }

    def verify_bearer(self, token: str) -> AuthResult | None:
        record = self.tokens.get(self._hash_token(token))
        if record is None:
            return None
        if record.expires_at < now_seconds():
            self.tokens.pop(record.token_hash, None)
            return None
        return AuthResult("oauth", subject=record.subject, scopes=record.scopes)

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuthConfig:
    bearer_tokens: tuple[str, ...]
    path_secrets: tuple[str, ...]
    oauth: OAuthProvider
    allow_no_auth: bool = False

    @classmethod
    def from_args(cls, args: argparse.Namespace, oauth: OAuthProvider) -> "AuthConfig":
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
        return cls(tuple(dict.fromkeys(bearer_tokens)), tuple(dict.fromkeys(path_secrets)), oauth, bool(args.allow_no_auth))

    def authorize(self, path: str, headers: Any) -> AuthResult:
        if self.allow_no_auth:
            return AuthResult("no_auth")

        header = str(headers.get("Authorization") or "").strip()
        if header.lower().startswith("bearer "):
            token = header.split(" ", 1)[1].strip()
            if any(hmac.compare_digest(token, expected) for expected in self.bearer_tokens):
                return AuthResult("bearer", subject="local-bearer", scopes=OAUTH_SCOPES)
            if self.oauth.enabled:
                auth_result = self.oauth.verify_bearer(token)
                if auth_result is not None:
                    return auth_result

        path_secret = self._path_secret(path)
        if path_secret and any(hmac.compare_digest(path_secret, secret) for secret in self.path_secrets):
            return AuthResult("path_secret")

        challenge = self.oauth.www_authenticate(headers) if self.oauth.enabled else ""
        raise AuthError("missing or invalid Alexandria MCP authorization", challenge)

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


def tool_output_schema(
    *,
    tool: str,
    properties: dict[str, Any] | None = None,
    required: list[str] | None = None,
    description: str = "",
) -> dict[str, Any]:
    schema_properties: dict[str, Any] = {
        "schema_version": {"type": "string", "const": TOOL_OUTPUT_SCHEMA_VERSION},
        "contract_version": {"type": "string", "const": MCP_CONTRACT_VERSION},
        "tool": {"type": "string", "const": tool},
    }
    schema_properties.update(properties or {})
    return {
        "type": "object",
        "description": description or f"Structured output for {tool}.",
        "required": ["schema_version", "contract_version", "tool", *(required or [])],
        "properties": schema_properties,
        "additionalProperties": True,
    }


MEMORY_VIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["id"],
    "properties": {
        "id": {"type": "string"},
        "source_family": {"type": ["string", "null"]},
        "authority": {"type": ["string", "null"]},
        "created_at": {"type": ["string", "null"]},
        "claim_type": {"type": ["string", "null"]},
        "staleness": {"type": ["string", "null"]},
        "safety_label": {"type": ["string", "null"]},
        "exposure_policy": {"type": ["string", "null"]},
        "tags": {"type": "array", "items": {"type": "string"}},
        "aliases": {"type": "array", "items": {"type": "string"}},
        "provenance": {"type": "object", "additionalProperties": True},
        "text": {"type": "string"},
        "text_preview": {"type": "string"},
        "score": {"type": "number"},
    },
    "additionalProperties": True,
}


TOOLS: list[dict[str, Any]] = [
    {
        "name": "alexandria_status",
        "title": "Show Alexandria status",
        "description": "Use this when the user wants to check whether Alexandria is live, how many memories are stored, and which D-ACCA hooks are available.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "outputSchema": tool_output_schema(
            tool="alexandria_status",
            required=["server", "health", "hooks"],
            properties={
                "server": {"type": "object", "additionalProperties": True},
                "health": {"type": "object", "additionalProperties": True},
                "hooks": {"type": "object", "additionalProperties": True},
            },
            description="Status, hook discovery, and memory-health metadata for the local Alexandria engine.",
        ),
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "alexandria_import_memories",
        "title": "Import selected memories",
        "description": "Use this only when the user asks to save selected long-term memories from a ChatGPT, Codex, OpenCode, or agent conversation into Alexandria. Pass one explicit durable fact, decision, preference, runbook note, or project constraint per item. Do not import raw transcript dumps and do not invent memories.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "description": "One memory candidate per array item. A string is treated as memory text. An object may include text plus title, tags, source metadata, and why the memory matters.",
                    "minItems": 1,
                    "maxItems": MAX_IMPORT_ITEMS,
                    "items": {
                        "oneOf": [
                            {"type": "string", "description": "A single explicit memory statement approved or provided by the user."},
                            {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "description": "Optional stable caller-provided id. Alexandria will still normalize ids."},
                                    "text": {"type": "string", "description": "The memory text. Prefer concise, durable facts over conversation excerpts."},
                                    "memory": {"type": "string", "description": "Alias for text when the caller naturally uses a memory field."},
                                    "content": {"type": "string", "description": "Alias for text when importing from generic content records."},
                                    "title": {"type": "string", "description": "Short label prepended to the memory text when useful."},
                                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Lowercase topical tags such as project, subsystem, workflow, or tool name."},
                                    "aliases": {"type": "array", "items": {"type": "string"}, "description": "Search phrases that should recall this memory."},
                                    "source_family": {"type": "string", "enum": sorted(VALID_SOURCE_FAMILIES), "description": "Memory family used by D-ACCA routing and admissibility."},
                                    "authority": {"type": "string", "enum": sorted(VALID_AUTHORITIES), "description": "Confidence level for the source. Use high only for user-confirmed or canonical project facts."},
                                    "staleness": {"type": "string", "enum": sorted(VALID_STALENESS), "description": "Freshness label. Use stale when retaining historical context that should be treated cautiously."},
                                    "project": {"type": "string", "description": "Project or workspace this memory belongs to."},
                                    "source": {"type": "string", "description": "Human-readable source name, document, chat title, tool, or run id."},
                                    "why": {"type": "string", "description": "Brief reason this belongs in long-term memory. The bridge appends this to provenance-oriented text."},
                                },
                                "additionalProperties": True,
                            },
                        ]
                    },
                },
                "conversation_title": {"type": "string", "description": "Optional title of the source conversation for provenance."},
                "conversation_url": {"type": "string", "description": "Optional URL of the source conversation for provenance."},
                "agent": {"type": "string", "default": "chatgpt", "description": "Originating agent or host, for example chatgpt, codex, opencode, or human."},
                "project": {"type": "string", "description": "Default project applied to items that omit project."},
                "source": {"type": "string", "description": "Default source label applied to items that omit source."},
            },
            "required": ["items"],
            "additionalProperties": False,
        },
        "outputSchema": tool_output_schema(
            tool="alexandria_import_memories",
            required=["imported_at", "agent", "ingested", "ids", "memory_count"],
            properties={
                "imported_at": {"type": "string"},
                "agent": {"type": "string"},
                "conversation_title": {"type": "string"},
                "conversation_url": {"type": "string"},
                "import_id": {"type": "string"},
                "ingested": {"type": "integer"},
                "ids": {"type": "array", "items": {"type": "string"}},
                "memory_count": {"type": "integer"},
            },
            description="Import result for explicit memory candidates saved through Alexandria.",
        ),
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
        "outputSchema": tool_output_schema(
            tool="alexandria_pick_memories",
            required=["model_visible_packet", "route_id", "strategy", "selected_ids"],
            properties={
                "model_visible_packet": {"type": "object", "additionalProperties": True},
                "route_id": {"type": ["string", "null"]},
                "strategy": {"type": ["string", "null"]},
                "decision": {"type": ["string", "null"]},
                "confidence": {"type": ["number", "null"]},
                "selected_ids": {"type": "array", "items": {"type": "string"}},
                "latency_ms": {"type": ["number", "null"]},
                "route_summary": {"type": "object", "additionalProperties": True},
                "route_proof": {"type": ["object", "null"], "additionalProperties": True},
                "artifact_errors": {"type": "array"},
            },
            description="D-ACCA/helper-lazy memory packet plus route metadata.",
        ),
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
        "outputSchema": tool_output_schema(
            tool="alexandria_search_memories",
            required=["query", "count", "items"],
            properties={
                "query": {"type": "string"},
                "count": {"type": "integer"},
                "items": {"type": "array", "items": MEMORY_VIEW_SCHEMA},
            },
            description="Search results over Alexandria memories.",
        ),
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
        "outputSchema": tool_output_schema(
            tool="alexandria_list_memories",
            required=["total", "limit", "offset", "items"],
            properties={
                "total": {"type": "integer"},
                "limit": {"type": "integer"},
                "offset": {"type": "integer"},
                "items": {"type": "array", "items": MEMORY_VIEW_SCHEMA},
            },
            description="Paginated Alexandria memory listing.",
        ),
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
        "outputSchema": tool_output_schema(
            tool="alexandria_get_proof",
            required=["route_id"],
            properties={
                "service_version": {"type": "string"},
                "route_id": {"type": "string"},
                "strategy": {"type": "string"},
                "decision": {"type": "string"},
                "confidence": {"type": "number"},
                "selected_ids": {"type": "array", "items": {"type": "string"}},
                "packet": {"type": "object", "additionalProperties": True},
                "route_proof": {"type": "object", "additionalProperties": True},
            },
            description="Stored route record and proof for a prior memory packet.",
        ),
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
        "outputSchema": tool_output_schema(
            tool="alexandria_feedback",
            required=["saved", "feedback"],
            properties={
                "saved": {"type": "boolean"},
                "feedback": {
                    "type": "object",
                    "required": ["route_id", "rating"],
                    "properties": {
                        "created_at": {"type": "string"},
                        "route_id": {"type": "string"},
                        "rating": {"type": "string"},
                        "note": {"type": "string"},
                        "expected_ids": {"type": "array", "items": {"type": "string"}},
                        "tags": {"type": "array", "items": {"type": "string"}},
                    },
                    "additionalProperties": True,
                },
            },
            description="Saved feedback record for a prior Alexandria route.",
        ),
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
    },
]


def tool_descriptors(*, oauth_enabled: bool) -> list[dict[str, Any]]:
    descriptors = [json.loads(json.dumps(tool, ensure_ascii=False)) for tool in TOOLS]
    if oauth_enabled:
        for tool in descriptors:
            scopes = list(TOOL_SCOPES.get(str(tool.get("name")), OAUTH_SCOPES))
            security_schemes = [{"type": "oauth2", "scopes": scopes}]
            tool["securitySchemes"] = security_schemes
            meta = tool.get("_meta") if isinstance(tool.get("_meta"), dict) else {}
            meta["securitySchemes"] = json.loads(json.dumps(security_schemes))
            tool["_meta"] = meta
    return descriptors


class AlexandriaMcpBridge:
    def __init__(self, client: DogfoodHttpClient, audit: AuditLogger, oauth: OAuthProvider | None = None) -> None:
        self.client = client
        self.audit = audit
        self.oauth = oauth or OAuthProvider.disabled()

    def handle_json_rpc(self, payload: Any, *, auth: AuthResult, headers: Any | None = None) -> tuple[int, Any | None]:
        headers = headers or {}
        if isinstance(payload, list):
            responses = [response for request in payload if (response := self._handle_one(request, auth=auth, headers=headers)) is not None]
            return (200, responses) if responses else (202, None)
        response = self._handle_one(payload, auth=auth, headers=headers)
        return (200, response) if response is not None else (202, None)

    def _handle_one(self, request: Any, *, auth: AuthResult, headers: Any) -> dict[str, Any] | None:
        request_id = None
        started = time.perf_counter()
        method = "<invalid>"
        try:
            if not isinstance(request, dict):
                raise RpcError(-32600, "JSON-RPC request must be an object")
            request_id = request.get("id")
            method = str(request.get("method") or "")
            params = request.get("params") if isinstance(request.get("params"), dict) else {}
            result = self._dispatch(method, params, auth=auth, headers=headers)
            latency_ms = round((time.perf_counter() - started) * 1000, 3)
            self.audit.write("rpc_ok", method=method, has_id=request_id is not None, auth_mode=auth.mode, latency_ms=latency_ms)
            if request_id is None:
                return None
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except RpcError as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 3)
            self.audit.write(
                "rpc_error",
                method=method,
                has_id=request_id is not None,
                auth_mode=auth.mode,
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

    def _dispatch(self, method: str, params: dict[str, Any], *, auth: AuthResult, headers: Any) -> Any:
        if method == "initialize":
            return {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}, "resources": {}, "prompts": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION, "contractVersion": MCP_CONTRACT_VERSION},
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
            return {"tools": tool_descriptors(oauth_enabled=self.oauth.enabled)}
        if method == "resources/list":
            return {"resources": []}
        if method == "prompts/list":
            return {"prompts": []}
        if method == "tools/call":
            name = str(params.get("name") or "")
            arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            return self._call_tool(name, arguments, auth=auth, headers=headers)
        raise RpcError(-32601, f"unsupported method: {method}")

    def _call_tool(self, name: str, arguments: dict[str, Any], *, auth: AuthResult, headers: Any) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            required_scopes = TOOL_SCOPES.get(name, OAUTH_SCOPES)
            if self.oauth.enabled and self.oauth.require_for_tools and not auth.grants(required_scopes):
                return self._oauth_required_tool_result(name, required_scopes, headers)
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

            result = self._with_contract(name, result)
            latency_ms = round((time.perf_counter() - started) * 1000, 3)
            self.audit.write(
                "tool_ok",
                tool=name,
                auth_mode=auth.mode,
                latency_ms=latency_ms,
                summary=self._argument_summary(name, arguments, result),
            )
            return {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)}],
                "structuredContent": result,
                "isError": False,
            }
        except EngineClientError as exc:
            raise RpcError(-32000, str(exc), {"path": exc.path, "status": exc.status, "body": exc.body[:500]}) from exc

    def _oauth_required_tool_result(self, name: str, required_scopes: tuple[str, ...], headers: Any) -> dict[str, Any]:
        structured = self._with_contract(
            name,
            {
                "error": "authentication_required",
                "required_scopes": list(required_scopes),
                "message": "OAuth login is required to use this Alexandria tool.",
            },
        )
        return {
            "content": [{"type": "text", "text": json.dumps(structured, ensure_ascii=False, sort_keys=True, indent=2)}],
            "structuredContent": structured,
            "_meta": {"mcp/www_authenticate": [self.oauth.www_authenticate(headers, required_scopes)]},
            "isError": True,
        }

    @staticmethod
    def _with_contract(tool: str, result: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": TOOL_OUTPUT_SCHEMA_VERSION,
            "contract_version": MCP_CONTRACT_VERSION,
            "tool": tool,
            **result,
        }

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
            if auth.oauth.enabled and path == "/.well-known/oauth-protected-resource":
                self._write_json(200, auth.oauth.protected_resource_metadata(self.headers))
                return
            if auth.oauth.enabled and path in {"/.well-known/oauth-authorization-server", "/.well-known/openid-configuration"}:
                self._write_json(200, auth.oauth.authorization_server_metadata(self.headers))
                return
            if auth.oauth.enabled and path == "/oauth/authorize":
                params = {key: values[-1] if values else "" for key, values in urllib.parse.parse_qs(parsed.query, keep_blank_values=True).items()}
                self._write_html(200, auth.oauth.authorize_page(params, self.headers))
                return
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
            if auth.oauth.enabled and path == "/oauth/register":
                try:
                    payload = self._read_json_body()
                    if not isinstance(payload, dict):
                        raise ValueError("OAuth client registration body must be an object")
                    self._write_json(201, auth.oauth.register_client(payload, self.headers))
                except Exception as exc:
                    self._write_json(400, {"error": "invalid_client_metadata", "error_description": str(exc)})
                return
            if auth.oauth.enabled and path == "/oauth/token":
                try:
                    form = self._read_form_body()
                    self._write_json(200, auth.oauth.exchange_token(form))
                except PermissionError as exc:
                    self._write_json(400, {"error": "invalid_grant", "error_description": str(exc)})
                except Exception as exc:
                    self._write_json(400, {"error": "invalid_request", "error_description": str(exc)})
                return
            if auth.oauth.enabled and path == "/oauth/authorize":
                form: dict[str, str] = {}
                try:
                    form = self._read_form_body()
                    _, redirect_url = auth.oauth.approve_authorization(form)
                    self.send_response(302)
                    self.send_header("Location", redirect_url)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                except PermissionError as exc:
                    form.pop("pin", None)
                    self._write_html(403, auth.oauth.authorize_page(form, self.headers, error=str(exc)))
                except Exception as exc:
                    self._write_json(400, {"error": "invalid_request", "error_description": str(exc)})
                return
            if not self._is_mcp_path(path):
                self._write_json(404, {"error": "not_found", "path": redact_path(path, auth)})
                return
            try:
                auth_result = auth.authorize(path, self.headers)
                payload = self._read_json_body()
                status, response = bridge.handle_json_rpc(payload, auth=auth_result, headers=self.headers)
                latency_ms = round((time.perf_counter() - started) * 1000, 3)
                bridge.audit.write("http_ok", path=redact_path(path, auth), auth_mode=auth_result.mode, status=status, latency_ms=latency_ms)
                if response is None:
                    self.send_response(status)
                    self._write_cors_headers()
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                else:
                    self._write_json(status, response)
            except AuthError as exc:
                bridge.audit.write("http_auth_error", path=redact_path(path, auth), message=str(exc))
                extra_headers = {"WWW-Authenticate": exc.challenge} if exc.challenge else None
                self._write_json(401, {"error": "unauthorized", "message": exc.message}, extra_headers=extra_headers)
            except Exception as exc:
                bridge.audit.write("http_error", path=redact_path(path, auth), error=type(exc).__name__, message=str(exc))
                self._write_json(400, {"error": type(exc).__name__, "message": str(exc)})

        def _is_mcp_path(self, path: str) -> bool:
            parts = [part for part in path.split("/") if part]
            return parts == ["mcp"] or (len(parts) == 2 and parts[0] == "mcp")

        def _read_json_body(self) -> Any:
            raw = self._read_body_bytes()
            if not raw:
                raise ValueError("empty request body")
            return json.loads(raw.decode("utf-8"))

        def _read_form_body(self) -> dict[str, str]:
            raw = self._read_body_bytes()
            if not raw:
                raise ValueError("empty request body")
            return parse_form_bytes(raw)

        def _read_body_bytes(self) -> bytes:
            length = int(self.headers.get("Content-Length") or "0")
            if length > MAX_BODY_BYTES:
                raise ValueError(f"body too large; max {MAX_BODY_BYTES} bytes")
            return self.rfile.read(length)

        def _write_json(self, status: int, payload: Any, *, extra_headers: dict[str, str] | None = None) -> None:
            body = json_bytes(payload)
            self.send_response(status)
            self._write_cors_headers()
            self.send_header("Content-Type", "application/json")
            for key, value in (extra_headers or {}).items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _write_html(self, status: int, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
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
    oauth = OAuthProvider.from_args(args)
    auth = AuthConfig.from_args(args, oauth)
    if not auth.allow_no_auth and not auth.bearer_tokens and not auth.path_secrets:
        raise SystemExit("Refusing to start without --secrets-file, --bearer-token/--bearer-token-env, --path-secret, or --allow-no-auth.")
    if oauth.enabled and oauth.require_for_tools and not oauth.owner_pin:
        raise SystemExit("Refusing to enable Alexandria OAuth without --oauth-owner-pin/--oauth-owner-pin-env or mcp_oauth_owner_pin in --secrets-file.")

    audit_path = None if args.audit_log == "" else Path(args.audit_log)
    client = DogfoodHttpClient(args.engine_base_url, timeout=args.engine_timeout)
    bridge = AlexandriaMcpBridge(client, AuditLogger(audit_path, log_payloads=args.log_payloads), oauth)
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
    parser.add_argument("--oauth-enabled", action="store_true")
    parser.add_argument("--require-oauth-for-tools", action="store_true")
    parser.add_argument("--oauth-owner-pin", default="")
    parser.add_argument("--oauth-owner-pin-env", default="ALEXANDRIA_MCP_OAUTH_PIN")
    parser.add_argument("--oauth-code-ttl-seconds", type=int, default=300)
    parser.add_argument("--oauth-token-ttl-seconds", type=int, default=86_400)
    parser.add_argument("--public-base-url", default="")
    return serve(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
