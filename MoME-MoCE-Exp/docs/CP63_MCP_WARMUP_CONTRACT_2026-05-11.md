# CP63 MCP Warmup Contract - 2026-05-11

## What Changed

Added subprocess coverage for the MCP `ivy_memory_warm` tool.

Updated:

```text
MoME-MoCE-Exp/tests/test_ivy_context_memory_plugin.py
```

The test starts the plugin in MCP stdio mode, sends framed JSON-RPC messages to:

1. initialize
2. remember a CP62 warmup note
3. call `ivy_memory_warm`

It verifies the returned structured content reports warmed cache state.

## Why

CP62 added the warmup implementation and surfaces. CP63 proves the path that matters for Codex/OpenCode MCP clients actually works, not just the direct Python helper.

## Verified Contract

`ivy_memory_warm` returns:

- `ok: true`
- `warmed_queries`
- `query_index_cache_entries`
- `item_feature_cache_entries`
- `corpus_item_cache_entries`

## Verification

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ivy_context_memory_plugin.py -q
python -m py_compile plugins\ivy-context-memory\scripts\ivy_context_memory.py
```

Result:

- `13 passed`
