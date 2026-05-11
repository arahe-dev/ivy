# IVY Context Memory Daemon Smoke Test

Created: `2026-05-11T18:23:21Z`
Passed: `True`
Base URL: `http://127.0.0.1:49709`
Total wall: `2277.323 ms`
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
| Index items | `799` |
| Query index cache entries | `1` |
| Item feature cache entries | `799` |
| Corpus item cache entries | `83` |
| Warm wall | `50.226 ms` |

## Query

| Metric | Value |
|---|---:|
| Selected | `ing_mome_moce_exp_cp30_adaptive_packet_and_not_5_26513cc7eb30` |
| Packet mode | `proof_lite` |
| Query wall | `10.487 ms` |
| Router latency | `3.236 ms` |

## Timing Breakdown

| Stage | ms |
|---|---:|
| `prefilter` | `2.116` |
| `corpus` | `0.017` |
| `router_init` | `2.531` |
| `route` | `3.236` |
| `render` | `0.017` |
| `packet_write` | `2.272` |
| `total` | `10.487` |
