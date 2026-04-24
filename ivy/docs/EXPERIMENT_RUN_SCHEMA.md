# Experiment Run Schema

Minimal schema/contract for `scripts/run_experiment.ps1`.

## Required Inputs
- One of:
  - `-ManifestPath <yaml>`
  - direct params: `ModelPath`, `RuntimePath`, `PromptFile` (+ server/generation flags)
- Required runtime context:
  - stock `llama-server.exe`
  - reachable local port

## Required Artifacts (per run folder)
- `run_started.txt`
- `status.log`
- `command.txt`
- `request.json`
- `response.json` (on success)
- `output.txt` (on success)
- `result.json` (on success)
- `failure.json` (on failure)
- `server_err.log`
- `server_out.log`
- `notes.md`

## Result Fields (`result.json`)
- `run_id`
- `run_dir`
- `timestamp_local`
- `model`
- `runtime`
- `flags`
  - `n_gpu_layers`
  - `n_cpu_moe`
  - `flash_attn`
  - `threads`
  - `threads_batch`
  - `ctx_size`
- `generation`
  - `seed`
  - `temperature`
  - `top_k`
  - `top_p`
  - `min_p`
  - `repeat_penalty`
  - `n_predict`
- `metrics`
  - `prompt_n`
  - `predicted_n`
  - `ttft_est_ms`
  - `wall_ms`
  - `decode_tps`
  - `coherent`
  - `cpu_mapped_model_buffer`
  - `cuda_model_buffer`

## Validity Expectations
- Server reaches true readiness (`/slots` responds OK).
- One `/completion` request succeeds.
- `result.json` exists and includes all fields above.
- `coherent=true` for usable output.
- On failure, `failure.json` must explain the failure reason.

