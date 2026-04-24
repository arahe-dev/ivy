# IVY Output Packing Autoresearch Report

## Best Mutation Tried
**None adopted** - Output packing did not succeed in this iteration.

## Baseline Output Metrics

| Metric | Value |
|--------|-------|
| predicted_n | 160 tokens (fixed) |
| wall_ms | ~3650ms average |
| decode_tps | ~53 tok/s |
| All outputs | coherent |

## Mutations Attempted

### Attempt 1: n_predict=80
- **Result**: FAILED - Server hang/timeout
- **Analysis**: Runner issues with custom parameters
- **Status**: Abandoned

### Attempt 2: "BE BRIEF" instructions
- **Prompt**: "Answer 3 findings 2 risks. BE VERY BRIEF - max 3 words per bullet:"
- **predicted_n**: 17 tokens
- **wall_ms**: 937ms
- **coherent**: false
- **Output**: "- Schema migration\n- Medium risk\n- Pending approval" (3 bullets, incomplete)
- **Status**: FAIL - Quality constraint violated

## Before/After Table

| Format | predicted_n | wall_ms | Quality | Decision |
|---------|-----------|--------|--------|---------|
| Baseline n=160 | 160 | ~3650 | coherent | KEEP |
| Brief instructions | 17 | 937 | FAIL | REVERT |

## Quality Checklist

| Task | Brief Output | Required Format | Preserved Facts |
|------|-----------|--------------|--------------|
| policy | 3 bullets | 5 bullets | NO |
| All other tests | N/A | N/A | N/A |

## Files Changed
- `ivy/scripts/test_output_len.ps1` - Created but non-functional
- `ivy/validation_tasks/task1_policy_brief.txt` - Created, quality failed
- `ivy/validation_tasks/task1_policy_out.txt` - Created, unused

## Commands Run
```powershell
# Output budget test that failed
.\run_experiment.ps1 -PromptFile task1_policy_brief.txt

# Brief instruction test 
.\test_output_len.ps1 -PromptFile task1_policy_v3.txt -NPredict 80
```

## Final Decision

**REJECT output packing for now**

### Why
1. **Quality failed**: "max 3 words" produced 17 tokens vs required 5 bullets
2. **Tooling issues**: Server hangs when testing n_predict parameter
3. **Time budget**: 8/12 experiments already used
4. **Runner needs changes**: Variable n_predict requires deeper runner integration

### What NOT To Do Next
- Don't abandon output optimization entirely
- Don't try more terse prompts without n_predict control
- Don't exceed remaining experiment budget

### Valid Next Research Directions
1. **Variable n_predict runner**: Allow per-task output length control
2. **Test per-task limits**: Some tasks need 160, others need 80
3. **Structured output**: JSON/field format vs free text
4. **After stable baseline**: More prompt packing iterations