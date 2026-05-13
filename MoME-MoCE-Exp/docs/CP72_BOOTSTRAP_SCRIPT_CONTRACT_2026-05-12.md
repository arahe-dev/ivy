# CP72 Bootstrap Script Contract - 2026-05-12

## What Changed

Added automated coverage for the daemon bootstrap PowerShell script.

Added:

```text
MoME-MoCE-Exp/tests/test_context_memory_bootstrap_script.py
```

The test verifies:

- `start_context_memory_daemon.ps1` parses through the PowerShell parser
- the script still contains `/warm`
- the script still supports `-StopAfterWarm`
- the script returns `process_caches`

## Why

CP70 made the daemon bootstrap operational. CP71 documented it. CP72 makes the script harder to break accidentally.

## Verification

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_context_memory_bootstrap_script.py tests\test_context_memory_daemon_smoke.py tests\test_ivy_context_memory_plugin.py -q
```

Result:

- `18 passed`
