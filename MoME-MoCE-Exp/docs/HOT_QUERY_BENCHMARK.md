# IVY Context Memory Hot Query Benchmark

Created: `2026-05-11T17:59:56Z`

## Summary

| Pass | Avg wall ms | Avg plugin wall ms | Avg router ms | Prefilter ms | Corpus ms |
|---:|---:|---:|---:|---:|---:|
| 1 | 21.992 | 21.856 | 2.474 | 12.809 | 3.689 |
| 2 | 7.669 | 7.546 | 2.546 | 1.979 | 0.018 |
| 3 | 7.853 | 7.726 | 2.454 | 2.288 | 0.021 |

## Rows

### Pass 1

| Query | Wall ms | Router ms | Mode | Selected |
|---|---:|---:|---|---:|
| What did CP28 show about final answer packet formats? | 80.303 | 3.169 | proof_lite | 1 |
| What MCP tools does ivy-context-memory expose? | 9.898 | 1.47 | contradiction_aware | 1 |
| What did CP29 change about generated output ingestion? | 9.092 | 2.427 | proof_lite | 1 |
| How does CP32 make repeated plugin builds faster? | 12.096 | 2.427 | contradiction_aware | 1 |
| What is the latest CP42 rebuild policy versus stale memory? | 10.527 | 2.544 | contradiction_aware | 2 |
| What is today's Bitcoin price? | 10.036 | 2.809 | abstain_notice | 0 |

### Pass 2

| Query | Wall ms | Router ms | Mode | Selected |
|---|---:|---:|---|---:|
| What did CP28 show about final answer packet formats? | 8.206 | 3.034 | proof_lite | 1 |
| What MCP tools does ivy-context-memory expose? | 5.97 | 1.481 | contradiction_aware | 1 |
| What did CP29 change about generated output ingestion? | 7.515 | 2.949 | proof_lite | 1 |
| How does CP32 make repeated plugin builds faster? | 7.897 | 2.437 | contradiction_aware | 1 |
| What is the latest CP42 rebuild policy versus stale memory? | 9.163 | 2.308 | contradiction_aware | 2 |
| What is today's Bitcoin price? | 7.265 | 3.065 | abstain_notice | 0 |

### Pass 3

| Query | Wall ms | Router ms | Mode | Selected |
|---|---:|---:|---|---:|
| What did CP28 show about final answer packet formats? | 7.562 | 2.513 | proof_lite | 1 |
| What MCP tools does ivy-context-memory expose? | 6.9 | 1.647 | contradiction_aware | 1 |
| What did CP29 change about generated output ingestion? | 8.002 | 2.548 | proof_lite | 1 |
| How does CP32 make repeated plugin builds faster? | 7.606 | 2.567 | contradiction_aware | 1 |
| What is the latest CP42 rebuild policy versus stale memory? | 8.525 | 2.208 | contradiction_aware | 2 |
| What is today's Bitcoin price? | 8.525 | 3.238 | abstain_notice | 0 |
