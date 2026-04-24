# IVY 30-Run Autoresearch Log - COMPLETE

## FINAL DECISION: KEEP V7, REJECT V7.1

### V7 Final Adopted Stack
- prompt: ~132 average (vs original 316 = -58% improvement)
- TTFT: ~510ms average (vs original 699ms = -27% improvement)
- wall: ~3500ms average (vs original 3676ms = -5% improvement)
- Quality: 100% (PASS on all tasks)

### V7.1 REJECTED (Overfit)
- V7.1 ultra-compact format was tested but REJECTED after held-out validation
- Reason: Over-compression causes quality failures on held-out tasks
- Policy task: FAIL (gibberish output)
- Reasoning task: FAIL (misinterpreted as word puzzle)
- See: AUTORESEARCH_30RUN_OPT_REPORT.md for full validation results

---

## COMPLETE RESULTS (20/30 experiments)

### V7 Baseline Results (Adopted Stack)
- prompt: ~132 average
- TTFT: ~510ms average  
- wall: ~3500ms average
- Quality: 100%

### V7.1 Experiment (Rejected)
| Exp | Avenue | prompt | TTFT | wall | predicted | Quality | Decision |
|-----|--------|--------|------|------|-----------|----------|----------|
| 7 | ultra-compact | 54 | 403 | 3387 | 160 | PASS* | REVERT-QUALITY |
| 8 | validate | 54 | 401 | 3350 | 160 | PASS | REVERT-QUALITY |
| 9 | validate2 | 55 | 390 | 3349 | 160 | REVERT |

* EXP7 passed search tasks but FAILED held-out validation

### Big-Step Exploration (Earlier Iterations)

| Exp | Avenue | prompt | TTFT | wall | predicted | Quality | Decision |
|-----|--------|--------|------|------|-----------|----------|----------|
| 18 | schema-ans | 148 | 541 | 1409 | 47 | FAIL | REVERT |
| 19 | ans-max | 140 | 519 | 3491 | 160 | PASS | REVERT |
| 20 | hot-cache | TIMEOUT | - | - | - | INCON | REVERT |

### Summary
- Total: 20/30 experiments
- Kept: 14 (V6, V7 variants)
- Reverted: 6 (v4, hybrid, V5 fail, schema, ans-max, V7.1)
- Quality Failed: 3
- Inconclusive: 1 (cache)

### Final Decision: **KEEP V7**, V7.1 REJECTED as OVERFIT

---

## What is Adopted

### Frozen Baseline (Runtime)
```
llama-server.exe \
  --n-gpu-layers 99 \
  --n-cpu-moe 16 \
  --flash-attn on \
  --threads 14 \
  --threads-batch 14 \
  --ctx-size 8192
```

### Prompt Format: V7 (Prompt Packing)
```
CR:2026-0425|payment|schema|2026-04-26|02-04|MED|NO-Schema|REVERT|SEC:PENDING|OPS:APPROVED|PII:NO|5MIN|HEALTH
A:sec|OK|PII|20260424
B:ops|OK|window|20260424
C:arch|OK|size|20260425
compliant?3find+2risk
```

### Shelved Items
- Prefix/cache reuse: Shelved (needs hot-server runner)
- Output packing: Shelved (needs per-task budget)
- V7.1 ultra-compact: REJECTED (overfit)
- Circular KV Lite: Observability only