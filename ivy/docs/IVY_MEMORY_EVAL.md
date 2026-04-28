# IVY Memory Retrieval Eval

Memory eval measures whether the passive memory subsystem retrieves useful, relevant, provenance-backed memories. It comes before prompt injection so retrieval quality can be tested without changing agent behavior.

This is not prompt injection, agent behavior change, MoME routing, or MoCE context assembly. It is repeatable offline evaluation over the SQLite memory ledger.

Current known checkpoint after real ingestion: `C:\ivy\runs\memory_eval\20260428_205737` reached `0.75` top-1/top-3/top-k hit rate and `0.75` provenance rate on the default four cases.

## Run Against Real DB

```powershell
cd C:\ivy
python -m ivy_agent_demo.memory_eval --cases ivy_agent_demo/memory_eval_cases.json --top-k 5 --compare-latest
```

Use an explicit DB:

```powershell
python -m ivy_agent_demo.memory_eval --cases ivy_agent_demo/memory_eval_cases.json --db ivy_agent_demo\memory\ivy_memory.sqlite3 --top-k 5
```

## Synthetic Eval

Synthetic mode creates a timestamped DB under `runs/memory_eval/<timestamp>/synthetic_memory.sqlite3` and does not pollute user memory.

```powershell
python -m ivy_agent_demo.memory_eval --cases ivy_agent_demo/memory_eval_cases.json --build-synthetic-db --top-k 5
```

## Rerun After Ingestion

```powershell
python -m ivy_agent_demo.memory_cli ingest --runs-root C:\ivy\runs\phase1_agent_demo
python -m ivy_agent_demo.memory_eval --cases ivy_agent_demo/memory_eval_cases.json --top-k 5 --compare-latest
```

PowerShell helper:

```powershell
powershell -ExecutionPolicy Bypass -File ivy\scripts\rerun_memory_eval.ps1 -BuildSyntheticDb -CompareLatest
```

```powershell
powershell -ExecutionPolicy Bypass -File ivy\scripts\rerun_memory_eval.ps1 `
  -IngestBeforeEval `
  -RunsRoot C:\ivy\runs\phase1_agent_demo `
  -CompareLatest
```

## Outputs

Each run writes:

```text
runs/memory_eval/<timestamp>/
  memory_eval_config.json
  memory_eval_report.md
  memory_eval_results.csv
  memory_eval_results.json
```

History is append-only:

```text
runs/memory_eval/history.jsonl
runs/memory_eval/history.csv
```

## Metrics

- `top_1_hit_rate`: expected memory appears as the first result.
- `top_3_hit_rate`: expected memory appears in the first three results.
- `top_k_hit_rate`: expected memory appears anywhere in the configured `top-k`.
- `provenance_present_rate`: results include source artifact, episode id, or run id when required.
- `average_latency_ms`: mean retrieval latency per case.

Sparse DBs can legitimately score low. Misses mean the expected evidence was not retrieved, not necessarily that the memory system is broken.

Before real ingestion, the default DB scored `0.0` across hit/provenance rates because it was empty. Synthetic eval scored `1.0` across hit/provenance rates and proves evaluator mechanics, not real memory quality.

## Comparison

`--compare-latest` compares the current run with the most recent previous row in `history.jsonl`. It reports metric deltas, improved cases, regressions, newly passing cases, newly failing cases, and case ID changes.

## Known Limitations

- Hit detection is term-based and deterministic.
- Synthetic eval proves evaluator mechanics, not real retrieval quality.
- Real DB quality depends on what artifacts have been ingested.
- Vector retrieval currently uses the standard-library hashed vector fallback.
- No memory is injected into agent prompts.

## Future Memory Experiments

### Phase 2A: Read-only memory packets

- Retrieve top-k memories before a run.
- Do not inject into prompt yet.
- Only print proposed memory packet.
- Evaluate whether selected memory is relevant.

### Phase 2B: Prompt injection experiment

- Add opt-in flag only.
- Inject compact memory packet into dynamic suffix.
- Compare:
  - no memory
  - FTS-only memory
  - vector-only memory
  - hybrid memory
- Measure:
  - task success
  - JSON validity
  - tool failures
  - steps to completion
  - latency
  - token/prompt size if available

### Phase 2C: Memory policy configs

- Add YAML/JSON policies:
  - `memory_policy_none`
  - `memory_policy_keyword_only`
  - `memory_policy_vector_only`
  - `memory_policy_hybrid`
  - `memory_policy_recent_buffer`
  - `memory_policy_failure_first`
  - `memory_policy_success_weighted`

### Phase 3: Hot buffer / LRU memory

- Add recent working memory buffer.
- Promote memories when reused successfully.
- Demote stale memories.
- Track `last_used_at` and `use_count`.
- Evaluate useful recall per latency.

### Phase 4: MoME — Mixture of Memory Experts

- Add memory experts:
  - episodic expert
  - procedural expert
  - failure expert
  - benchmark expert
  - safety expert
  - FTS expert
  - vector expert
  - recent-buffer expert
- Add simple router.
- Evaluate which expert contributed useful memories.

### Phase 5: MoCE — Mixture of Context Experts

- Add context composers:
  - minimal composer
  - debugging composer
  - benchmark composer
  - tool-use composer
  - safety composer
  - planning composer
- Evaluate how memory formatting affects model reliability.

### Phase 6: Procedure promotion

- Promote repeated successful tool traces into reusable procedures.
- Do not allow procedures to bypass policy gate.
- Store evidence episodes.
- Evaluate whether procedures reduce steps.

### Phase 7: Memory governance

- Add statuses:
  - active
  - stale
  - superseded
  - rejected
- Add confidence decay.
- Add stale-memory detection.
- Add memory pruning reports.

### Phase 8: Advanced vectors

- Keep current stdlib hashed vectors as fallback.
- Optionally add sqlite-vec if available.
- Later optionally compare with external embedding backends, but do not make them mandatory.
