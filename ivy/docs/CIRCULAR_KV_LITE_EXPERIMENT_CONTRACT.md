# Circular KV Lite v0 Experiment Contract

## Hypothesis
Circular KV Lite can improve long-context responsiveness and memory stability without breaking output coherence, while keeping short-context performance close to the frozen baseline.

## Why This Experiment Exists
- Current IVY baseline is stable and reproducible.
- Long-context workloads are the next likely bottleneck.
- Circular KV Lite is the first scoped attempt to improve that bottleneck with minimal policy complexity.

## Change vs Baseline
- Baseline behavior: stock KV handling under current frozen runtime flags.
- Experiment behavior: Circular KV Lite policy mode (`circular_kv_lite_v0_placeholder`) layered on top of the same baseline runtime setup.
- No model change, no runtime binary swap, no sampling change.

## Fixed Inputs
- Model path: `C:\bread_v2\gguf\Qwen3.6-35B-A3B-UD-IQ2_XXS.gguf`
- Runtime path: `C:\Users\arahe\dev\llama.cpp\build\bin\Release\llama-server.exe`
- Baseline flags and server settings from `qwen35_a3b_4060_baseline.yaml`
- Prompt files and generation settings (`seed`, `temperature`, `top_k`, `top_p`, `repeat_penalty`, `n_predict`)
- Artifact layout and `result.json` schema used by current IVY runners

## Validity Conditions
- Run completes with standard IVY artifacts written (`command.txt`, `request.json`, `response.json`, `output.txt`, `result.json`, logs).
- Output is coherent (`coherent=true`).
- Comparison against baseline is produced by `compare_runs.ps1`.
- For long-context case(s), experiment run finishes without crash or timeout.

## Failure Conditions
- Missing artifacts or malformed `result.json`.
- Run crashes, hangs, or returns unusable output.
- Coherence fails relative to baseline.
- Severe regressions in short-context metrics without compensating long-context benefit.

## Required Artifacts
- Run folder artifacts from experiment runner.
- Comparison JSON against baseline (`compare_vs_baseline.json`).
- Short experiment note summarizing outcome and anomalies.
- At least one short-context and one long-context run pair (baseline vs experiment).

## Comparison Dimensions
- Correctness:
  - Coherence and basic response usability vs baseline.
- TTFT:
  - `ttft_est_ms` delta for short-context and long-context.
- Wall time:
  - `wall_ms` delta for short-context and long-context.
- Decode throughput:
  - `decode_tps` delta.
- Memory behavior:
  - Buffer-related fields/logs (`cpu_mapped_model_buffer`, `cuda_model_buffer`) and stability signs in logs.
- Long-context behavior:
  - Completion success rate, latency trend, and absence of pathological degradation under larger prompts.

