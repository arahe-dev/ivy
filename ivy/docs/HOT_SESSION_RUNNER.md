# Q4_K_M Hot Session Runner

`ivy/scripts/run_hot_session.ps1` is IVY's minimal hot-server runner for the Q4_K_M agent baseline.

It uses the validated llama.cpp pattern:
- one long-lived `llama-server`
- fixed `id_slot`
- `cache_prompt=true`
- stable static prefix first
- dynamic task appended last
- deterministic generation settings

## Files

- Manifest: `C:\ivy\ivy\manifests\q4km_hot_agent.yaml`
- Static prefix: `C:\ivy\ivy\prompts\static_prefix\ivy_agent_static_prefix.txt`
- Runner: `C:\ivy\ivy\scripts\run_hot_session.ps1`

## Basic Usage

```powershell
& C:\ivy\ivy\scripts\run_hot_session.ps1 `
  -ManifestPath C:\ivy\ivy\manifests\q4km_hot_agent.yaml `
  -DynamicTask "Explain whether IVY should use hot prompt reuse for Q4_K_M in 4 concise bullets." `
  -SlotId 0 `
  -OutputRunDirectory C:\ivy\ivy\runs\hot_session\example
```

For a task file:

```powershell
& C:\ivy\ivy\scripts\run_hot_session.ps1 `
  -ManifestPath C:\ivy\ivy\manifests\q4km_hot_agent.yaml `
  -DynamicTaskFile C:\path\to\task.txt `
  -SlotId 0 `
  -OutputRunDirectory C:\ivy\ivy\runs\hot_session\example
```

The first invocation starts `llama-server` if the manifest port is not live. Later invocations attach to the same live server and slot. By default, a server started by the runner is left running so future calls can reuse the prompt/KV cache. Use `-StopServerAfter` only for one-off tests.

## Artifacts

Each run directory contains:
- `request.json`
- `response.json`
- `output.txt`
- `result.json`
- `server_command.txt`
- `hot_session_log.md`
- `server.stdout.log` and `server.stderr.log` when the runner launched the server

`result.json` includes:
- model and server config
- slot id
- prompt and decode timing
- `cache_reuse_status`
- think/fence checks
- JSON parse status
- notes

## Cache Reuse Classification

Current v0 thresholds are hardcoded:
- `likely_hot_reuse`: `prompt_n <= 16` or `prompt_ms < 150`
- `partial_reuse`: `prompt_n` is less than 85% of the manifest cold baseline and greater than 16
- `cold_or_lost_reuse`: otherwise

These thresholds are intentionally simple. They should become manifest-configurable once IVY has more run history.

## Prompt Contract

Do not put changing data before the static prefix. The runner always sends:

```text
<stable static prefix>

DYNAMIC TASK:
<dynamic task>
```

Keep the static prefix byte-for-byte stable during a workflow. Put volatile data, observations, user task text, tool results, and timestamps in the dynamic suffix.

## Recommended Agent Path

Use the hot-session runner as the main Q4_K_M agent path when:
- a workflow has repeated project/tool policy context
- multiple turns share the same prefix
- tool-call cleanliness matters more than Q2/IQ2 raw speed

Track `prompt_n`, `prompt_ms`, and `cache_reuse_status` on every call. If reuse is lost, continue safely; do not depend on cache reuse for correctness.

## Validation

Validation folder:

`C:\ivy\ivy\runs\hot_session\validation_20260426_v2`

Commands run:

```powershell
& C:\ivy\ivy\scripts\run_hot_session.ps1 -ManifestPath C:\ivy\ivy\manifests\q4km_hot_agent.yaml -DynamicTask "Explain whether IVY should adopt Q4_K_M hot prompt reuse as the main agent path in 4 concise bullets." -SlotId 0 -OutputRunDirectory C:\ivy\ivy\runs\hot_session\validation_20260426_v2\01_cold

& C:\ivy\ivy\scripts\run_hot_session.ps1 -ManifestPath C:\ivy\ivy\manifests\q4km_hot_agent.yaml -DynamicTask "Explain whether IVY should adopt Q4_K_M hot prompt reuse as the main agent path in 4 concise bullets." -SlotId 0 -OutputRunDirectory C:\ivy\ivy\runs\hot_session\validation_20260426_v2\02_repeat_same

& C:\ivy\ivy\scripts\run_hot_session.ps1 -ManifestPath C:\ivy\ivy\manifests\q4km_hot_agent.yaml -DynamicTask "Give the exact request pattern IVY should use for Q4_K_M hot prompt reuse in 4 concise bullets." -SlotId 0 -OutputRunDirectory C:\ivy\ivy\runs\hot_session\validation_20260426_v2\03_changed_tail
```

Results:

| Run | prompt_n | prompt_ms | predicted_n | wall_ms | decode_tps | cache_reuse_status | Output cleanliness |
|---|---:|---:|---:|---:|---:|---|---|
| `01_cold` | 683 | 3263.614 | 119 | 7047.5 | 31.818 | `cold_or_lost_reuse` | no think tags, no fences |
| `02_repeat_same` | 4 | 77.850 | 119 | 3881.0 | 31.456 | `likely_hot_reuse` | no think tags, no fences |
| `03_changed_tail` | 514 | 1782.776 | 66 | 3925.4 | 31.173 | `partial_reuse` | no think tags, no fences |

The repeat request reduced prompt time by about 97.6%. The changed-tail request kept partial reuse and reduced prompt time by about 45.4% versus cold. This validates the v0 classification rules and supports adopting the runner as IVY's main Q4_K_M agent path.
