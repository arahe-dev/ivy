# IVY Context Memory Daemon Smoke Test

Created: `2026-05-11T18:09:43Z`
Passed: `True`
Base URL: `http://127.0.0.1:61528`
Total wall: `2535.591 ms`

## Warmup

| Metric | Value |
|---|---:|
| Warmed queries | `4` |
| Index items | `786` |
| Query index cache entries | `1` |
| Item feature cache entries | `786` |
| Corpus item cache entries | `83` |
| Warm wall | `48.45 ms` |

## Query

| Metric | Value |
|---|---:|
| Selected | `ing_mome_moce_exp_cp30_adaptive_packet_and_not_5_26513cc7eb30` |
| Packet mode | `proof_lite` |
| Query wall | `8.5 ms` |
| Router latency | `3.183 ms` |

## Timing Breakdown

| Stage | ms |
|---|---:|
| `prefilter` | `1.929` |
| `corpus` | `0.018` |
| `router_init` | `2.036` |
| `route` | `3.183` |
| `render` | `0.016` |
| `packet_write` | `0.959` |
| `total` | `8.5` |
