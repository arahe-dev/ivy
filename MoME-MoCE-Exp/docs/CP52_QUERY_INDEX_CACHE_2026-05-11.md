# CP52 Query Index Cache - 2026-05-11

## What Changed

Added an in-process query-index cache to the context-memory plugin:

```text
plugins/ivy-context-memory/scripts/ivy_context_memory.py
```

The cache is keyed by resolved index path, file `mtime_ns`, and file size. When the query index is unchanged, repeated plugin queries reuse the decoded JSON payload instead of reading and parsing `corpus_index.json` on every call.

## Why

CP51 brought router latency down to about `2.5 ms`, but end-to-end plugin query wall time was still much higher because repeated calls were paying disk and JSON decode cost for the same index.

## Probe Result

Command:

```powershell
python MoME-MoCE-Exp\scripts\run_context_memory_plugin_benchmark.py `
  --store MoME-MoCE-Exp\out\cp52_probe_plugin_store `
  --source-root MoME-MoCE-Exp `
  --out-dir MoME-MoCE-Exp\out\cp52_probe_plugin_benchmarks `
  --reset
```

Result:

- passed expectations: `6 / 6`
- avg query wall: `30.241 ms`
- avg router latency: `2.54 ms`

Earlier CP51 probe:

- avg query wall: about `64.103 ms`
- avg router latency: about `2.43 ms`

## Regression Gate After Change

- gate passed: `true`
- mined policy: `5 / 5`
- feature eval: `5 / 5`
- plugin benchmark: `6 / 6`
- feature avg router latency: `2.149 ms`
- plugin avg router latency: `2.411 ms`

The tracked gate report is updated at:

```text
MoME-MoCE-Exp/docs/AUTORESEARCH_REGRESSION_GATE.md
```

## Verification

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_context_memory_regression_gate.py tests\test_reranker_feature_eval.py tests\test_mined_case_policy_eval.py tests\test_ivy_context_memory_plugin.py -q
python -m py_compile plugins\ivy-context-memory\scripts\ivy_context_memory.py
```

Result:

- `16 passed`
