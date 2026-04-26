# IVY Phase 1 Tool Simulation Demo

This document describes the first Windows-native end-to-end IVY tool loop demo:

- Q4_K_M hot-session model call
- strict JSON validator
- policy gate
- sandbox tool execution
- tool result injection
- final answer generation

## Architecture

Phase 1 components:

- `ivy_agent_demo/model_client.py`: llama.cpp client over `q4km_hot_agent` manifest
- `ivy_agent_demo/validator.py`: strict output contract validator
- `ivy_agent_demo/policy.py`: policy enforcement and path rules
- `ivy_agent_demo/tools.py`: six Phase 1 tools
- `ivy_agent_demo/agent_loop.py`: step loop, retry, artifacts, scenario runner
- `ivy_agent_demo/schemas.py`: tool schemas + prompt contract helpers

Phase 1.1 adds a stable in-process Phase 1 contract prefix before the dynamic task suffix. The stable prefix contains tool schemas, sandbox path examples, and safety constraints so those tokens remain byte-stable across scenario steps. Volatile state stays in the dynamic suffix.

Tool flow:

1. Build dynamic task prompt with constraints and tool schemas.
2. Send to llama-server with deterministic settings and `id_slot` + `cache_prompt=true`.
3. Validate output strictly:
   - must be exactly one JSON object
   - reject markdown fences
   - reject `<think>` tags
   - reject extra prose
   - reject unknown tools and invalid schema/enum/fields
4. If invalid, issue one repair attempt.
5. If valid tool call, apply policy gate.
6. If approved, execute tool in sandbox and inject result into next turn.
7. Stop on `{"final":"..."}` or safe-stop at max steps (5).

## How to Run

Prerequisites:

- Windows
- Python 3.11+
- llama.cpp `llama-server.exe`
- model file at `C:\bread_v2\gguf\Qwen3.6-35B-A3B-UD-Q4_K_M.gguf`
- manifest at `C:\ivy\ivy\manifests\q4km_hot_agent.yaml`

Run:

```powershell
& C:\ivy\scripts\run_phase1_demo.ps1 `
  -ManifestPath C:\ivy\ivy\manifests\q4km_hot_agent.yaml `
  -ScenariosPath C:\ivy\ivy_agent_demo\scenarios\scenarios.json `
  -RunsRoot C:\ivy\runs\phase1_agent_demo `
  -SandboxRoot C:\ivy\ivy_agent_demo\sandbox_workspace `
  -SlotId 0 `
  -RequestTimeoutSec 180 `
  -StopServerAfter
```

## Phase 1 Tools

Allowed tools:

1. `calc_eval`
   - args: `{"expr": string}`
   - arithmetic-only expression parser
2. `json_validate`
   - args: `{"json_text": string}`
   - syntax-only JSON validation
3. `fs_list`
   - args: `{"path": string}`
   - list only under sandbox root
4. `fs_read`
   - args: `{"path": string}`
   - read only under sandbox root, max 100 KB
5. `fs_write`
   - args: `{"path": string, "content": string, "mode": "overwrite"|"append"}`
   - write only under `sandbox_workspace/out`
6. `ask_user`
   - args: `{"question": string}`
   - simulated answer only for Phase 1

## Sandbox Boundaries

Workspace:

- `C:\ivy\ivy_agent_demo\sandbox_workspace\fixtures\`
- `C:\ivy\ivy_agent_demo\sandbox_workspace\out\`

Fixture files:

- `project.txt`
- `sample_data.json`
- `malformed.json`
- `notes.txt`

Enforced restrictions:

- no shell execution
- no network
- no delete operations
- no reads outside sandbox root
- no writes outside sandbox/out

## Scenarios

Defined scenarios in `C:\ivy\ivy_agent_demo\scenarios\scenarios.json`:

1. `calc_write`
2. `read_summarize`
3. `list_ambiguous`
4. `json_validate_report`
5. `unsafe_delete`

## Artifacts

Per run:

- `C:\ivy\runs\phase1_agent_demo\<timestamp>\phase1_results.json`

Per scenario directory:

- `dynamic_task.txt`
- `model_request_*.json`
- `model_response_*.json`
- `validation_*.json`
- `tool_call_*.json`
- `tool_result_*.json`
- `final_answer.txt`
- `run_summary.json`

## Safety Model

Core rule:

- Model output is never authority.
- Only validated and policy-approved tool calls execute.

Validation blocks:

- malformed JSON
- markdown-fenced output
- think tags
- extra prose / non-contract shape
- unknown tools
- missing required fields
- extra fields
- invalid enum values
- unsafe paths

Policy blocks:

- network intent
- delete intent
- path escape
- write outside `out`
- unsafe scenario tool misuse (unsafe scenario must resolve via `ask_user` or refusal)

## Phase 1.1 Hardening

Changes made after the first Phase 1 run:

- Moved tool schemas, output contract, path examples, and safety constraints into a stable Phase 1.1 prefix inside the agent loop.
- Kept volatile task data, tool results, validation failures, and step state in the dynamic suffix.
- Added explicit path examples:
  - good `fs_list` path: `fixtures`
  - good `fs_read` path: `fixtures/project.txt`
  - good `fs_write` path: `out/report.txt`
  - bad path: `C:\ivy\...`
  - bad path: `..\outside.txt`
  - bad path: `sandbox_workspace/fixtures`
- Sanitized injected tool results so the model sees relative sandbox paths rather than host absolute paths.
- Updated simulated `ask_user` responses so ambiguity prompts stop and ask the user instead of proceeding to inspect files.
- Updated unsafe scenario scoring to accept a direct safe refusal as successful behavior.

Result:

- `list_ambiguous` now passes.
- Cache reuse improved from all `cold_or_lost_reuse` to all `partial_reuse` in the representative Phase 1.1 run.
- No sandbox policy was loosened.

## Intentionally Not Implemented

Out of scope for Phase 1:

- Hermes install/integration
- WSL2/Docker
- browser automation
- messaging integrations
- subagents
- arbitrary shell execution
- external network calls
- destructive filesystem actions
