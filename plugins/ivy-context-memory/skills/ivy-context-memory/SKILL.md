---
name: ivy-context-memory
description: Use the local IVY ACCA context/memory sidecar to ingest repos/docs, remember safe notes, and query small audited context packets before Codex or OpenCode works on a task.
---

# IVY Context Memory

Use this skill when a task would benefit from repository-scale or long-running memory without stuffing raw history into the model prompt.

The sidecar stores memory outside the model context, compiles it through MoME/MoCE, and returns a small ACCA packet plus route proof.

If `store/policy/autoresearch_policy.json` exists, query defaults may use its tuned `max_prefilter_items` value.
The plugin keeps recall and route cost separate: `max_prefilter_items` controls the recall pool, while optional `router_candidate_k` caps final proof-router scoring.

## CLI

From `C:\ivy`:

```powershell
python .\plugins\ivy-context-memory\scripts\ivy_context_memory.py init
python .\plugins\ivy-context-memory\scripts\ivy_context_memory.py ingest --source-root C:\ivy --no-build
python .\plugins\ivy-context-memory\scripts\ivy_context_memory.py build
python .\plugins\ivy-context-memory\scripts\ivy_context_memory.py query --query "What context matters for this task?" --text
```

Preferred hot daemon bootstrap:

```powershell
powershell -ExecutionPolicy Bypass -File .\MoME-MoCE-Exp\scripts\start_context_memory_daemon.ps1
```

This starts the localhost sidecar if it is not already healthy, ingests the configured source root, calls `/warm`, and prints process cache counts. Use this before substantial Codex/OpenCode sessions when low-latency repeated memory queries matter.

Remember a safe result:

```powershell
python .\plugins\ivy-context-memory\scripts\ivy_context_memory.py remember `
  --text "CP28 showed contradiction-aware packets won final-answer A/B on conflict cases." `
  --source-path "root/notes/cp28.md" `
  --tag cp28 `
  --tag final-answer
```

For stale or conflicting memory, add `--staleness stale`, `--supersedes <id>`, or `--conflicts-with <id>` as needed.

Capture a session transcript and query the agent packet wrapper:

```powershell
python .\plugins\ivy-context-memory\scripts\ivy_context_memory.py session-ingest --json .\session.json
python .\plugins\ivy-context-memory\scripts\ivy_context_memory.py session-batch-ingest --json .\sessions.json
python .\plugins\ivy-context-memory\scripts\ivy_context_memory.py agent-hook --hook before_task --task "What context matters for this task?"
python .\plugins\ivy-context-memory\scripts\ivy_context_memory.py packet-v2 --query "What did the last verified session establish?"
python .\plugins\ivy-context-memory\scripts\ivy_context_memory.py freshness-scan
python .\plugins\ivy-context-memory\scripts\ivy_context_memory.py agent-doctor
```

## HTTP API

Start the local API:

```powershell
python .\plugins\ivy-context-memory\scripts\ivy_context_memory.py serve --host 127.0.0.1 --port 8768
```

Endpoints:

- `GET /health`
- `GET /status`
- `POST /ingest` with `{ "source_root": "C:\\ivy", "build": true }`
- `POST /remember` with `{ "text": "...", "source_path": "root/notes/x.md", "tags": ["tag"] }`
- `POST /session/ingest` with `{ "session_id": "...", "records": [{ "event_type": "decision", "text": "..." }] }`
- `POST /session/batch-ingest` with `{ "sessions": [{ "records": [...] }] }`
- `POST /agent/hook` with `{ "hook": "before_task", "task": "..." }`
- `POST /packet/v2` with `{ "query": "...", "hook": "before_task" }`
- `POST /freshness` with `{ "source_root": "...", "limit": 20 }`
- `POST /agent/doctor`
- `POST /query` with `{ "query": "...", "variant": "auto" }`
- `POST /build`
- `POST /warm` with `{ "queries": ["..."] }`

## MCP

When a client supports local MCP plugin tools, use the bundled `.mcp.json` server:

```powershell
python C:\ivy\plugins\ivy-context-memory\scripts\ivy_context_memory.py mcp
```

Available tools:

- `ivy_memory_query`
- `ivy_memory_remember`
- `ivy_memory_session_ingest`
- `ivy_memory_session_batch_ingest`
- `ivy_memory_agent_hook`
- `ivy_memory_freshness_scan`
- `ivy_memory_agent_doctor`
- `ivy_memory_ingest`
- `ivy_memory_build`
- `ivy_memory_warm`
- `ivy_memory_status`

Available resources:

- `ivy-memory://status`
- `ivy-memory://latest-packet`
- `ivy-memory://track-record`

Available prompts:

- `query_ivy_memory_before_task`
- `remember_verified_milestone`

## Agent Use

Before a deep task:

1. Start or reuse the daemon and warm it when available.
2. Query the sidecar for the current task.
3. Read only the returned packet text and selected evidence IDs.
4. Treat memory as advisory. User, system, developer, repo state, and tool safety still outrank memory.
5. After a verified milestone, call `remember` with a short factual note.
6. For longer sessions, call `ivy_memory_session_ingest` or `agent-hook --hook after_task` with only durable decisions, outcomes, failures, and test results.

Do not store secrets, API keys, credentials, or private path contents. The CLI rejects obvious secret-like note text.
