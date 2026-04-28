# IVY Memory Status

This is the current checkpoint for IVY passive memory and Qwen benchmark measurement before MoME/MoCE work.

## Current Architecture

Memory is passive. It is not injected into prompts and it does not change the agent loop.

Memory stack:

- SQLite: canonical ledger and source of truth.
- FTS5: exact keyword retrieval over memory text and episode context.
- Hashed vectors: deterministic local semantic-ish retrieval fallback.
- Hybrid search: combines keyword, vector, and recent-success style retrieval.
- Eval harness: tests retrieval quality before prompt injection.

Current policy:

- No prompt injection.
- No agent-loop behavior changes.
- Model-generated JSON is not trusted as memory state.
- Memory entries should point to source artifacts or episodes wherever possible.
- Vectors are retrieval hints, not truth.

## Implemented

- Qwen 3.6 35B-A3B RTX 4060 Phase 1 measurement harness.
- SQLite memory ledger.
- Deterministic artifact ingestion from existing run artifacts.
- FTS5 search with LIKE fallback.
- Standard-library hashed-vector retrieval fallback.
- Hybrid memory search.
- Memory CLI.
- Memory retrieval eval harness.
- Timestamped eval reruns and append-only history.
- PowerShell rerun helpers.

## Intentionally Not Implemented

- Prompt memory injection.
- MoME runtime routing.
- MoCE context assembly.
- Planner or agent-loop changes.
- Trusted model-authored memory JSON.
- Mandatory sqlite-vec, Chroma, LanceDB, Postgres, cloud APIs, or external vector services.

## Files

- `ivy/scripts/bench_qwen36_4060.ps1`
- `ivy/scripts/collect_qwen36_metrics.py`
- `ivy/scripts/rerun_memory_eval.ps1`
- `ivy/manifests/qwen36_4060_baseline.yaml`
- `ivy_agent_demo/memory_store.py`
- `ivy_agent_demo/memory_ingest.py`
- `ivy_agent_demo/memory_search.py`
- `ivy_agent_demo/memory_cli.py`
- `ivy_agent_demo/memory_eval.py`
- `ivy_agent_demo/memory_eval_cases.json`
- `ivy_agent_demo/memory/ivy_memory.sqlite3`

## Commands

```powershell
cd C:\ivy
python -m ivy_agent_demo.memory_cli init
python -m ivy_agent_demo.memory_cli ingest --runs-root C:\ivy\runs\phase1_agent_demo
python -m ivy_agent_demo.memory_cli ingest --runs-root C:\ivy\runs\qwen36_4060_bench
python -m ivy_agent_demo.memory_cli stats
python -m ivy_agent_demo.memory_eval --cases ivy_agent_demo/memory_eval_cases.json --top-k 5 --compare-latest
```

Synthetic eval:

```powershell
python -m ivy_agent_demo.memory_eval --cases ivy_agent_demo/memory_eval_cases.json --build-synthetic-db --top-k 5 --compare-latest
```

## First Results

Synthetic memory eval passed:

| Metric | Value |
|---|---:|
| total_cases | 4 |
| evaluated_cases | 4 |
| top_1_hit_rate | 1.0 |
| top_3_hit_rate | 1.0 |
| top_k_hit_rate | 1.0 |
| provenance_present_rate | 1.0 |
| average_latency_ms | about 17.327 |

Before real ingestion, the default DB eval had all-zero retrieval metrics because the DB was empty.

After real ingestion:

| Source | Episodes | Artifacts | Tool Traces | Memory Items | Vectorized |
|---|---:|---:|---:|---:|---:|
| `phase1_agent_demo` | 145 | 1968 | 240 | 181 | 181 |
| `qwen36_4060_bench` | 10 | 20 | 0 | 10 | 10 |

Current memory stats after ingestion:

| Metric | Value |
|---|---:|
| episodes | 155 |
| tool_traces | 240 |
| artifacts | 1988 |
| memory_items | 191 |
| memory_vectors | 191 |
| fts5_available | True |
| sqlite_vec_available | False |

Real memory eval after ingestion:

| Metric | Value |
|---|---:|
| run | `C:\ivy\runs\memory_eval\20260428_205737` |
| top_1_hit_rate | 0.75 |
| top_3_hit_rate | 0.75 |
| top_k_hit_rate | 0.75 |
| provenance_present_rate | 0.75 |

This means 3 of 4 default cases passed. Inspect the report to identify the missed case.

## Qwen Benchmark Status

One Qwen-backed smoke produced and ingested benchmark memory for:

- `ctx=512`
- `cache_k=f16`
- `cache_v=f16`
- `cpu_moe=False`
- `n_gpu_layers=20`
- `prompt=short_completion`
- one ingested run reported `decode_tps` around `19.616`

Earlier smoke observed about `12.68 tok/s` for a similar tiny run. Single-run TPS is not stable and must not be treated as final performance.

## Current Limitations

- Retrieval hit detection is term-based.
- Hashed vectors are deterministic hints, not high-quality embeddings.
- `sqlite_vec` is not available in the current local run.
- Real eval quality depends on what artifacts have been ingested.
- Qwen benchmark results are smoke measurements, not optimization conclusions.

## Next Checkpoint Before MoME/MoCE

Implement Phase 2A only: read-only memory packet preview. Retrieve candidate memories and save/print a proposed packet, but do not inject it into prompts.
