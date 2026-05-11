# IVY Context Memory Daemon Smoke Test

Created: `2026-05-11T18:21:49Z`
Passed: `True`
Base URL: `http://127.0.0.1:49582`
Total wall: `4082.596 ms`
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
| `query_wall_under_budget` | `True` |
| `router_under_budget` | `True` |

## Warmup

| Metric | Value |
|---|---:|
| Warmed queries | `4` |
| Index items | `794` |
| Query index cache entries | `1` |
| Item feature cache entries | `794` |
| Corpus item cache entries | `83` |
| Warm wall | `46.441 ms` |

## Query

| Metric | Value |
|---|---:|
| Selected | `ing_mome_moce_exp_cp30_adaptive_packet_and_not_5_26513cc7eb30` |
| Packet mode | `proof_lite` |
| Query wall | `9.865 ms` |
| Router latency | `3.257 ms` |

## Timing Breakdown

| Stage | ms |
|---|---:|
| `prefilter` | `3.061` |
| `corpus` | `0.019` |
| `router_init` | `2.442` |
| `route` | `3.257` |
| `render` | `0.016` |
| `packet_write` | `0.683` |
| `total` | `9.865` |
