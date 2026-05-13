# CP31/CP32 Incremental Build Cache - 2026-05-11

## What Changed

The `ivy-context-memory` plugin now keeps a build fingerprint cache at:

```text
store/cache/build_fingerprint.json
```

The fingerprint includes:

- registered source roots
- enabled file extensions
- `max_files`
- source file count
- aggregate source byte size
- per-file relative path, size, and `mtime_ns`
- notes file hash

When the fingerprint is unchanged and the dataset plus query index already exist, `build` returns a cache hit instead of re-ingesting and re-chunking source files.

## Why This Matters

This is the first practical step toward a continuously available memory plugin:

- Codex/OpenCode can call `build` frequently without paying full parse cost every time.
- Agent notes invalidate the cache automatically because the notes hash is part of the fingerprint.
- Source edits invalidate the cache through size/mtime changes.
- The existing ACCA dataset and CP29 query index remain the serving artifacts.

## Verification

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ivy_context_memory_plugin.py -q
python -m py_compile C:\ivy\plugins\ivy-context-memory\scripts\ivy_context_memory.py
```

Result:

- `5 passed`
- Python compile check passed

## Smoke Timing

Smoke store:

```text
C:\ivy\MoME-MoCE-Exp\out\plugin_smoke_store
```

Observed:

| Build Mode | CLI Wall Time | Cache Status |
|---|---:|---|
| First build after code/doc changes | `2133.291 ms` | `miss` |
| Repeated unchanged build | `872.931 ms` | `hit` |

The cache-hit path still scans file metadata to compute the fingerprint, so it is not yet a sub-100ms watcher. It does avoid full source parsing, chunking, dataset rewrite, and query index rewrite.

## Current Limitation

This is a whole-build cache, not a file-level incremental cache.

Next improvement:

- Store per-file chunk outputs.
- Re-ingest only changed files.
- Rebuild the query index from cached unchanged chunks plus changed chunks.
- Add a filesystem watcher or explicit `watch` mode for near-real-time memory freshness.
