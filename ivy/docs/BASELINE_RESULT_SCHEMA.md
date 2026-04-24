# Baseline Result Schema (IVY)

This document defines the canonical JSON fields written to `result.json` for baseline and A/B experiments.

## File
- `result.json` (UTF-8 JSON)

## Top-Level Fields
- `run_id` (string): unique run identifier (timestamp-based is OK).
- `run_dir` (string): absolute path to the run folder.
- `timestamp_local` (string): local timestamp, ISO-like (e.g. `2026-04-24T23:59:00`).
- `model` (string): absolute model path used.
- `runtime` (string): absolute runtime binary path used.
- `flags` (object):
  - `n_gpu_layers` (number)
  - `n_cpu_moe` (number)
  - `flash_attn` (string: `on|off|auto`)
  - `threads` (number)
  - `threads_batch` (number)
  - `ctx_size` (number)
- `generation` (object):
  - `seed` (number)
  - `temperature` (number)
  - `top_k` (number)
  - `top_p` (number)
  - `min_p` (number)
  - `repeat_penalty` (number)
  - `n_predict` (number)
- `metrics` (object):
  - `prompt_n` (number): prompt token count from server timings.
  - `predicted_n` (number): predicted token count from server timings.
  - `ttft_est_ms` (number): `prompt_ms + predicted_per_token_ms` (estimated TTFT).
  - `wall_ms` (number): client wall time for the `/completion` request.
  - `decode_tps` (number): `predicted_per_second` from server timings.
  - `coherent` (boolean): simple usability heuristic (current default: output length threshold).
  - `cpu_mapped_model_buffer` (string): extracted from server stderr (e.g. `4119.38 MiB`).
  - `cuda_model_buffer` (string): extracted from server stderr (e.g. `6550.99 MiB`).

## Notes
- Raw server response must also be saved as `response.json` in the run folder.
- If additional fields are added later, keep this schema updated and version it explicitly.

