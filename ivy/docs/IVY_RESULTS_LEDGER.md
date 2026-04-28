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

## Memory Packet Quality

Phase 2B compresses duplicate-heavy packets. The known failure-first query for `json tool call failed because qwen emitted think tags` now groups repeated `json_contamination_warning` memories into one packet line while preserving multiple evidence artifacts.

Key expected indicators:

| Metric | Expected |
|---|---:|
| duplicate_group_count | `> 0` for repeated think-tag memories |
| compression_ratio | `< 1.0` for duplicate-heavy packets |
| provenance_line_rate | `1.0` when evidence is available |

## Packet Sweep

Phase 2B.5 adds broader real packet sweeps across categories. Results are written under `C:\ivy\runs\memory_packet_sweep`.

Use the sweep to identify candidate policies for Phase 2C, not to claim the packet is ready for prompt injection.

Baseline Phase 2B.5 sweep before docs/source coverage backfill:

| Metric | Value |
|---|---:|
| overall packet_term_hit_rate | 0.82 |
| safety hit_rate | 0.6667 |
| general_repo hit_rate | 0.5714 |
| empty_packet_count | 14 |
| overclaim_risk_count | 0 |
| overcompression_risk_count | 0 |

Phase 2B.6 adds source-provenanced docs/source ingestion and coverage checks. Record post-backfill sweep results from `runs/memory_packet_sweep/<timestamp>/sweep_report.md`.

Phase 2B.7 adds source-family ranking cleanup. Track:

| Metric | Meaning |
|---|---|
| top_1_source_family_hit_rate | known-miss query top result came from expected source family |
| top_3_source_family_hit_rate | expected source family appeared in top 3 |
| term_hit_rate | expected terms appeared in ranked candidates |
| known_miss_recovery_rate | expected source family and terms both recovered |

Reports are written under `C:\ivy\runs\memory_ranking_eval`.

## Phase 2C: Opt-in Memory Injection Experiment

Memory injection harness is ready under `ivy_agent_demo/memory_injection_experiment.py`. It compares runs with and without memory-packet augmentation.

| Metric | Value |
|---|---|
| experiment harness | exists (dry-run works) |
| packet augmentation | advisory header + packet + current task |
| none policy baseline | true baseline (no memory) |
| forbidden diffs | none |

Current limitation: Real agent execution requires a clean programmatic runner path. Dry-run validates harness mechanics.

## AutoResearch Harness

AutoResearch is a bounded experiment manager for memory packet/ranking improvements. It logs per-iteration metrics, decisions, and diffs under `C:\ivy\runs\autoresearch` without changing the agent runtime.
