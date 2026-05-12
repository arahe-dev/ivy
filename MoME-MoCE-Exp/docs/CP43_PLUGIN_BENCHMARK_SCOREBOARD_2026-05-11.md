# CP43 Plugin Benchmark Scoreboard - 2026-05-11

## What Changed

The plugin benchmark harness can now update a stable committed scoreboard:

```powershell
python MoME-MoCE-Exp\scripts\run_context_memory_plugin_benchmark.py `
  --reset `
  --scoreboard-path MoME-MoCE-Exp\docs\PLUGIN_BENCHMARK_SCOREBOARD.md
```

Generated scoreboard:

```text
MoME-MoCE-Exp/docs/PLUGIN_BENCHMARK_SCOREBOARD.md
```

## Latest Scoreboard

- Query count: `6`
- Passed expectations: `6 / 6`
- Avg query wall: `105.959 ms`
- Avg router latency: `12.401 ms`

The scoreboard includes:

- direct CP28 note retrieval
- CP33 MCP memory retrieval
- CP29 generated-output ingestion memory
- CP32 build-cache memory
- CP42 stale/current conflict behavior
- live Bitcoin price abstention

## Verification

Commands:

```powershell
python -m py_compile MoME-MoCE-Exp\scripts\run_context_memory_plugin_benchmark.py
.\.venv\Scripts\python.exe -m pytest tests\test_ivy_context_memory_plugin.py -q
```

Result:

- `11 passed`

## Why This Matters

Timestamped `out/` reports are good for raw run artifacts, but a committed scoreboard gives future agents a stable reference point without searching ignored output directories.
