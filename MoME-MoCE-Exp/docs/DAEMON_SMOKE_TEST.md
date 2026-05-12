# IVY Context Memory Daemon Smoke Test

Created: `2026-05-12T03:05:43Z`
Passed: `True`
Base URL: `http://127.0.0.1:63065`
Total wall: `2479.782 ms`
Query wall budget: `15.0 ms`
Router budget: `5.0 ms`

## Checks

| Check | Pass |
|---|---:|
| `health_ok` | `True` |
| `ingest_has_corpus` | `True` |
| `warm_ok` | `True` |
| `query_index_cache_warm` | `True` |
| `item_feature_cache_warm` | `True` |
| `corpus_item_cache_warm` | `True` |
| `query_selected_evidence` | `True` |
| `agent_hook_selected_evidence` | `True` |
| `packet_v2_selected_evidence` | `True` |
| `query_wall_under_budget` | `True` |
| `router_under_budget` | `True` |

## Warmup

| Metric | Value |
|---|---:|
| Warmed queries | `4` |
| Index items | `923` |
| Query index cache entries | `1` |
| Item feature cache entries | `923` |
| Corpus item cache entries | `81` |
| Warm wall | `57.177 ms` |

## Query

| Metric | Value |
|---|---:|
| Selected | `ing_mome_moce_exp_cp30_adaptive_packet_and_not_5_26513cc7eb30` |
| Packet mode | `proof_lite` |
| Query wall | `11.889 ms` |
| Router latency | `4.406 ms` |

## Agent Hooks

| Surface | Hook | Selected | Packet mode |
|---|---|---:|---|
| `/agent/hook` | `before_task` | `ing_mome_moce_exp_cp30_adaptive_packet_and_not_5_26513cc7eb30` | `proof_lite` |
| `/packet/v2` | `before_edit` | `ing_mome_moce_exp_codex_opencode_memory_plugin_2_a6ca53bab3c1` | `proof_lite` |

## Timing Breakdown

| Stage | ms |
|---|---:|
| `prefilter` | `3.609` |
| `corpus` | `0.03` |
| `router_init` | `2.748` |
| `route` | `4.406` |
| `render` | `0.016` |
| `packet_write` | `0.762` |
| `total` | `11.889` |
