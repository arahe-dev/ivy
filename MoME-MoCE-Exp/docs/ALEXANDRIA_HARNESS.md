# Alexandria Harness

Date: 2026-05-13

The Alexandria harness is the contract boundary between the D-ACCA dogfood hook service and any website, ChatGPT App, local dashboard, or Kimi-built frontend.

It exists because the frontend should not infer product truth directly from raw engine JSON. The harness validates the engine response, checks route/proof invariants, then emits a stable dashboard view model.

## Boundary

```text
website action/query
  -> harness request validation
  -> D-ACCA hook service
  -> raw packet/proof/memory JSON
  -> harness contract checks
  -> dashboard_view.json
  -> website rendering
```

The model-visible payload remains separate:

- `packet_response.packet` is the model packet.
- `proof_response.route_proof` is dashboard/debug state.
- `dashboard_view.json` is UI state, not a prompt.

## Why It Matters

Alexandria is supposed to prove why memory was admitted. A pretty frontend that fills cards from partial, stale, mocked, or malformed data would break that promise. The harness makes those failures explicit.

The harness enforces:

- packet evidence IDs match `selected_ids`;
- packet route IDs match stored route proof IDs;
- artifact errors are surfaced as contract failures;
- forbidden or secret-like evidence cannot silently enter the model packet;
- stale/decoy evidence is warned on;
- empty corpora render as truly empty state, not demo metrics.

## Files

| path | purpose |
|---|---|
| `alexandria_harness/engine_client.py` | stdlib HTTP client plus in-process test adapter |
| `alexandria_harness/validate.py` | contract and invariant checks |
| `alexandria_harness/transform.py` | raw engine JSON to dashboard view model |
| `alexandria_harness/scenario_runner.py` | scenario seeding, packet run, proof fetch, artifact write |
| `alexandria_harness/contracts/*.schema.json` | documented packet and dashboard view shapes |
| `tests/test_alexandria_harness.py` | focused boundary tests |

## Run Against A Live Hook Service

Start the service:

```powershell
cd C:\ivy-worktrees\d-acca-dd-acca-librarian-supercharge\MoME-MoCE-Exp
C:\ivy\MoME-MoCE-Exp\.venv\Scripts\python.exe scripts\d_acca_dogfood_service.py serve `
  --root out\d_acca_dogfood `
  --host 127.0.0.1 `
  --port 8766 `
  --candidate-backend indexed
```

Run the harness:

```powershell
C:\ivy\MoME-MoCE-Exp\.venv\Scripts\python.exe -m alexandria_harness.scenario_runner `
  --base-url http://127.0.0.1:8766 `
  --scenario answerable `
  --output out\alexandria_harness
```

Artifacts are written under:

```text
out/alexandria_harness/<scenario>/
  request.json
  ingest_response.json
  snapshot.json
  packet_response.json
  proof_response.json
  dashboard_view.json
  report.json
```

## Scenarios

```powershell
C:\ivy\MoME-MoCE-Exp\.venv\Scripts\python.exe -m alexandria_harness.scenario_runner --list
```

Current scenarios:

- `empty`: no ingested memories; verifies real empty UI state.
- `answerable`: seeded Alexandria harness facts; should admit relevant evidence.
- `stale_conflict`: stale low-authority draft plus current high-authority policy.
- `safety_block`: secret-like forbidden evidence case for safety contract testing.

## Test

```powershell
C:\ivy\MoME-MoCE-Exp\.venv\Scripts\python.exe -m pytest tests\test_alexandria_harness.py -q
```

Current focused result:

```text
4 passed
```

## Next Integration Step

The React dashboard should eventually consume this harness output instead of duplicating contract logic in `frontend/src/hooks/useAlexandriaHooks.ts`.

The clean frontend API is:

```text
refresh/live run -> dashboard_view.json
model use       -> dashboard_view.model_packet
debug display   -> dashboard_view.dashboard_proof
UI display      -> dashboard_view.dashboard
```
