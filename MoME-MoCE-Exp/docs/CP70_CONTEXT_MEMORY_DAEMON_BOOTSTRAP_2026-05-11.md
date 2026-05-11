# CP70 Context Memory Daemon Bootstrap - 2026-05-11

## What Changed

Added a Windows PowerShell bootstrap for the context-memory daemon:

```text
MoME-MoCE-Exp/scripts/start_context_memory_daemon.ps1
```

The script:

1. checks whether the daemon is already healthy
2. starts `ivy_context_memory.py serve` on localhost when needed
3. optionally ingests/builds the source root
4. calls `/warm`
5. returns health, ingest, warm, and process-cache status as JSON

It supports `-StopAfterWarm` so the bootstrap can be tested without leaving a background process running.

## Real Run

Command:

```powershell
powershell -ExecutionPolicy Bypass `
  -File MoME-MoCE-Exp\scripts\start_context_memory_daemon.ps1 `
  -Port 18768 `
  -Store C:\ivy\MoME-MoCE-Exp\out\context_memory_daemon_bootstrap_store `
  -StopAfterWarm
```

Result:

- `ok: true`
- URL: `http://127.0.0.1:18768`
- started by script: `true`
- corpus items: `807`
- warmed queries: `4`
- query index cache entries: `1`
- item feature cache entries: `807`
- corpus item cache entries: `80`
- warm wall: `50.562 ms`
- `-StopAfterWarm` successfully stopped the test daemon

## Verification

Commands:

```powershell
$errors=$null
[System.Management.Automation.Language.Parser]::ParseFile(
  'C:\ivy\MoME-MoCE-Exp\scripts\start_context_memory_daemon.ps1',
  [ref]$null,
  [ref]$errors
) | Out-Null
if ($errors.Count) { exit 1 }
```

Result:

- PowerShell parser: `ok`
