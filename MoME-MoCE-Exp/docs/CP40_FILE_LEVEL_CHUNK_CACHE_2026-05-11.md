# CP40 File-Level Chunk Cache - 2026-05-11

## What Changed

CP40 upgrades the plugin build cache from whole-build only to file-level chunk reuse.

New behavior:

- `ingest_external_corpus.py` now exposes `ingest_file(...)`.
- `ivy-context-memory` stores per-file chunk cache records under:

```text
store/cache/chunks/
```

Each chunk cache record is keyed by source root plus relative path and validates:

- root
- relative path
- file size
- `mtime_ns`

If one source file changes, unchanged file chunks are reused while the changed file is re-ingested.

## Verification

New regression:

- create two source files
- build once
- edit only one file
- rebuild
- assert `hit_files == 1`
- assert `miss_files == 1`

Focused suite:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ivy_context_memory_plugin.py tests\test_context_stress_contract.py tests\test_cp7_cp9_contract.py tests\test_cp26_cp28_contract.py -q
```

Result:

- `22 passed`

## Benchmark

Command:

```powershell
python MoME-MoCE-Exp\scripts\run_context_memory_plugin_benchmark.py --reset
```

Latest:

- Query count: `5`
- Passed expectations: `5 / 5`
- Avg query wall: `96.344 ms`
- Avg router latency: `11.235 ms`

## Extra Fix During CP40

The expanded corpus made the live Bitcoin-price negative case fail again by selecting the track-record doc that described the previous Bitcoin bug.

Fix:

- current price questions now require `valid_from` evidence
- generic source/code/doc mentions with only `created_at` do not support volatile market-price claims

## Why This Matters

This makes the memory plugin much more suitable for long-running coding sessions:

- unchanged files do not need re-chunking after every edit
- changed files can be refreshed without losing the existing index path
- source edits become cheaper without needing a watcher yet
