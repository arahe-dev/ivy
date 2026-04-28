# IVY Memory Phase 1

This phase adds passive memory only. It does not inject memory into prompts, change planner behavior, or let the model write trusted memory state. Retrieval is tested separately by `IVY_MEMORY_EVAL.md` before any active use.

## Architecture

SQLite is the canonical ledger. It stores episodes, artifacts, sanitized tool traces, memory items, and local retrieval vectors. Every memory item points back to an episode or source artifact.

FTS5 is exact keyword retrieval over memory text and episode context when the local SQLite build supports it. If FTS5 is unavailable, search falls back to `LIKE` and warns.

Vectors are retrieval hints only. The default backend is a deterministic standard-library hashed bag-of-words vector. It requires no service, no cloud API, and no optional extension. `sqlite-vec` is detected but not required; in the current local run it is not available, so the stdlib fallback is used.

Model JSON is not trusted as memory state. Ingestion parses existing artifacts deterministically. LLM text may appear as source output, but canonical memory rows are created by code from provenance-backed artifacts.

## Schema Summary

- `episodes`: run id, task text, outcome, success, failure type, artifact path, model profile, step count, source kind.
- `tool_traces`: episode id, step index, tool name, status, sanitized argument summary, argument hash, result summary, artifact path.
- `artifacts`: episode id, path, kind, SHA-256, created timestamp.
- `memory_items`: source episode id, kind, text, importance, confidence, status, source artifact path, timestamps.
- `memory_vectors`: memory item id, backend, embedding model, dimension, vector JSON/blob, timestamp.

## Commands

Initialize the default DB:

```powershell
python -m ivy_agent_demo.memory_cli init
```

Ingest one run:

```powershell
python -m ivy_agent_demo.memory_cli ingest --run-dir C:\ivy\runs\phase1_agent_demo\20260426_181439\calc_write
```

Ingest a parent runs directory:

```powershell
python -m ivy_agent_demo.memory_cli ingest --runs-root C:\ivy\runs\phase1_agent_demo
python -m ivy_agent_demo.memory_cli ingest --runs-root C:\ivy\runs\qwen36_4060_bench
```

Search:

```powershell
python -m ivy_agent_demo.memory_cli search --query "json validation failed"
python -m ivy_agent_demo.memory_cli vector-search --query "model emitted think tags before JSON"
python -m ivy_agent_demo.memory_cli hybrid-search --query "json tool call failed because of reasoning tags"
python -m ivy_agent_demo.memory_cli stats
```

Use `--db <path>` to test in a temporary database. Use `--json` for machine-readable CLI output.

## Test Plan

1. Initialize schema twice in a temp DB and verify required tables.
2. Insert and read back a synthetic episode.
3. Ingest a synthetic run with summary, validation, tool call, and tool result artifacts.
4. Ingest at least one real run from `C:\ivy\runs` when present.
5. Search for a known term and verify FTS or LIKE returns the expected memory item.
6. Vectorize at least three synthetic memory items and verify a similar query returns the expected item.
7. Run CLI smoke tests for init, ingest, stats, search, vector-search, and hybrid-search.
8. If local Qwen paths exist, run or ingest a tiny Qwen-backed run and verify a Qwen memory item is searchable.

## Inspect Manually

```powershell
sqlite3 ivy_agent_demo\memory\ivy_memory.sqlite3 ".tables"
sqlite3 ivy_agent_demo\memory\ivy_memory.sqlite3 "select id, kind, text, source_artifact_path from memory_items limit 10;"
```

If `sqlite3.exe` is not installed, use Python:

```powershell
python -c "import sqlite3; c=sqlite3.connect(r'ivy_agent_demo\memory\ivy_memory.sqlite3'); print(c.execute('select count(*) from memory_items').fetchone())"
```

## Resetting Test Memory

Do not delete the default user memory DB during normal use. For tests, pass `--db` pointing at a temp directory and delete only that temp directory after the test.

## Known Limitations

- Ingestion supports current IVY agent-demo and benchmark-style artifacts, not every historical run shape.
- Tool arguments are summarized and hashed, not stored raw.
- The fallback vector backend is simple hashed bag-of-words, so it is deterministic but not a high-quality semantic embedding.
- No prompt injection from memory exists in this phase.
- No model reflection generation exists in this phase.
- Real retrieval quality should be judged with `python -m ivy_agent_demo.memory_eval --cases ivy_agent_demo/memory_eval_cases.json --top-k 5 --compare-latest` after ingestion.
