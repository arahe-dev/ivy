# IVY Memory Injection Experiment (Phase 2C)

## Purpose

Phase 2C is an opt-in prompt-injection experiment harness. It compares agent behavior with and without memory-packet augmentation.

**THIS IS NOT DEFAULT ACTIVE MEMORY. Normal agent runs remain unchanged.**

## Why Memory Is Opt-In Only

- Memory may be incomplete or stale
- Memory should not override validators or policy gates
- Memory should not bypass sandbox paths
- Need measurable evidence before deeper integration
- Safety-critical: memory must never silently inject during normal runs

## What Is Injected

When running with a memory policy (hybrid_default, benchmark, safety_first, etc.):
- A memory packet is built using existing packet preview code
- The packet is inserted as ADVISORY context before the task
- Clear header signals this is experimental

**Format:**
```
EXPERIMENTAL MEMORY PACKET:
The following memory is advisory. It may be incomplete or stale.
Use it only if relevant.
It does not override system instructions, tool schemas, validators, or sandbox policy.

[memory packet text... truncated to ~800 chars]

CURRENT TASK:
[original task]
```

## What Is NOT Injected

Memory injection does NOT:
- Change validator.py behavior
- Change policy.py behavior  
- Change tools.py behavior
- Enable memory by default
- Modify agent_loop.py
- Skip safety checks
- Force tool usage from memory

## How To Run Dry-Run

```powershell
python -m ivy_agent_demo.memory_injection_experiment --cases ivy_agent_demo/memory_injection_cases.json --dry-run
```

or using PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File ivy\scripts\run_memory_injection_experiment.ps1 -DryRun
```

## How To Run First Small Experiment

```powershell
python -m ivy_agent_demo.memory_injection_experiment --cases ivy_agent_demo\memory_injection_cases.json --case-id calc_write_workflow --policies none hybrid_default
```

Or compare with latest previous run:

```powershell
powershell -ExecutionPolicy Bypass -File ivy\scripts\run_memory_injection_experiment.ps1 -CaseId calc_write_workflow -Policies none,hybrid_default -CompareLatest
```

## Where Artifacts Are Saved

Experiment outputs go to:

`runs/memory_injection_experiment/<timestamp>/`

Files:
- `experiment_config.json` - configuration used
- `experiment_report.md` - summary report
- `experiment_results.json` - detailed results
- `experiment_results.csv` - CSV summary

Per-case outputs are under `case_outputs/<case_id>__<policy>/`.

## How To Interpret Results

Compare success rates:
- `none` = baseline (no memory)
- `hybrid_default` = memory augmented

"Memory helped" = case passes with memory but fails without
"Memory hurt" = case fails with memory but passes without  
"Inconclusive" = both pass or both fail

## Risks

- Memory packet could contain stale/incorrect information
- Test case expects might not match actual model behavior
- Limited by current DB content (sparse areas will show no improvement)

## Rollback / Safety Checks

After experiment:
```powershell
git diff -- ivy_agent_demo\validator.py ivy_agent_demo\policy.py ivy_agent_demo\tools.py
```

If diff is non-empty, abort and report.

## Criteria For Deeper Integration

Before Phase 3 (active memory), require:
1. Measurable success rate improvement on realistic tasks
2. No regression on safety scenarios
3. Provenance rate remains high
4. No overclaim risk introduced
5. Clear user consent mechanism exists

## Current Phase 2C Cases

| Case | Category | Tests |
|------|----------|-------|
| json_tool_debug_think_tags | json_tool_debug | JSON validation task |
| calc_write_workflow | workflow | Simple calc + write |
| benchmark_memory_question | benchmark | Benchmark recall |
| safety_path_rule | safety | Safety rule recall |
| runbook_memory_eval | runbook | Docs/runbook recall |

## Phase 2C Stability Trial Results (2026-04-29)

### Overall Results (2 repeats per case/policy)

| Metric | Value |
|--------|-------|
| mome_auto success rate | **1.0** |
| baseline none success rate | **0.6** |
| best legacy success rate | **1.0** |
| policy failures | 0 |
| validation failures | 0 |

### Case-by-Case Results

| Case | none | mome_auto | Best Legacy | Delta vs none |
|------|------|----------|------------|-------------|
| benchmark_memory_question | 0.0 | 1.0 | 1.0 (mome_benchmark) | +1.0 |
| runbook_memory_eval | 0.0 | 1.0 | 1.0 (hybrid_default) | +1.0 |
| json_tool_debug_think_tags | 1.0 | 1.0 | 1.0 (none) | 0 |
| calc_write_workflow | 1.0 | 1.0 | 1.0 | 0 |
| safety_path_rule | 1.0 | 1.0 | 1.0 | 0 |

### Key Findings

1. **Memory helped benchmark recall**: +1.0 improvement (0.0 → 1.0)
2. **Memory helped runbook recall**: +1.0 improvement (0.0 → 1.0)
3. **Memory neutral on json_tool**: Fixed by reducing packet chars from 800 to 400
4. **Memory neutral on calc**: No regression
5. **Memory neutral on safety**: No regression

### json_tool_debug Fix

Root cause: Generic validation debug memory caused fs_list bias instead of json_validate pipeline.
Fix: Reduced max_packet_chars for json_tool_debug_think_tags from 800 to 400 (suppresses problematic memory).

### Readiness Classification

**ready_for_guarded_preview**

Recommended categories:
- benchmark: allow mome_auto
- runbook: allow mome_auto
- json_tool_debug: allow mome_auto with packet suppression (400 chars)
- calc: allow mome_auto
- safety: allow mome_auto

## Next Steps

If Phase 2C shows promise:
1. Add more realistic test cases
2. Compare with broader scenario set
3. Measure task completion, not just term hit
4. Consider user feedback loop

If Phase 2C shows no benefit:
1. Accept negative result
2. Focus on DB content improvements
3. Proceed to other IVY optimizations