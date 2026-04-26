# IVY Phase 1 UI Debug Specs

This folder captures the local sandbox UI requirements and the Phase 1.2.1 hardening context in one place for debugging.

## Launch

```powershell
cd C:\ivy
powershell -ExecutionPolicy Bypass -File C:\ivy\scripts\run_phase1_ui.ps1
```

Open `http://127.0.0.1:8787`.

## Safety Boundary

- Localhost only: `127.0.0.1`.
- No shell execution.
- No network access.
- No delete operations.
- No app opening or computer-use.
- Reads are limited to `C:\ivy\ivy_agent_demo\sandbox_workspace`.
- Writes are limited to `C:\ivy\ivy_agent_demo\sandbox_workspace\out`.
- The UI uses the same `run_scenario` Phase 1 agent loop; it does not create a separate execution path.

## Chat Behavior

- The user sends one sandbox task per turn.
- The backend runs that task through the existing model/tool loop.
- The UI renders the resulting trace as chat-style messages:
  - user task,
  - proposed model tool calls,
  - tool results,
  - validation failures,
  - policy/progress guard blocks,
  - final answer.
- Each UI run writes artifacts under `C:\ivy\runs\phase1_agent_demo_ui\<timestamp>`.

## Phase 1.2.1 Progress Guard

The guard blocks non-progressing actions before execution:

- repeated same tool plus same arguments,
- repeated `fs_read` of an already-read file,
- extra `fs_read` after all required source files are available,
- repeated calls that would not add meaningful new state.

The guard injects corrective dynamic context instead of weakening validation or policy.

## Current Benchmark Baseline

- Latest completed Phase 1.2.1 run: `C:\ivy\runs\phase1_agent_demo\20260426_214559`
- Result: 25/25 pass
- Retries: 3
- Unsafe failures: 0
- Policy violations: 0
- Progress guard triggers: 2
- Cache reuse: 67 `partial_reuse`, 1 `cold_or_lost_reuse`
