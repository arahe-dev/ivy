# A/B Compare Schema

This schema defines the output fields for `scripts/compare_runs.ps1`.

## Inputs
- `baseline_run_dir`: absolute path to a run folder containing `result.json`
- `experiment_run_dir`: absolute path to a run folder containing `result.json`

## Output Fields
- `baseline_run_id` (string)
- `experiment_run_id` (string)
- `baseline_wall_ms` (number)
- `experiment_wall_ms` (number)
- `wall_ms_delta` (number): `experiment - baseline` (negative is better)
- `baseline_ttft_est_ms` (number)
- `experiment_ttft_est_ms` (number)
- `ttft_est_ms_delta` (number): `experiment - baseline` (negative is better)
- `baseline_decode_tps` (number)
- `experiment_decode_tps` (number)
- `decode_tps_delta` (number): `experiment - baseline` (positive is better)
- `baseline_coherent` (bool)
- `experiment_coherent` (bool)
- `baseline_cpu_mapped_model_buffer` (string or null)
- `experiment_cpu_mapped_model_buffer` (string or null)
- `baseline_cuda_model_buffer` (string or null)
- `experiment_cuda_model_buffer` (string or null)
- `recommendation` (string): short line based on wall/ttft/decode/coherence

## Recommendation Rule (simple)
- If experiment is coherent and improves wall time, recommend experiment.
- Otherwise recommend baseline.

