# RUN ONE BASELINE (MANUAL)

1. Open `manifests/qwen_local_baseline.yaml` and confirm model path + context settings match your machine.
2. Choose one fixed prompt and write it down in `runs/2026-04-24-baseline/notes.txt`.
3. Execute one stock substrate command (no IVY KV policy modifications yet).
4. Copy the exact command into `runs/2026-04-24-baseline/command.txt`.
5. Save raw model output into `runs/2026-04-24-baseline/output.txt`.
6. Save timing/perf output into `runs/2026-04-24-baseline/timings.txt`.
7. Add hardware/build details and anomalies to `runs/2026-04-24-baseline/notes.txt`.
8. Re-run once with same seed to confirm repeatability; append notes on output/metric stability.

