# DeepSeek Router Latency Report - 2026-05-11

Question: is DeepSeek v4 Flash viable as a low-latency MoME/MoCE router, or should the project optimize sub-millisecond deterministic algorithms?

Dataset: `out/context_stress_ivy_real_v2`

Cases: 119

Policy for DeepSeek runs: `decoy_or_ambiguous`

Backend: `indexed`

DeepSeek role: advisory finder only. It can choose from deterministic candidates, but ACCA still gates evidence and falls back to deterministic selected evidence.

## Results

| Router | Quality | Passed | DeepSeek Calls | Mean ms | P50 ms | Max ms | Forbidden Hits | Approx ms / Remote Call |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D-ACCA scan | 1.0 | 119/119 | 0 | 1.619 | 1.569 | 2.650 | 0 | 0 |
| D-ACCA indexed | 1.0 | 119/119 | 0 | 0.857 | 0.795 | 2.516 | 0 | 0 |
| D-ACCA indexed k16 top3 | 1.0 | 119/119 | 0 | 0.814 | 0.741 | 2.502 | 0 | 0 |
| DeepSeek cap 4 | 1.0 | 119/119 | 16 | 519.559 | 15.084 | 5364.152 | 0 | 3864.220 |
| DeepSeek cap 8 | 1.0 | 119/119 | 16 | 565.062 | 15.530 | 4859.278 | 0 | 4202.649 |
| DeepSeek cap 16 | 1.0 | 119/119 | 16 | 560.356 | 15.545 | 4652.482 | 0 | 4167.648 |
| DeepSeek cap 24 | 1.0 | 119/119 | 16 | 658.458 | 15.315 | 5934.198 | 0 | 4897.281 |
| DeepSeek cap 32 | 1.0 | 119/119 | 16 | 683.361 | 15.014 | 5929.240 | 0 | 5082.497 |
| DeepSeek cap 48 | 1.0 | 119/119 | 16 | 772.460 | 15.499 | 6814.883 | 0 | 5745.171 |
| DeepSeek cap 64 | 1.0 | 119/119 | 16 | 845.836 | 14.878 | 7582.014 | 0 | 6290.905 |
| DeepSeek cap 80 | 1.0 | 119/119 | 16 | 907.588 | 15.538 | 7304.281 | 0 | 6750.186 |
| DeepSeek cap 96 | 1.0 | 119/119 | 16 | 1247.274 | 15.575 | 20856.194 | 0 | 9276.600 |
| DeepSeek cap 128 | 1.0 | 119/119 | 16 | 1100.985 | 14.778 | 10702.082 | 0 | 8188.576 |
| DeepSeek cap 160 | 1.0 | 119/119 | 16 | 1299.461 | 15.321 | 10664.997 | 0 | 9664.741 |
| DeepSeek cap 384 | 1.0 | 119/119 | 16 | 2207.116 | 14.547 | 35039.340 | 0 | 16415.425 |
| DeepSeek ambiguous-only | 1.0 | 119/119 | 0 | 12.593 | 14.734 | 31.563 | 0 | 0 |

## Interpretation

DeepSeek v4 Flash is not viable as the default low-latency router. Even with `max_output_tokens=4`, the full-suite mean is 519.559 ms because 16 remote advisory calls dominate runtime. The per-remote-call cost is still roughly 3.9 seconds.

D-ACCA indexed is the correct hot path. It gives 119/119 quality, 0 forbidden hits, and sub-millisecond p50. The `candidate_k=16, top_k=3` variant was slightly faster in this run while preserving quality.

DeepSeek remains useful as an offline judge, adversarial case generator, or rare escalation path. It should not be used for ordinary routing if the target is under 5 ms.

## Decision

Optimize sub-millisecond deterministic algorithms first.

Use DeepSeek only when one of these is true:

- the query is low confidence under deterministic gates;
- answer-level eval needs an external judge;
- autoresearch wants to generate harder contradiction/staleness cases;
- latency is explicitly allowed to exceed the hot-path budget.

For the user's stated preference, the correct product target is:

> Prefer a deterministic router that is right 9/10 times under 5 ms over a remote router that is right 10/10 times but takes seconds.

Current data is stronger than that target on Ivy-real v2: D-ACCA indexed is 10/10 quality on this benchmark under 1 ms p50.
