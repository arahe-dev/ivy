# Experiment Contract (IVY)

This repository treats performance experiments as *reproducible runs* with explicit validity checks and artifacts.

## Hypothesis
Changing one or more experiment variables (vs a known baseline) will produce a measurable improvement (or regression) on:
- TTFT (time-to-first-token)
- Total wall time for a fixed `n_predict`
- Decode throughput (tokens/sec)

## Fixed Inputs (Must Not Change)
- Model file (exact path + file hash if available)
- Runtime binary (exact path, build commit/version if available)
- Hardware + driver context (CPU/GPU model; CUDA driver/runtime)
- Prompt text file contents
- Generation settings (`seed`, `temperature`, `top_k`, `top_p`, `repeat_penalty`, `n_predict`)
- Measurement method (how `wall_ms` and `ttft_est_ms` are computed)

## Validity Conditions (Run Is Valid Only If)
- The `llama-server` process starts and serves `/completion`.
- The request completes without crashing or timing out.
- The result artifact contains all required fields from `docs/BASELINE_RESULT_SCHEMA.md`.
- `coherent=true` by the run’s coherence heuristic (currently: output length and bullet formatting sanity).

## Failure Conditions (Stop And Mark Invalid)
- Server fails to start, exits early, or `/completion` fails after retries.
- Output is empty/garbled, or violates the response contract for the prompt.
- Timings are missing or obviously corrupted (e.g. negative durations).

## Required Artifacts (Per Run Folder)
- `command.txt` (exact server command line)
- `request.json` (exact `/completion` request payload)
- `response.json` (raw `/completion` JSON response)
- `output.txt` (model text output only)
- `server_err.log` (stderr logs; includes placement buffers)
- `result.json` (normalized result in the schema)
- `notes.md` (human notes; optional, but present as a file)

## Decision At The End
For any A/B change:
- **Adopt** if it improves the primary metric(s) by a meaningful margin *and* passes validity.
- **Reject** if it regresses primary metrics, reduces stability, or fails validity.
- **Defer** if results are inconsistent (needs repeats) or environment changed.

