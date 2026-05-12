# CP56 Plugin Timing Breakdown - 2026-05-11

## What Changed

Added per-query timing instrumentation to the context-memory plugin and aggregated timing output to the plugin benchmark.

Updated:

```text
plugins/ivy-context-memory/scripts/ivy_context_memory.py
MoME-MoCE-Exp/scripts/run_context_memory_plugin_benchmark.py
MoME-MoCE-Exp/tests/test_ivy_context_memory_plugin.py
```

Each `query_store(...)` result now includes:

```json
{
  "wall_ms": 30.188,
  "timings_ms": {
    "prefilter": 17.531,
    "corpus": 4.134,
    "router_init": 3.297,
    "route": 2.745,
    "render": 0.022,
    "packet_write": 2.274,
    "total": 30.188
  }
}
```

The benchmark now aggregates these timings under:

```json
summary.avg_timings_ms
```

## Real Probe

Command:

```powershell
python MoME-MoCE-Exp\scripts\run_context_memory_plugin_benchmark.py `
  --store MoME-MoCE-Exp\out\cp56_probe_plugin_store `
  --source-root MoME-MoCE-Exp `
  --out-dir MoME-MoCE-Exp\out\cp56_probe_plugin_benchmarks `
  --reset
```

Result:

- passed expectations: `6 / 6`
- avg query wall: `30.34 ms`
- avg plugin-reported wall: `30.188 ms`
- avg router latency: `2.745 ms`

Timing breakdown:

| Stage | Avg ms |
|---|---:|
| `prefilter` | `17.531` |
| `corpus` | `4.134` |
| `router_init` | `3.297` |
| `route` | `2.745` |
| `render` | `0.022` |
| `packet_write` | `2.274` |
| `total` | `30.188` |

## Interpretation

The remaining wall-time cost is not the ACCA router. The largest cost is prefilter scoring over the persisted index. Next optimization should focus on reducing prefilter scan/sort work, likely by:

- caching item feature bonuses
- limiting feature-adjustment loops to scored candidate ids only
- avoiding repeated item text reconstruction inside `prefilter_feature_bonus`

## Verification

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ivy_context_memory_plugin.py tests\test_context_memory_regression_gate.py -q
python -m py_compile plugins\ivy-context-memory\scripts\ivy_context_memory.py MoME-MoCE-Exp\scripts\run_context_memory_plugin_benchmark.py
```

Result:

- `14 passed`
