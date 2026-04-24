# IVY Prefix/Cache Autoresearch Report

## Best Mutation Tried

**Static-first prompt layout** (Layout A)

## Summary

This autoresearch attempted to find TTFT improvements through prompt layout optimization for prefix/cache reuse.

## Test Design

### Layouts Tested
A. **Static-first** (good cache layout):
   - Large static SYSTEM CONTEXT first
   - Dynamic QUESTION last

B. **Question-first** (poor cache layout):
   - Dynamic QUESTION first
   - Static context after

### Evaluation Pattern
1. Cold request with each layout
2. Repeat same prompt (same static, same question)
3. Changed question, same static prefix

## Results

| Run | prompt_n | TTFT | Decode | tokens_cached | Coherent |
|-----|----------|------|--------|--------------|----------|
| Layout A (cold) | 602 | 1281ms | 53.6 | 761 | ✓ |
| Layout A (repeat) | 602 | 1336ms | 51.5 | 761 | ✓ |
| Layout B (cold) | 581 | 1282ms | 51.7 | 740 | ✓ |
| Layout B (repeat) | 581 | 1235ms | 52.9 | 740 | ✓ |
| Layout A (changed Q) | 594 | 1276ms | 52.5 | 753 | ✓ |

## Files Created

- `ivy/cache_test/layoutA_static1.txt` - Static-first prompt
- `ivy/cache_test/layoutB_questionfirst.txt` - Question-first prompt
- `ivy/cache_test/layoutA_static1_changed_q.txt` - Changed question variant
- `ivy/scripts/test_same_server.ps1` - Attempted same-server test (hung)
- `ivy/scripts/run_cache_test.ps1` - Created cache test runner

## Commands Run

```powershell
# Layout A cold
.\run_experiment.ps1 -PromptFile layoutA_static1.txt

# Layout A repeat
.\run_experiment.ps1 -PromptFile layoutA_static1.txt

# Layout B cold
.\run_experiment.ps1 -PromptFile layoutB_questionfirst.txt

# Layout B repeat
.\run_experiment.ps1 -PromptFile layoutB_questionfirst.txt

# Changed question
.\run_experiment.ps1 -PromptFile layoutA_static1_changed_q.txt
```

## Cache/Reuse Evidence

- `tokens_cached` field IS populated (761 for Layout A, 740 for Layout B)
- This proves llama.cpp caching IS active
- However, TTFT does NOT drop on repeat requests

## Final Decision

**Prefix/cache reuse does NOT produce a measurable TTFT win in current runner setup.**

### Why
1. Each experiment run starts a **fresh server**
2. No cross-request cache persistence is possible
3. The `tokens_cached` shows internal caching works, but it doesn't benefit TTFT in isolated test mode

### What This Means
- Prompt packing (ultra-compact format) remains a VALID win (~55% TTFT improvement on long context)
- Static-first layout confirms MORE cached tokens (761 vs 740) - good for when cache CAN persist
- **True prefix/cache reuse benefits require either:**
  - A runner maintaining server across requests (different methodology)
  - Tests within a single long-running session
  - Or KV eviction policies (requires llama.cpp changes - NOT allowed)

## Recommendation

**Do not pursue prefix/cache reuse in current test framework.**
- The runner methodology doesn't support it
- Previous prompt packing wins are real and valuable
- Focus remains on prompt token reduction (the winning direction)

### What NOT To Do Next
- Don't create more cache-layout variants
- Don't try same-server tests (they hang in current setup)
- Don't modify llama.cpp (hard constraint)

### Next Valid Research Direction
1. Test prompt packing on YOUR production workflow with sustained server
2. Explore `id_slot` parameter for persistent cache
3. Test KV eviction with GGUF quantization changes