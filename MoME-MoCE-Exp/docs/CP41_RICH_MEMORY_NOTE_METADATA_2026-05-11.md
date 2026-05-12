# CP41 Rich Memory Note Metadata - 2026-05-11

## What Changed

`ivy-context-memory remember` now supports richer ACCA metadata for notes:

- `staleness`
- `supersedes`
- `conflicts_with`

CLI additions:

```powershell
python C:\ivy\plugins\ivy-context-memory\scripts\ivy_context_memory.py remember `
  --text "..." `
  --staleness stale `
  --supersedes old_note_id `
  --conflicts-with conflicting_note_id
```

MCP and HTTP `remember` calls support the same fields.

## Verification

Added regression:

- remember a stale CP41 note
- set `conflicts_with`
- convert it to a corpus item
- assert staleness and conflict metadata are preserved

Focused command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ivy_context_memory_plugin.py tests\test_context_stress_contract.py tests\test_cp26_cp28_contract.py -q
```

Result:

- `17 passed`

## Why This Matters

The plugin can now create memory records that participate in ACCA freshness and conflict behavior without hand-editing corpus JSON.

This unlocks better benchmark lanes:

- stale memory should not answer latest/current queries
- conflict queries should surface both sides when explicitly requested
- superseded notes can remain auditable without becoming default evidence
