# CP55 Wall-Time Regression Gate - 2026-05-11

## What Changed

Extended the combined context-memory regression gate with end-to-end wall-time budgets in addition to router latency budgets.

Updated:

```text
MoME-MoCE-Exp/scripts/run_context_memory_regression_gate.py
MoME-MoCE-Exp/tests/test_context_memory_regression_gate.py
MoME-MoCE-Exp/docs/AUTORESEARCH_REGRESSION_GATE.md
```

New checks:

- `mined_policy_wall_under_budget`
- `feature_wall_under_budget`
- `plugin_wall_under_budget`

## Why

CP51-CP53 optimized the plugin enough that router latency alone became too narrow. A regression could keep router latency low while reintroducing disk decode, tokenization, or packet-render overhead. CP55 makes that visible and gateable.

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
  --max-plugin-router-ms 15.0 `
  --max-wall-ms 50.0 `
  --max-plugin-wall-ms 40.0
```

Result:

- gate passed: `true`
- mined policy: `5 / 5`
- mined policy avg wall: `30.718 ms`
- feature eval: `5 / 5`
- feature avg wall: `29.088 ms`
- feature avg router: `2.153 ms`
- plugin benchmark: `6 / 6`
- plugin avg query wall: `29.071 ms`
- plugin avg router: `2.732 ms`

## Verification

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_context_memory_regression_gate.py tests\test_reranker_feature_eval.py tests\test_mined_case_policy_eval.py tests\test_ivy_context_memory_plugin.py -q
python -m py_compile MoME-MoCE-Exp\scripts\run_context_memory_regression_gate.py
```

Result:

- `17 passed`
