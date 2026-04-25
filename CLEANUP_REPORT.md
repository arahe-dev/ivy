# IVY Cleanup Report

## Session: 2026-04-25

### Task
Cleanup/documentation - not performance optimization

---

## Files Changed

### Created/Updated

| File | Action | Notes |
|------|--------|-------|
| `README.md` | Updated | Main README with current stack |
| `ivy/docs/PROMPT_PACKING.md` | Created | V7 format guide |
| `ivy/docs/CURRENT_STATE.md` | Created | State reference |
| `ivy/docs/NEXT_STEPS.md` | Created | Future work |

### Updated (Stale Claims Fixed)

| File | Change |
|------|--------|
| `AUTORESEARCH_30RUN_OPT_LOG.md` | Updated final decision to KEEP V7 |
| `AUTORESEARCH_30RUN_OPT_REPORT.md` | Full rewrite with V7.1 rejection |
| `COMBINED_POSITIVES_REPORT.md` | Added note about V7 evolution |
| `PROMPT_PACKING_VALIDATION.md` | Added V7/V7.1 note |
| `AUTORESEARCH_PROMPT_PACKING_V2_REPORT.md` | Added note about V7 |
| `AUTORESEARCH_PREFIX_CACHE_REPORT.md` | Updated reference to V7 |

---

## Final State

### Adopted Stack (Frozen)

**Runtime Baseline:**
```
llama-server.exe \
  --n-gpu-layers 99 \
  --n-cpu-moe 16 \
  --flash-attn on \
  --threads 14 \
  --threads-batch 14 \
  --ctx-size 8192
```

**Prompt Format: V7 (Prompt Packing)**
- ~132 prompt tokens
- ~510ms TTFT
- ~3500ms wall
- 100% quality pass

### Rejected Items

| Item | Status | Reason |
|------|--------|--------|
| V7.1 ultra-compact | REJECTED | Overfit - fails held-out validation |
| Output packing | REJECTED | Quality failures |

### Shelved Items

| Item | Status | Reason |
|------|--------|--------|
| Prefix/cache reuse | Shelved | Needs hot-server runner |
| Circular KV Lite | Observability-only | Qwen35MoE only |

---

## What Was Fixed

1. Updated AUTORESEARCH_30RUN_OPT_LOG.md and REPORT.md with correct final decision
2. Added notes to older reports about V7 evolution from V3
3. Added notes about V7.1 rejection to key documents
4. Created new docs for V7 format, current state, next steps

---

## Next Recommended Build

| Priority | Item |
|----------|------|
| P0 | Hot-server runner (for cache testing) |
| P1 | V7 format integration tests |
| P2 | Circular KV Lite documentation |

---

## Key References

- `ivy/docs/PROMPT_PACKING.md` - V7 format spec
- `ivy/docs/CURRENT_STATE.md` - Quick state reference  
- `ivy/docs/NEXT_STEPS.md` - Future work
- `AUTORESEARCH_30RUN_OPT_REPORT.md` - Full V7/V7.1 history