# CP60 Hot Query Benchmark - 2026-05-11

## What Changed

Added a repeated hot-query benchmark for the context-memory plugin:

```text
MoME-MoCE-Exp/scripts/run_context_memory_hot_query_benchmark.py
MoME-MoCE-Exp/tests/test_context_memory_hot_query_benchmark.py
MoME-MoCE-Exp/docs/HOT_QUERY_BENCHMARK.md
```

The benchmark first sets up the same plugin benchmark store, then runs the core six queries repeatedly in the same Python process. This measures the behavior that matters for a long-running Codex/OpenCode/MCP sidecar.

## Real Run

Command:

```powershell
python MoME-MoCE-Exp\scripts\run_context_memory_hot_query_benchmark.py `
  --store MoME-MoCE-Exp\out\hot_query_benchmark_store `
  --source-root MoME-MoCE-Exp `
  --out MoME-MoCE-Exp\docs\HOT_QUERY_BENCHMARK.md `
  --passes 3 `
  --reset
```

Result:

| Pass | Avg wall ms | Avg plugin wall ms | Avg router ms | Prefilter ms | Corpus ms |
|---:|---:|---:|---:|---:|---:|
| 1 | `21.992` | `21.856` | `2.474` | `12.809` | `3.689` |
| 2 | `7.669` | `7.546` | `2.546` | `1.979` | `0.018` |
| 3 | `7.853` | `7.726` | `2.454` | `2.288` | `0.021` |

## Interpretation

The plugin is now materially different in cold-ish versus hot repeated use:

- First repeated pass still pays feature and item cache warmup.
- Subsequent passes run around `7.5-7.7 ms` plugin-reported wall time.
- Router latency remains around `2.5 ms`.
- Corpus conversion effectively disappears after the item cache is warm.

This supports the intended deployment shape: a long-running memory/context sidecar used by Codex/OpenCode, not repeated one-shot process startup.

## Verification

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_context_memory_hot_query_benchmark.py tests\test_ivy_context_memory_plugin.py -q
python -m py_compile MoME-MoCE-Exp\scripts\run_context_memory_hot_query_benchmark.py
```

Result:

- `13 passed`
