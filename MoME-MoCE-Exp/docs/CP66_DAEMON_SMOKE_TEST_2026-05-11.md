# CP66 Daemon Smoke Test - 2026-05-11

## What Changed

Added a persistent HTTP daemon smoke test:

```text
MoME-MoCE-Exp/scripts/run_context_memory_daemon_smoke.py
MoME-MoCE-Exp/tests/test_context_memory_daemon_smoke.py
MoME-MoCE-Exp/docs/DAEMON_SMOKE_TEST.md
```

The smoke test:

1. starts `ivy_context_memory.py serve` on `127.0.0.1` with a temporary port
2. waits for `/health`
3. calls `/ingest`
4. calls `/warm`
5. calls `/status`
6. calls `/query`
7. verifies warmed process-cache counts and selected evidence
8. terminates the daemon process

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
- corpus items: `786`
- index tokens: `8426`
- warmed queries: `4`
- query index cache entries: `1`
- item feature cache entries: `786`
- corpus item cache entries: `83`
- warm wall: `48.45 ms`
- post-warm query wall: `8.5 ms`
- post-warm router latency: `3.183 ms`

## Why This Matters

This is the first end-to-end daemon-level proof that the intended deployment shape works: keep the memory sidecar alive, warm caches once, then serve low-latency context packets through HTTP.

## Verification

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_context_memory_daemon_smoke.py tests\test_ivy_context_memory_plugin.py -q
python -m py_compile MoME-MoCE-Exp\scripts\run_context_memory_daemon_smoke.py
```

Result:

- `15 passed`
