# Alexandria MCP and ChatGPT App Setup

Alexandria now has a thin MCP bridge over the existing D-ACCA dogfood hooks.
The bridge is meant for two hosts:

- Codex: local streamable HTTP MCP at `http://127.0.0.1:8790/mcp` with bearer-token auth.
- ChatGPT Developer Mode: HTTPS MCP URL from a tunnel, using an unguessable path secret plus dogfood OAuth for tool calls.

The engine remains the existing deterministic D-ACCA/helper-lazy stack. The MCP bridge does not put an LLM inside base ACCA. It exposes import, recall, proof, search, and feedback hooks to agents that already know how to call MCP tools.

## MCP Contract

The bridge advertises `alexandria.mcp.contract.v0.2` from `initialize.serverInfo.contractVersion`.
Every tool descriptor includes an `outputSchema`, and every successful tool result includes:

- `schema_version: alexandria.mcp.tool_output.v0.2`
- `contract_version: alexandria.mcp.contract.v0.2`
- `tool: <tool name>`

Successful tool calls return the same JSON object in both `structuredContent` and the single text item in `content`. The text item is JSON-encoded for MCP clients that do not consume `structuredContent` directly.

## Local Data Layout

Runtime state is outside the git repo:

| Path | Purpose |
|---|---|
| `C:\ivy-data\alexandria\engine\` | D-ACCA memory corpus, routes, imports, feedback |
| `C:\ivy-data\alexandria\logs\` | MCP, hook, tunnel, and audit logs |
| `C:\ivy-data\alexandria\secrets\alexandria.secrets.json` | Local bearer token, ChatGPT path secret, and OAuth owner PIN |
| `C:\ivy-data\alexandria\pids\` | Background process ids |
| `C:\ivy-data\alexandria\chatgpt_mcp_url.txt` | Current tunnel URL for ChatGPT Developer Mode |

Secrets are generated locally by `alexandria-mcp.cmd setup`. Do not commit `C:\ivy-data\alexandria`.

## Dogfood OAuth

Alexandria exposes a small MCP-native OAuth dogfood flow in front of tool calls:

- `GET /.well-known/oauth-protected-resource`
- `GET /.well-known/oauth-authorization-server`
- `POST /oauth/register`
- `GET/POST /oauth/authorize`
- `POST /oauth/token`

The flow supports dynamic client registration, authorization-code + PKCE (`S256`), short-lived authorization codes, scoped bearer tokens, and per-tool `securitySchemes`. The local Codex bearer token still bypasses OAuth for developer workflows, while ChatGPT calls through the path-secret URL are challenged into OAuth before tools execute.

OAuth requests with no explicit scope default to `alexandria.read`; unsupported scopes are rejected rather than silently expanded. Write tools require `alexandria.write`.

This is a local lab authorization server, not a production identity provider. For a hosted or multi-user Alexandria app, replace it with an established OAuth 2.1 provider such as Auth0, Okta, Cognito, or another provider that publishes discovery metadata, supports PKCE, and issues tokens with the expected `resource`/audience and scopes.

The owner approval PIN is stored outside git in:

```text
C:\ivy-data\alexandria\secrets\alexandria.secrets.json
```

You can inspect it locally with:

```powershell
(Get-Content C:\ivy-data\alexandria\secrets\alexandria.secrets.json -Raw | ConvertFrom-Json).mcp_oauth_owner_pin
```

## Commands

From `C:\ivy-worktrees\d-acca-dd-acca-librarian-supercharge\MoME-MoCE-Exp`:

```powershell
.\alexandria-mcp.cmd setup
.\alexandria-mcp.cmd start
.\alexandria-mcp.cmd status
```

`setup` creates the data directories, generates secrets, and sets the user-level `ALEXANDRIA_MCP_TOKEN` and `ALEXANDRIA_MCP_OAUTH_PIN` environment variables. Restart Codex after setup so the process inherits them.

By default the dedicated Alexandria D-ACCA hooks listen on `127.0.0.1:8767`; the MCP bridge listens on `127.0.0.1:8790`. Port `8766` is intentionally avoided because older local dashboard experiments may already use it.

To expose the MCP endpoint to ChatGPT for a temporary developer-mode session:

```powershell
.\alexandria-mcp.cmd ngrok
```

Then use the URL stored in:

```text
C:\ivy-data\alexandria\chatgpt_mcp_url.txt
```

The launcher also still supports `.\alexandria-mcp.cmd tunnel` for Cloudflare quick tunnels. For current ChatGPT dogfood, prefer `ngrok` because it gives more repeatable tunnel management once the local ngrok account token is configured.

Stop everything:

```powershell
.\alexandria-mcp.cmd stop-tunnel
.\alexandria-mcp.cmd stop
```

## Codex Config

Codex supports streamable HTTP MCP servers with a bearer token sourced from an environment variable. Add this block to `C:\Users\arahe\.codex\config.toml`:

```toml
[mcp_servers.alexandria]
url = "http://127.0.0.1:8790/mcp"
bearer_token_env_var = "ALEXANDRIA_MCP_TOKEN"
enabled = true
tool_timeout_sec = 30
```

After restarting Codex, Alexandria tools should be available from new sessions while `alexandria-mcp.cmd start` is running.

## ChatGPT App Flow

OpenAI's current ChatGPT Developer Mode flow creates an app from a remote MCP server. Developer Mode supports SSE and streaming HTTP MCP, and supports OAuth, no-auth, or mixed auth. For this local dogfood setup we use an unguessable `/mcp/<secret>` path behind a temporary HTTPS tunnel plus MCP-native OAuth before tools execute. For a published or multi-user app, replace the local dogfood OAuth provider with a real identity provider.

Suggested prompt inside ChatGPT:

```text
Use the Alexandria app only. Extract the 12 most useful long-term memories from this chat. Do not invent anything. Call alexandria_import_memories with one item per memory, concise text, tags, source_family, authority, and why it matters.
```

In a new ChatGPT chat or in Codex:

```text
Use Alexandria to pick the 8 most relevant memories for this task, then answer using only the admitted packet evidence and cite memory ids when useful.
```

## Tools Exposed

| Tool | Mutates State | Purpose |
|---|---:|---|
| `alexandria_status` | No | Check hook and memory health |
| `alexandria_import_memories` | Yes | Save explicit selected memories from a chat/agent |
| `alexandria_pick_memories` | No | Build a D-ACCA context packet |
| `alexandria_search_memories` | No | Lightweight memory search |
| `alexandria_list_memories` | No | Inspect stored memories |
| `alexandria_get_proof` | No | Fetch why a packet was selected |
| `alexandria_feedback` | Yes | Record whether a packet was useful/wrong/stale |

No destructive `forget` tool is exposed through MCP yet. Keep deletion in the local hook service or a human-confirmed UI until the auth story is stronger.

For imports, pass one durable memory candidate per `items` entry. Prefer concise user-approved facts, project decisions, preferences, runbook notes, or constraints. Do not import raw transcript dumps, and do not invent memories. Include `project`, `source`, `tags`, `source_family`, `authority`, `staleness`, and `why` when those fields are known.

## Security Notes

- Codex uses bearer-token auth through `ALEXANDRIA_MCP_TOKEN`.
- ChatGPT Developer Mode uses an HTTPS tunnel plus a long random path secret, then OAuth-scoped bearer tokens for tool execution.
- The ChatGPT path-secret plus local OAuth mode is acceptable for private dogfood, not for production or public sharing.
- Production-grade "only I can use it" should use an established OAuth provider, verifying issuer, audience, expiry, and scopes on every request.
- Audit logs redact the path secret and avoid full payload logging by default.
- Imported memories are stored in `C:\ivy-data\alexandria\engine\dataset\corpus\corpus_items.jsonl`.

## References

- OpenAI Apps SDK MCP/auth docs: `https://developers.openai.com/apps-sdk/build/auth`
- OpenAI ChatGPT Developer Mode docs: `https://developers.openai.com/api/docs/guides/developer-mode`
- OpenAI Codex MCP config docs: `https://developers.openai.com/codex/mcp`
- ngrok docs: `https://ngrok.com/docs`
- Cloudflare Tunnel docs: `https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/`
