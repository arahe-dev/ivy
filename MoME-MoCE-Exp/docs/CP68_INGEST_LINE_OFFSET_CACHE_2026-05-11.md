# CP68 Ingest Line Offset Cache - 2026-05-11

## What Changed

Removed repeated file reads during external corpus ingestion line-offset calculation.

Updated:

```text
MoME-MoCE-Exp/scripts/ingest_external_corpus.py
MoME-MoCE-Exp/tests/test_ingest_external_corpus.py
MoME-MoCE-Exp/docs/DAEMON_SMOKE_TEST.md
```

`ingest_file(...)` already reads each source file into memory. It now passes that text into `item_from_chunk(...)`, so provenance line numbers are computed from the already-loaded text instead of rereading the same file for every chunk.

## Why

This is not full section-level caching yet, but it removes a simple per-chunk I/O cost from the build path and is especially relevant for large Markdown/RST files with many sections.

## Real Daemon Gate

Command:

```powershell
python MoME-MoCE-Exp\scripts\run_context_memory_daemon_smoke.py `
  --store MoME-MoCE-Exp\out\daemon_smoke_store `
  --source-root MoME-MoCE-Exp `
  --out MoME-MoCE-Exp\docs\DAEMON_SMOKE_TEST.md
```

Result:

- passed: `true`
- corpus items: `799`
- warm wall: `50.226 ms`
- post-warm query wall: `10.487 ms`
- post-warm router latency: `3.236 ms`

## Verification

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ingest_external_corpus.py tests\test_context_memory_daemon_smoke.py tests\test_ivy_context_memory_plugin.py -q
python -m py_compile MoME-MoCE-Exp\scripts\ingest_external_corpus.py
```

Result:

- `17 passed`
