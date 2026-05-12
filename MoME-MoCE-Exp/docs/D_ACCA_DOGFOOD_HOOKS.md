# D-ACCA Dogfood Hooks

Date: 2026-05-12

This is the dashboard-free dogfood surface for D-ACCA. It exposes stable HTTP/JSON hooks that a ChatGPT App MCP wrapper, Kimi-built dashboard, local CLI, or another UI can call.

The service intentionally separates model-visible packet data from debug/proof data:

- `/packet` returns a small admitted context packet for the model.
- `/proof/{route_id}` returns richer route details for dashboards and debugging.
- `/hooks` returns the hook discovery contract.

## Start The Service

```powershell
cd C:\ivy-worktrees\d-acca-dd-acca-librarian-supercharge\MoME-MoCE-Exp
C:\ivy\MoME-MoCE-Exp\.venv\Scripts\python.exe scripts\d_acca_dogfood_service.py serve `
  --root out\d_acca_dogfood `
  --host 127.0.0.1 `
  --port 8766 `
  --candidate-backend indexed
```

Health:

```powershell
Invoke-RestMethod http://127.0.0.1:8766/health
```

Discover hooks:

```powershell
Invoke-RestMethod http://127.0.0.1:8766/hooks
```

## Hook Contract

| method | path | role |
|---|---|---|
| `GET` | `/health` | service status and memory count |
| `GET` | `/hooks` | machine-readable hook discovery |
| `GET` | `/memories?limit=50&offset=0` | list memory records |
| `GET` | `/search?q=...&limit=10&include_text=false` | debug memory search |
| `GET` | `/proof/{route_id}` | full stored route proof/debug record |
| `POST` | `/ingest` | add memory records |
| `POST` | `/packet` | create D-ACCA context packet |
| `POST` | `/feedback` | mark route useful/wrong/stale/missed/private |
| `POST` | `/forget` | remove memory records by id |

The HTTP server sends permissive local CORS headers and handles `OPTIONS` preflight so a local dashboard such as `http://localhost:5173` can call these hooks directly during dogfood work.

## Alexandria Frontend Hook Points

The React dashboard in `frontend/` should call only one local adapter layer:

- `src/hooks/useAlexandriaHooks.ts` owns `/health`, `/hooks`, `/memories`, `/packet`, `/proof/{route_id}`, and `/feedback`.
- UI components receive a derived view model instead of calling `fetch` directly.
- `VITE_ALEXANDRIA_API_BASE` can override the default `http://127.0.0.1:8766`.
- Empty live corpora must render as empty live state, not synthetic product examples.

The more durable boundary is now `alexandria_harness/`: it validates raw hook responses, enforces packet/proof invariants, and emits `dashboard_view.json` for frontends to consume or replay. See `docs/ALEXANDRIA_HARNESS.md`.

For immediate dogfooding without React/Vite, use `alexandria_simple/`:

```powershell
.\alexandria-simple.cmd start
```

It opens a plain static UI over the same hooks: health, hooks, memories, ingest, packet, proof, search, feedback, and forget.

## Ingest

```powershell
$body = @{
  items = @(
    @{
      id = "signal_phone_bridge"
      text = "Signal phone pings use the local Signal daemon plus the phone bridge."
      source_family = "runbook"
      authority = "high"
      tags = @("signal", "phone", "runbook")
      aliases = @("ping my phone", "signalcli", "phone bridge")
      helper_query = "Signal local push reply phone daemon Tailscale Web Push agent pings"
      guard_terms = @("signal")
      replay_match_terms = @("ping my phone", "signalcli")
      distillation_patterns = @(@("ping", "phone"), @("signalcli"))
    }
  )
} | ConvertTo-Json -Depth 8

Invoke-RestMethod http://127.0.0.1:8766/ingest -Method Post -ContentType "application/json" -Body $body
```

Minimum accepted input:

```json
{
  "text": "ACCA packets are compact admissible context packets with selected evidence and route proofs.",
  "tags": ["acca", "context"]
}
```

Useful record fields:

| field | notes |
|---|---|
| `text` | required memory text |
| `id` | optional stable id; service adds a content hash suffix |
| `source_family` | `doc_memory`, `runbook`, `workflow_trace`, `debug_failure`, `source_code`, etc. |
| `authority` | `high`, `medium`, `low`, or `decoy` |
| `staleness` | `current`, `stale`, `unknown`, or `decoy` |
| `tags` | short routing labels |
| `aliases` | user-language phrases that should hit this memory; if omitted, tags become the default aliases |
| `helper_query` | canonical helper-lazy query text |
| `guard_terms` | intent guard terms |
| `replay_match_terms` | exact terms distilled from real misses |
| `distillation_patterns` | all-terms-present phrase patterns |

## Packet

```powershell
$body = @{
  query = "how do I ping my phone from Codex with signalcli?"
  strategy = "helper-lazy"
  include_proof = $false
} | ConvertTo-Json

Invoke-RestMethod http://127.0.0.1:8766/packet -Method Post -ContentType "application/json" -Body $body
```

Strategies:

| strategy | behavior |
|---|---|
| `helper-lazy` | default dogfood path; uses alias/profile metadata to draft query bundles, then D-ACCA verifies evidence |
| `d-acca` | direct deterministic router without helper-lazy advice |

The model-facing part is:

```json
{
  "route_id": "route_...",
  "packet": {
    "role": "frontier_model_context_packet",
    "query": "...",
    "evidence": [],
    "constraints": []
  }
}
```

For a ChatGPT App or dashboard, pass only `packet` to the model by default. Fetch `/proof/{route_id}` only for inspection, route debugging, or a dashboard-only panel.

## Search

```powershell
Invoke-RestMethod "http://127.0.0.1:8766/search?q=signalcli%20phone&limit=5"
```

By default search returns previews, not full text. Add `include_text=true` only for trusted local dashboard views.

## Proof

```powershell
Invoke-RestMethod "http://127.0.0.1:8766/proof/route_..."
```

The proof record includes:

- selected ids;
- helper-lazy advice;
- route queries;
- route decisions;
- intent guard rejections;
- stored packet.

## Feedback

```powershell
$body = @{
  route_id = "route_..."
  rating = "useful"
  note = "Correct Signal phone memory."
} | ConvertTo-Json

Invoke-RestMethod http://127.0.0.1:8766/feedback -Method Post -ContentType "application/json" -Body $body
```

Valid ratings:

- `useful`
- `wrong`
- `missed`
- `stale`
- `private`
- `neutral`

## Forget

```powershell
$body = @{
  ids = @("signal_phone_bridge_abcd1234")
  reason = "User requested deletion"
} | ConvertTo-Json

Invoke-RestMethod http://127.0.0.1:8766/forget -Method Post -ContentType "application/json" -Body $body
```

`forget` removes active records from the service corpus and appends a tombstone event under the dogfood root.

## CLI Shortcuts

```powershell
C:\ivy\MoME-MoCE-Exp\.venv\Scripts\python.exe scripts\d_acca_dogfood_service.py hooks

C:\ivy\MoME-MoCE-Exp\.venv\Scripts\python.exe scripts\d_acca_dogfood_service.py ingest `
  --text "Signal pings use the local daemon and phone bridge." `
  --source manual `
  --tag signal `
  --tag phone

C:\ivy\MoME-MoCE-Exp\.venv\Scripts\python.exe scripts\d_acca_dogfood_service.py packet `
  --query "how do I ping my phone?" `
  --strategy helper-lazy
```

## ChatGPT App Fit

The hook split is deliberate:

- MCP tool result can return concise `packet` as structured content.
- Dashboard/widget-only metadata can fetch `/proof/{route_id}`.
- Import, feedback, and forget are state-changing tools and should be marked as write actions in MCP metadata.
- Search and packet are read-only from ChatGPT's perspective, though `/packet` still stores a route proof locally for observability.

Do not expose raw full logs to the model by default. Ingest them into records, then let D-ACCA admit the smallest useful packet.
