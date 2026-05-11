# CP57 Prefilter Feature Cache - 2026-05-11

## What Changed

Added cached per-item prefilter feature metadata in the context-memory plugin.

Updated:

```text
plugins/ivy-context-memory/scripts/ivy_context_memory.py
```

The cache stores:

- lowercased tags
- checkpoint numbers present in the item search text
- source family

This avoids rebuilding full item search text and rerunning checkpoint extraction for repeated feature-bonus scoring.

## Why

CP56 showed the prefilter stage was the dominant wall-time cost:

| Stage | CP56 Avg ms |
|---|---:|
| `prefilter` | `17.531` |
| `total` | `30.188` |

## Probe Result

Command:

```powershell
python MoME-MoCE-Exp\scripts\run_context_memory_plugin_benchmark.py `
  --store MoME-MoCE-Exp\out\cp57_probe_plugin_store `
  --source-root MoME-MoCE-Exp `
  --out-dir MoME-MoCE-Exp\out\cp57_probe_plugin_benchmarks `
  --reset
```

Result:

- passed expectations: `6 / 6`
- avg query wall: `18.715 ms`
- avg plugin-reported wall: `18.512 ms`
- avg router latency: `2.769 ms`

Timing breakdown:

| Stage | Avg ms |
|---|---:|
| `prefilter` | `8.239` |
| `corpus` | `4.304` |
| `router_init` | `1.975` |
| `route` | `2.769` |
| `render` | `0.042` |
| `packet_write` | `0.933` |
| `total` | `18.512` |

## Regression Gate After Change

- gate passed: `true`
- mined policy: `5 / 5`
- feature eval: `5 / 5`
- plugin benchmark: `6 / 6`
- plugin avg query wall: `17.054 ms`
- plugin avg router latency: `2.617 ms`

## Interpretation

The optimization moved the dominant stage without changing router decisions. The remaining largest wall contributors are now prefilter scoring, corpus conversion, and route execution, with packet rendering effectively negligible.

## Verification

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ivy_context_memory_plugin.py tests\test_context_memory_regression_gate.py tests\test_reranker_feature_eval.py -q
python -m py_compile plugins\ivy-context-memory\scripts\ivy_context_memory.py
```

Result:

- `16 passed`
