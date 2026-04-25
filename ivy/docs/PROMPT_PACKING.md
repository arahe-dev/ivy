# Prompt Packing Guide

## Adopted Format: V7

The V7 Prompt Packing format is the adopted standard for IVY production prompts.

## V7 Format Specification

```
CR:2026-0425|payment|schema|2026-04-26|02-04|MED|NO-Schema|REVERT|SEC:PENDING|OPS:APPROVED|PII:NO|5MIN|HEALTH
A:sec|OK|PII|20260424
B:ops|OK|window|20260424
C:arch|OK|size|20260425
compliant?3find+2risk
```

### Key Principles
1. Use pipe-separated fields (`|`) instead of multi-line blocks
2. Put Question BEFORE detailed context
3. Use abbreviated but readable field labels
4. Keep all context on minimal lines

## Metrics

| Metric | Original | V7 | Improvement |
|--------|----------|-----|--------------|
| prompt_n | 316 | 132 | -58% |
| TTFT | 699ms | 510ms | -27% |
| wall_ms | 3676ms | 3500ms | -5% |
| Quality | 100% | 100% | ✓ |

## Format Variants

| Version | Description | Status |
|---------|-------------|--------|
| V3 | Ultra-minimal format | SUPERSEDED |
| V6 | Question-first | SUPERSEDED |
| V7 | Adopted | CURRENT |
| V7.1 | Ultra-compact | REJECTED (overfit) |

## Why V7.1 Was Rejected

V7.1 ultra-compact format (~54 tokens) was tested but REJECTED:
- Held-out validation failed (2/3 tasks failed quality)
- Policy task: Output was gibberish
- Reasoning task: Misinterpreted as word puzzle
- Over-compression loses critical context

## Validation Tasks Location

All prompt variants are in `ivy/validation_tasks/`:
- `task1_policy_v7.txt` - Policy compliance
- `task2_troubleshoot_v7.txt` - Troubleshooting
- `task3_extraction_v7.txt` - Data extraction
- `task4_support_v7.txt` - Support tickets
- `task5_architecture_v7.txt` - Architecture review