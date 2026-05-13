# CP36 Plugin Status And OpenCode QoL - 2026-05-11

## What Changed

CP36 adds cache observability to plugin status and updates the OpenCode command runbook for MCP mode.

`status` and `ivy_memory_status` now include:

```json
{
  "build_cache": {
    "exists": true,
    "path": "...\\cache\\build_fingerprint.json",
    "updated_at": "...",
    "fingerprint_sha256": "...",
    "file_count": 1
  }
}
```

The OpenCode command note now documents:

- CLI query/remember
- HTTP API mode
- MCP mode
- MCP tool names

## Verification

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ivy_context_memory_plugin.py -q
```

Expected:

- plugin status reports a populated `build_cache`
- repeated build cache test still passes

## Why This Matters

Once agents call memory through MCP, they need a cheap way to know whether the memory store is healthy:

- Is the dataset built?
- Does the query index exist?
- Does the build cache exist?
- How many source files are represented by the current fingerprint?

This makes the plugin easier to operate from Codex/OpenCode without opening local files manually.
