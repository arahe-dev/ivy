# IVY Prompt Packing V2 Report

## Best Mutation Found
**Ultra-minimal format v3** - Key:Value short labels with compact pipe-separated facts.

## Before/After Table

| Format | prompt_n | TTFT (ms) | Decode (tok/s) | vs Ultra |
|--------|----------|-----------|---------------|---------|
| Ultra (v1 baseline) | 316.4 | 699.1 | 53.8 | - |
| **v3 ultra-minimal** | 195.8 | 602.2 | 52.5 | **-38% / -14%** |

## Per-Task Quality Checklist

| Task | V3 prompt_n | V3 TTFT | Decode | Coherent | Quality |
|------|-----------|--------|--------|----------|----------|
| policy | 172 | 596 | 52.7 | ✓ | ✓ |
| troubleshoot | 198 | 622 | 53.1 | ✓ | ✓ |
| extraction | 250 | 636 | 52.3 | ✓ | ✓ |
| support | 165 | 567 | 52.0 | ✓ | ✓ |
| architecture | 194 | 590 | 52.4 | ✓ | ✓ |

## Token Reduction
- Ultra baseline: 316.4 avg tokens
- v3 ultra-minimal: 195.8 avg tokens
- **Reduction: 38%**

## TTFT Reduction
- Ultra baseline: 699.1ms
- v3 ultra-minimal: 602.2ms
- **Reduction: 14%**

## Files Changed
- `ivy/validation_tasks/task1_policy_v3.txt` - Ultra-minimal policy
- `ivy/validation_tasks/task2_troubleshoot_v3.txt` - Ultra-minimal troubleshoot
- `ivy/validation_tasks/task3_extraction_v3.txt` - Ultra-minimal extraction
- `ivy/validation_tasks/task4_support_v3.txt` - Ultra-minimal support
- `ivy/validation_tasks/task5_architecture_v3.txt` - Ultra-minimal architecture
- `ivy/validation_tasks/task1_policy_v2.jsonl` - JSONL variant (reverted)
- `ivy/validation_tasks/task2_troubleshoot_v2.jsonl` - JSONL variant (reverted)
- `ivy/validation_tasks/task3_extraction_v2.jsonl` - JSONL variant (reverted)
- `ivy/validation_tasks/task4_support_v2.jsonl` - JSONL variant (reverted)
- `ivy/validation_tasks/task5_architecture_v2.jsonl` - JSONL variant (reverted)

## Commands Run
```powershell
# Ultra baseline (from previous validation)
.\run_experiment.ps1 -PromptFile task1_policy_ultra.txt
# ... (5 runs)

# v2 JSONL format
.\run_experiment.ps1 -PromptFile task1_policy_v2.jsonl
# ... (5 runs) 

# v3 ultra-minimal format
.\run_experiment.ps1 -PromptFile task1_policy_v3.txt
# ... (5 runs)
```

## Final Recommendation

**ADOPT v3 ultra-minimal format**

### Why
1. 14% TTFT improvement (>5% threshold) ✓
2. 38% token reduction ✓
3. All 5 tasks pass quality checks ✓
4. Decode: 52.5 tok/s (within 5% of 53.8) ✓
5. Format readable and maintainable ✓

### What to Use
For production:
- Use `KEY: Value | KEY2: Value2` format
- Short labels, no natural language glue
- Single line per entity
- Pipe-separated facts

### What NOT To Do Next
- Don't try v2 JSONL (flat TTFT, worse overall)
- Don't push past readability (no more gains without brittleness)
- Don't change model/runtime (valid constraint)