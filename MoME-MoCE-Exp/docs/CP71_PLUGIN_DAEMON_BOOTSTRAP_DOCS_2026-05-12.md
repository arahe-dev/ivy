# CP71 Plugin Daemon Bootstrap Docs - 2026-05-12

## What Changed

Updated the plugin README and skill instructions to describe the daemon-first hot path.

Updated:

```text
plugins/ivy-context-memory/README.md
plugins/ivy-context-memory/skills/ivy-context-memory/SKILL.md
```

Added coverage for:

- `MoME-MoCE-Exp/scripts/start_context_memory_daemon.ps1`
- CLI `warm`
- HTTP `POST /warm`
- MCP `ivy_memory_warm`
- process-local cache status
- the fact that warmup is useful for persistent daemon/MCP processes, not one-shot CLI processes

## Why

CP62-CP70 made the daemon path the practical fast path, but the user-facing plugin docs still described mostly cold CLI usage. CP71 makes the documented workflow match the measured workflow.

## Verification

This is a docs-only checkpoint. The edited docs now point users at:

```powershell
powershell -ExecutionPolicy Bypass -File .\MoME-MoCE-Exp\scripts\start_context_memory_daemon.ps1
```

and list the warmup tools/API surfaces explicitly.
