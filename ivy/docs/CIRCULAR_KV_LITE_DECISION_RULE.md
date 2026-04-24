# Circular KV Lite v0 Decision Rule

## Promising
Classify as promising when all are true:
- Outputs remain coherent and usable in short-context and long-context runs.
- Long-context shows a clear win in at least one primary latency metric (`wall_ms` or `ttft_est_ms`) versus baseline.
- No critical stability issues (no crashes/hangs/timeouts).
- Short-context regression, if any, is small and acceptable relative to long-context gain.

Action:
- Continue to next implementation iteration with the same experiment package.

## Marginal
Classify as marginal when:
- Coherence is acceptable and runs are stable, but performance gains are inconsistent or small.
- Improvements appear only in one metric with tradeoffs in others.

Action:
- Revise policy details and rerun a bounded follow-up experiment before broadening scope.

## Failure
Classify as failure when any are true:
- Coherence/usability degrades materially.
- Long-context does not improve and short-context regresses materially.
- Instability persists (frequent crashes, hangs, or invalid artifacts).

Action:
- Kill v0 approach for now; document failure mode and revert to baseline path.

## Continue / Revise / Kill Gate
- Continue:
  - Promising classification in two consecutive bounded runs.
- Revise:
  - Marginal classification or mixed results with no hard failures.
- Kill:
  - Failure classification, or repeated marginal outcomes after one controlled revision pass.

