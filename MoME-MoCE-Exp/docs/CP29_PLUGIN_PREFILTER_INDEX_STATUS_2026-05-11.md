# CP29 Plugin Prefilter Index Status - 2026-05-11

## What Changed

CP29 turns the `ivy-context-memory` plugin from a full-corpus router wrapper into a two-stage memory path:

1. Build/remember writes the normal ACCA corpus dataset.
2. Build/remember also writes a persisted JSON query index at `store/index/corpus_index.json`.
3. Query uses the persisted index to prefilter likely evidence before calling `MoMEMoCERouter`.
4. The prefiltered subset is routed in memory, avoiding temporary subset files on the hot path.
5. Ingestion now skips generated output directories such as `out`, `packets`, `query_subset`, `.ivy-context-memory`, and `artifacts` so plugin stores do not recursively ingest their own packets or benchmark output.

## Verification

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ivy_context_memory_plugin.py -q
python -m py_compile C:\ivy\plugins\ivy-context-memory\scripts\ivy_context_memory.py C:\ivy\MoME-MoCE-Exp\scripts\ingest_external_corpus.py
```

Result:

- `3 passed`
- Python compile checks passed

## Smoke Store

Smoke store:

```text
C:\ivy\MoME-MoCE-Exp\out\plugin_smoke_store
```

Build path:

```powershell
python C:\ivy\plugins\ivy-context-memory\scripts\ivy_context_memory.py --store C:\ivy\MoME-MoCE-Exp\out\plugin_smoke_store init
python C:\ivy\plugins\ivy-context-memory\scripts\ivy_context_memory.py --store C:\ivy\MoME-MoCE-Exp\out\plugin_smoke_store ingest --source-root C:\ivy\MoME-MoCE-Exp --no-build
python C:\ivy\plugins\ivy-context-memory\scripts\ivy_context_memory.py --store C:\ivy\MoME-MoCE-Exp\out\plugin_smoke_store remember --source-path root/notes/cp28.md --tag cp28 --tag final-answer --authority medium --text "CP28 showed contradiction-aware packets won final-answer A/B on conflict cases."
```

Observed build:

- Corpus items after generated-output filtering: `537`
- Query index items: `537`
- Query index tokens: `7053`

The earlier unfiltered smoke corpus had `5134` items because it ingested generated `out` material. CP29 removes that feedback loop.

## Latency Snapshot

Query:

```text
What did CP28 show about final answer packet formats?
```

| Mode | CLI Wall Time | Router Latency |
|---|---:|---:|
| Full indexed corpus, no prefilter | `467.380 ms` | `17.677 ms` |
| Persisted prefilter index, in-memory subset | `413.544 ms` | `12.078 ms` |

This is a modest win on the cleaned 537-item corpus. The bigger win is that the router no longer scales linearly with generated junk from prior runs, and the prefilter path is ready for larger source roots.

## Important Finding

The prefilter stage ranks the explicit CP28 agent note first, but the downstream router still selected a high-authority runbook chunk because the router's final scoring prefers high-authority docs over medium-authority notes.

That is acceptable for CP29 because the selected chunk was relevant and safe, but it exposes the next routing improvement:

- The plugin should preserve prefilter priority into the router score.
- Explicit `agent_note` evidence should have a first-class priority policy rather than only a prefilter boost.
- Query-specific notes should probably win over generic high-authority docs when the note is a direct answer memory.

This is a CP30/CP31 target, not an index correctness blocker.

## Current Track Record

- Generated-output feedback loop: fixed.
- Persisted query index: built and tested.
- In-memory prefilter routing: built and tested.
- Secret-like note rejection: still passing.
- Source ingest skip regression: added and passing.
