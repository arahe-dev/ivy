# IVY Current State

## Adopted Stack (Frozen)

### Runtime Baseline
```
llama-server.exe \
  --n-gpu-layers 99 \
  --n-cpu-moe 16 \
  --flash-attn on \
  --threads 14 \
  --threads-batch 14 \
  --ctx-size 8192
```

### Prompt Format
V7 (Prompt Packing) - Pipe-separated, question-first

## Rejected Items

| Item | Status | Reason |
|------|--------|--------|
| V7.1 ultra-compact | REJECTED | Overfit - fails held-out quality checks |
| Output packing | REJECTED | Quality failures |

## Shelved Items

| Item | Status | Reason |
|------|--------|--------|
| Prefix/cache reuse | Shelved | Needs hot-server runner to measure |
| Circular KV Lite | Observability-only | Simulation for Qwen35MoE only |

## Best-Known Metrics

| Metric | Value |
|--------|-------|
| prompt_n | ~132 |
| TTFT | ~510ms |
| wall_ms | ~3500ms |
| Quality pass | 100% |

## Key Reports

- `COMBINED_POSITIVES_REPORT.md` - Best-known stack (V3 era)
- `AUTORESEARCH_30RUN_OPT_REPORT.md` - Current (V7 adoption, V7.1 rejection)
- This file - Current state reference