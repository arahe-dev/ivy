# CP51 Plugin Default Prefilter Budget - 2026-05-11

## What Changed

Changed the context-memory plugin's no-policy default prefilter width from `192` to `32`:

```text
plugins/ivy-context-memory/scripts/ivy_context_memory.py
```

Runtime policy still overrides this value when `store/policy/autoresearch_policy.json` exists.

## Why

The autoresearch loop and mined hard-case eval repeatedly selected `max_prefilter_items=32` as the best correctness/latency point. The full plugin regression store did not have that runtime policy, so it fell back to the older wider `192` candidate budget and averaged around `11 ms` router latency.

## Real Gate After Change

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
- plugin benchmark: `6 / 6`
- feature avg router latency: `2.137 ms`
- plugin avg router latency: `2.515 ms`

## Delta

The full plugin benchmark moved from about `11.3 ms` to `2.5 ms` average router latency by using the same default candidate budget that autoresearch had already validated.

## Verification

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_context_memory_regression_gate.py tests\test_reranker_feature_eval.py tests\test_mined_case_policy_eval.py tests\test_ivy_context_memory_plugin.py -q
python -m py_compile plugins\ivy-context-memory\scripts\ivy_context_memory.py
```

Result:

- `16 passed`
