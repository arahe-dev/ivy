# IVY Results Ledger

This ledger records first-pass smoke and memory retrieval results. It is not a performance leaderboard.

## Qwen Benchmark Smoke Results

| Config | Result |
|---|---|
| Model | `Qwen3.6-35B-A3B-UD-IQ2_XXS.gguf` |
| ctx | `512` |
| cache_k/cache_v | `f16` / `f16` |
| cpu_moe | `False` |
| n_gpu_layers | `20` |
| prompt | `short_completion` |
| HTTP | success |
| ingested decode_tps | about `19.616` |
| earlier similar smoke | about `12.68 tok/s` |

Single-run TPS is not stable. These numbers only prove the harness can measure and ingest benchmark artifacts.

## Passive Memory Ingestion Results

| Source | Episodes | Artifacts | Tool Traces | Memory Items | Vectorized |
|---|---:|---:|---:|---:|---:|
| `phase1_agent_demo` | 145 | 1968 | 240 | 181 | 181 |
| `qwen36_4060_bench` | 10 | 20 | 0 | 10 | 10 |

Current stats after ingestion:

| Metric | Value |
|---|---:|
| episodes | 155 |
| tool_traces | 240 |
| artifacts | 1988 |
| memory_items | 191 |
| memory_vectors | 191 |
| fts5_available | True |
| sqlite_vec_available | False |

## Synthetic Memory Eval Results

| Metric | Value |
|---|---:|
| total_cases | 4 |
| evaluated_cases | 4 |
| top_1_hit_rate | 1.0 |
| top_3_hit_rate | 1.0 |
| top_k_hit_rate | 1.0 |
| provenance_present_rate | 1.0 |
| average_latency_ms | about 17.327 |

Synthetic eval proves evaluator mechanics. It does not prove real memory quality.

## Empty Real DB Eval Result

Before real ingestion, the default DB eval returned:

| Metric | Value |
|---|---:|
| top_1_hit_rate | 0.0 |
| top_3_hit_rate | 0.0 |
| top_k_hit_rate | 0.0 |
| provenance_present_rate | 0.0 |

Reason: the default DB was empty.

## Real DB Eval Result After Ingestion

| Metric | Value |
|---|---:|
| run | `C:\ivy\runs\memory_eval\20260428_205737` |
| top_1_hit_rate | 0.75 |
| top_3_hit_rate | 0.75 |
| top_k_hit_rate | 0.75 |
| provenance_present_rate | 0.75 |

`0.75` means 3 of 4 default cases passed. Inspect `memory_eval_report.md` in that run to identify the missed case before changing retrieval logic.
