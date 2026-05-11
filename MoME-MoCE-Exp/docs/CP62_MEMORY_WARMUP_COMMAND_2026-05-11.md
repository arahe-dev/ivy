# CP62 Memory Warmup Command - 2026-05-11

## What Changed

Added an explicit cache warmup surface to the context-memory plugin.

Updated:

```text
plugins/ivy-context-memory/scripts/ivy_context_memory.py
MoME-MoCE-Exp/tests/test_ivy_context_memory_plugin.py
```

New surfaces:

- CLI: `warm`
- HTTP: `POST /warm`
- MCP tool: `ivy_memory_warm`

The warmup path loads the query index and warms:

- query-index cache
- per-item feature cache
- converted `CorpusItem` cache

It does not write answer packets or run final routing.

## CLI Example

```powershell
python plugins\ivy-context-memory\scripts\ivy_context_memory.py `
  --store MoME-MoCE-Exp\out\scoreboard_plugin_store `
  warm `
  --query "What did CP28 show about final answer packet formats?" `
  --query "What MCP tools does ivy-context-memory expose?" `
  --query "What is the latest CP42 rebuild policy versus stale memory?" `
  --query "What is today's Bitcoin price?"
```

## Real Run

Result:

- index loaded: `true`
- index items: `756`
- warmed queries: `4`
- max prefilter items: `32`
- query index cache entries: `1`
- item feature cache entries: `756`
- corpus item cache entries: `86`
- warm wall: `101.836 ms`

Per-query warm rows:

| Query | Candidates | Corpus Items Warmed | Wall ms |
|---|---:|---:|---:|
| CP28 final-answer packet formats | `32` | `32` | `31.815` |
| MCP tools exposed | `32` | `32` | `6.077` |
| latest CP42 rebuild policy | `32` | `32` | `7.614` |
| today's Bitcoin price | `32` | `32` | `4.671` |

## Important Note

The warmup command is most useful inside a persistent MCP or HTTP process. A one-shot CLI invocation proves behavior, but the process exits and releases the in-memory caches.

## Verification

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ivy_context_memory_plugin.py -q
python -m py_compile plugins\ivy-context-memory\scripts\ivy_context_memory.py
```

Result:

- `12 passed`
