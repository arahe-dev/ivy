# IVY Phase 1 Agent Demo - Session Summary

## What We Built

A Windows-native tool-loop agent demo using Q4_K_M through llama.cpp, inspired by Hermes Agent architectures but built natively without WSL2, Docker, or Hermes installation.

## Files to Commit

### Core Agent Implementation
```
ivy_agent_demo/__init__.py                 # Package init
ivy_agent_demo/agent_loop.py              # Main agent loop with validator, policy, retry
ivy_agent_demo/model_client.py             # llama-server client with hot-session support
ivy_agent_demo/validator.py              # Strict JSON validation
ivy_agent_demo/policy.py                # Policy gate for sandbox paths
ivy_agent_demo/tools.py                 # 6 Phase 1 tools (calc_eval, json_validate, fs_list, fs_read, fs_write, ask_user)
ivy_agent_demo/schemas.py                # Tool schemas
```

### Test Scenarios
```
ivy_agent_demo/scenarios/scenarios.json    # 5 test scenarios
ivy_agent_demo/sandbox_workspace/fixtures/project.txt
ivy_agent_demo/sandbox_workspace/fixtures/sample_data.json
ivy_agent_demo/sandbox_workspace/fixtures/malformed.json
ivy_agent_demo/sandbox_workspace/fixtures/notes.txt
ivy_agent_demo/sandbox_workspace/out/
```

### Runner
```
scripts/run_phase1_demo.ps1                # PowerShell runner
```

### Documentation
```
docs/PHASE1_AGENT_DEMO.md                # Phase 1.1 architecture docs
docs/results/PHASE1_AGENT_DEMO_RESULTS.md # 5/5 pass, all partial_reuse results
docs/results/PHASE1_1_DECODE_DIAGNOSIS.md # decode_tps diagnosis
docs/HERMES_TO_IVY_WINDOWS_AGENT_DESIGN.md   # Research/design (pre-existing)
docs/IVY_BASIC_SKILLS_25.md                 # 25 skills design (pre-existing)
docs/IVY_SIMULATION_ENVIRONMENTS.md         # Simulation envs (pre-existing)
```

### Run Artifacts (generated, may want to exclude)
```
runs/phase1_agent_demo/20260426_185159/   # Phase 1.1 successful run (5/5)
```

## Key Changes Made

### Phase 1 → Phase 1.1 Hardening

1. **Stable Prompt Prefix**: Moved tool schemas, path examples, and safety constraints into a stable Phase 1.1 prefix so those tokens stay byte-stable across scenario steps. This improved cache reuse from all `cold_or_lost_reuse` to all `partial_reuse`.

2. **Sanitized Tool Results**: Tool results injected into the model now show relative sandbox paths instead of absolute Windows paths (e.g., `fixtures/project.txt` instead of `C:\ivy\ivy_agent_demo\sandbox_workspace\fixtures\project.txt`).

3. **Better ask_user Simulation**: Ambiguous file-selection tasks now stop and ask instead of proceeding to inspect files.

4. **Fixed Unsafe Scenario Scoring**: Direct safe refusals are now recognized as successful behavior.

5. **No Policy Weakening**: All sandbox restrictions preserved—no shell, no network, no delete, no writes outside `out/`.

## Final Results

| Metric | Phase 1 | Phase 1.1 |
|-------|---------|-----------|
| Scenario pass rate | 4/5 | **5/5** |
| Retry count | 1 | **0** |
| Unsafe delete safe | true | **true** |
| Cache reuse | `{"cold_or_lost_reuse": 15}` | **`{"partial_reuse": 13}`** |
| Average prompt_ms | 6322.589 | **2854.247** (2.2x faster) |
| Average decode_tps | 26.372 | 9.427* |

*Decode_tps drop is NOT a model regression—see `docs/results/PHASE1_1_DECODE_DIAGNOSIS.md` for full analysis. It's output-length and llama-server batch variance, not model slowdown.

## Why It Works

The agent loop:
1. Static prefix (tools, constraints, path examples) → stable for cache
2. Dynamic suffix (task, tool results) → varies per step
3. Model output → strict JSON validation
4. Policy gate → sandbox enforcement
5. Approved tool calls → real execution in sandbox
6. Tool results → injected back to model
7. Repeat until final answer or max steps

## Safety Guarantees

- No shell execution
- No network access
- No delete actions allowed
- Reads limited to sandbox_workspace root
- Writes limited to sandbox_workspace/out
- Model output never authority—validated and approved tool calls only

## Recommended Commit Message

```
feat: IVY Phase 1.1 tool-loop agent demo with 5/5 pass rate

- Add Windows-native agent loop with llama.cpp Q4_K_M backend
- Implement strict JSON validator + policy gate
- Add 6 sandbox tools (calc_eval, json_validate, fs_list, fs_read, fs_write, ask_user)
- Add stable prompt prefix for hot-session cache reuse
- Sanitize tool results to use relative paths
- Score unsafe scenarios as pass on direct refusal

Results:
- 5/5 scenarios pass
- 0 retries needed  
- All cache classified as partial_reuse
- prompt_ms 2.2x faster than Phase 1
- No policy weakening
```

## Optional: Files to Exclude from Commit

If desired, add to `.gitignore`:
```
runs/
ivy/runs/
```

## What NOT to Do After Commit

- Do NOT modify llama.cpp
- Do NOT change the GGUF model file
- Do NOT weaken sandbox policy
- Do NOT add shell/network/delete tools in Phase 1
- Do NOT connect real browser or messaging yet