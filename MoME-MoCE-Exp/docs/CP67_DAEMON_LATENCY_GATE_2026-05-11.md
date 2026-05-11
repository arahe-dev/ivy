# CP67 Daemon Latency Gate - 2026-05-11

## What Changed

Turned the HTTP daemon smoke test into a thresholded daemon latency gate.

Updated:

```text
MoME-MoCE-Exp/scripts/run_context_memory_daemon_smoke.py
MoME-MoCE-Exp/tests/test_context_memory_daemon_smoke.py
MoME-MoCE-Exp/docs/DAEMON_SMOKE_TEST.md
```

New default budgets:

- post-warm query wall: `15 ms`
- post-warm router latency: `5 ms`

The daemon smoke now checks:

- health endpoint works
- ingest produced corpus
- warmup ran
- query-index cache is warm
- item-feature cache is warm
- corpus-item cache is warm
- query selected evidence
- post-warm query wall is under budget
- router latency is under budget

## Real Run

Command:

```powershell
python MoME-MoCE-Exp\scripts\run_context_memory_daemon_smoke.py `
  --store MoME-MoCE-Exp\out\daemon_smoke_store `
  --source-root MoME-MoCE-Exp `
  --out MoME-MoCE-Exp\docs\DAEMON_SMOKE_TEST.md
```

Result:

- passed: `true`
- corpus items: `794`
- warmed queries: `4`
- item feature cache entries: `794`
- corpus item cache entries: `83`
- warm wall: `46.441 ms`
- post-warm query wall: `9.865 ms`
- post-warm router latency: `3.257 ms`

## Verification

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_context_memory_daemon_smoke.py tests\test_ivy_context_memory_plugin.py -q
python -m py_compile MoME-MoCE-Exp\scripts\run_context_memory_daemon_smoke.py
```

Result:

- `16 passed`
