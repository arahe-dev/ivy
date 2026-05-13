# IVY Context Memory Daemon Smoke Test

Created: `2026-05-12T03:25:24Z`
Passed: `True`
Base URL: `http://127.0.0.1:49619`
Total wall: `2865.15 ms`
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
| Index items | `936` |
| Query index cache entries | `1` |
| Item feature cache entries | `936` |
| Corpus item cache entries | `82` |
| Warm wall | `58.992 ms` |

## Query

| Metric | Value |
|---|---:|
| Selected | `ing_mome_moce_exp_cp30_adaptive_packet_and_not_5_26513cc7eb30` |
| Packet mode | `proof_lite` |
| Query wall | `10.142 ms` |
| Router latency | `4.638 ms` |

## Agent Hooks

| Surface | Hook | Selected | Packet mode |
|---|---|---:|---|
| `/agent/hook` | `before_task` | `ing_mome_moce_exp_cp30_adaptive_packet_and_not_5_26513cc7eb30` | `proof_lite` |
| `/packet/v2` | `before_edit` | `ing_mome_moce_exp_codex_opencode_memory_plugin_2_a6ca53bab3c1` | `proof_lite` |

## Timing Breakdown

| Stage | ms |
|---|---:|
| `prefilter` | `2.219` |
| `corpus` | `0.017` |
| `router_init` | `2.249` |
| `route` | `4.638` |
| `render` | `0.02` |
| `packet_write` | `0.736` |
| `total` | `10.142` |
