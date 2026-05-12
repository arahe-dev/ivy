# CP59 Plugin Scoreboard Refresh - 2026-05-11

## What Changed

Regenerated the committed plugin benchmark scoreboard after CP56-CP58 timing and latency work.

Updated:

```text
MoME-MoCE-Exp/docs/PLUGIN_BENCHMARK_SCOREBOARD.md
```

Command:

```powershell
python MoME-MoCE-Exp\scripts\run_context_memory_plugin_benchmark.py `
  --store MoME-MoCE-Exp\out\scoreboard_plugin_store `
  --source-root MoME-MoCE-Exp `
  --out-dir MoME-MoCE-Exp\out\plugin_benchmarks `
  --scoreboard-path MoME-MoCE-Exp\docs\PLUGIN_BENCHMARK_SCOREBOARD.md `
  --reset
```

## Result

- query count: `6`
- passed expectations: `6 / 6`
- avg query wall: `15.535 ms`
- avg plugin-reported wall: `15.401 ms`
- avg router latency: `2.478 ms`

Timing breakdown:

| Stage | Avg ms |
|---|---:|
| `prefilter` | `5.686` |
| `corpus` | `4.161` |
| `router_init` | `1.925` |
| `route` | `2.478` |
| `render` | `0.022` |
| `packet_write` | `0.941` |
| `total` | `15.401` |

## Why This Matters

The scoreboard now reflects the current optimized plugin path instead of the older pre-cache latency profile. This makes the docs useful as a quick health snapshot again.
