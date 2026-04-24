# IVY Output Packing Autoresearch Log

## Iteration 1: Establish Baseline Output Behavior

### Current State
- All validation tasks use n_predict=160 fixed
- Average predicted_n: 160 tokens
- Average wall_ms: ~3650ms
- Output varies by task type but maxes out at 160

## Iteration 2: Test Output Budget Mutations

### Mutation A: n_predict=80
Hypothesis: Shorter generation should reduce total latency.

### Result: FAILED - Server timeout/hang issues

### Mutation B: "BE BRIEF" / "max 3 words" instructions
Hypothesis: Prompt hints can guide shorter output.

### Result
```
prompt: "Is compliant? Answer 3 findings 2 risks. BE VERY BRIEF - max 3 words per bullet:"
predicted_n: 17
wall_ms: 937ms
coherent: false
Output:
- Schema migration
- Medium risk
- Pending approval
```

### Analysis
- Output is TOO SHORT - quality failed
- Model didn't follow 5-bullet format
- "max 3 words" was interpreted literally
- Incoherent output (17 tokens)

## Conclusion

### Baseline Metrics
- predicted_n: 160 tokens (fixed)
- wall_ms: ~3650ms average
- All tasks: coherent output

### Why No Iteration Progressed
1. Server hangs when testing smaller n_predict via custom runner
2. Brief instructions created unusable output
3. Quality constraint (required facts preserved) violated

## Decision: **NO KEEP - Revert**

Output packing requires:
- Different runner setup for variable n_predict
- More sophisticated brief language
- Quality validation which takes more iterations

### Files Tested
- task1_policy_brief.txt - too terse, failed quality

### Recommendation
- Output packing is WORTH exploring in future
- But needs:
  - Variable n_predict testing in runner
  - More iterations (12 limit already partly used)
  - Task-specific output lengths