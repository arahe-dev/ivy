# CP50 Context Memory Regression Gate - 2026-05-11

## What Changed

Added a single regression gate for the context-memory plugin and autoresearch loop:

```text
MoME-MoCE-Exp/scripts/run_context_memory_regression_gate.py
```

The gate runs:

- mined hard-case policy eval across `max_prefilter_items` candidates
- deterministic reranker feature eval
- optional guarded policy promotion
- full plugin benchmark on a reset plugin store

It writes:

```text
MoME-MoCE-Exp/docs/AUTORESEARCH_REGRESSION_GATE.md
```

## Budgets

The gate tracks two latency budgets because the workloads are not equivalent:

- mined/feature eval budget: `5.0 ms`
- full plugin benchmark budget: `15.0 ms`

The strict sub-5 ms target remains the hot router target. The full plugin benchmark currently runs over a much larger source corpus and is tracked separately so latency regressions are still visible.

## Real Run

Command:

```powershell
python MoME-MoCE-Exp\scripts\run_context_memory_regression_gate.py `
  --store MoME-MoCE-Exp\out\autoresearch_loop\memory_store `
  --plugin-store MoME-MoCE-Exp\out\regression_gate_plugin_store `
  --cases MoME-MoCE-Exp\docs\AUTORESEARCH_MINED_EVAL_CASES.json `
  --source-root MoME-MoCE-Exp `
  --out MoME-MoCE-Exp\docs\AUTORESEARCH_REGRESSION_GATE.md `
  --max-router-ms 5.0 `
  --max-plugin-router-ms 15.0
```

Result:

- gate passed: `true`
- mined policy: `5 / 5`
- feature eval: `5 / 5`
- feature winner: `code_penalty`
- feature avg router latency: `2.043 ms`
- plugin benchmark: `6 / 6`
- plugin avg router latency: `11.327 ms`

## Verification

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_context_memory_regression_gate.py tests\test_reranker_feature_eval.py tests\test_mined_case_policy_eval.py tests\test_ivy_context_memory_plugin.py -q
python -m py_compile MoME-MoCE-Exp\scripts\run_context_memory_regression_gate.py
```

Result:

- `16 passed`

## Why This Matters

The project now has a repeatable, one-command health gate that combines correctness, latency, feature-profile selection, and plugin-level behavior. It also makes the current latency split explicit: hot mined routing is around `2 ms`, while the larger full-plugin benchmark sits around `11 ms`.
