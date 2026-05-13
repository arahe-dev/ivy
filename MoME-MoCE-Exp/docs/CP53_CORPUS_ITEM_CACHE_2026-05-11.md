# CP53 Corpus Item Cache - 2026-05-11

## What Changed

Added an in-process cache for converted `CorpusItem` objects inside the context-memory plugin:

```text
plugins/ivy-context-memory/scripts/ivy_context_memory.py
```

The cache key uses:

- item id
- provenance source hash
- text length

This avoids repeated tokenization and `Counter` construction for selected raw items during repeated plugin queries.

## Probe Result

Command:

```powershell
python MoME-MoCE-Exp\scripts\run_context_memory_plugin_benchmark.py `
  --store MoME-MoCE-Exp\out\cp53_probe_plugin_store `
  --source-root MoME-MoCE-Exp `
  --out-dir MoME-MoCE-Exp\out\cp53_probe_plugin_benchmarks `
  --reset
```

Result:

- passed expectations: `6 / 6`
- avg query wall: `28.416 ms`
- avg router latency: `2.548 ms`

Earlier CP52 probe:

- avg query wall: `30.241 ms`
- avg router latency: `2.54 ms`

This is a smaller win than CP52, but it removes another repeated CPU cost from the hot plugin process.

## Regression Gate

The gate still passes after the cache:

- mined policy: `5 / 5`
- feature eval: `5 / 5`
- plugin benchmark: `6 / 6`
- plugin avg router latency: under the `15 ms` full-plugin budget

## Verification

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_context_memory_regression_gate.py tests\test_reranker_feature_eval.py tests\test_mined_case_policy_eval.py tests\test_ivy_context_memory_plugin.py -q
python -m py_compile plugins\ivy-context-memory\scripts\ivy_context_memory.py
```

Result:

- `16 passed`
