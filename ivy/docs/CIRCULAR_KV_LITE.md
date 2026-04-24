# CIRCULAR KV LITE

## Problem
Long-context local runs degrade when KV cache residency policy is naive; memory pressure and movement hurt latency and stability.

## Non-goals
- Rewriting substrate attention kernels.
- Solving all KV strategies at once.
- Distributed/multi-node policy orchestration.

## First implementation scope
- Add a minimal circular buffer style KV policy layer that decides retention/eviction windows.
- Keep integration thin: policy logic + instrumentation hooks only.
- Run on one model, one substrate path, fixed seed, fixed prompts.

## Explicitly deferred
- MoE KV policy.
- SSD/offload orchestration as productized system.
- Adaptive learned policy selection.
- Cross-model generalized policy engine.

## Metrics that matter
- Correctness drift vs stock baseline output.
- TTFT change.
- Decode throughput change.
- Peak/average memory footprint.
- Behavior at longer contexts (stability, truncation effects, quality degradation patterns).

## Successful first experiment
- Stock baseline and Circular KV Lite runs are both reproducible from manifests.
- Circular KV Lite shows measurable memory-behavior change with bounded correctness impact.
- Trace artifacts are sufficient to explain where policy helps or hurts.

