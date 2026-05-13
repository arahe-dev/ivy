# CP64 Process Cache Status - 2026-05-11

## What Changed

Added process-local cache visibility to plugin status output.

Updated:

```text
plugins/ivy-context-memory/scripts/ivy_context_memory.py
MoME-MoCE-Exp/tests/test_ivy_context_memory_plugin.py
```

`status(...)` now includes:

```json
{
  "process_caches": {
    "query_index_cache_entries": 1,
    "item_feature_cache_entries": 756,
    "corpus_item_cache_entries": 86
  }
}
```

## Why

CP62 introduced warmup, but clients still needed a way to confirm whether a persistent MCP/HTTP process was actually warm. CP64 makes that visible through the existing `status` surface and `ivy_memory_status` MCP tool.

## Verified Behavior

The MCP subprocess test now:

1. starts MCP stdio
2. remembers a note
3. calls `ivy_memory_warm`
4. calls `ivy_memory_status`
5. verifies status reports non-empty process cache counts

## Verification

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ivy_context_memory_plugin.py -q
python -m py_compile plugins\ivy-context-memory\scripts\ivy_context_memory.py
```

Result:

- `13 passed`
