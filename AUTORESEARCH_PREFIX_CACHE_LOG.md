# IVY Prefix/Cache Autoresearch Log

## Iteration 1: Establish Baseline - Static-First vs Question-First Layout

### Hypothesis
Placing static system context FIRST and dynamic question LAST should maximize cache reuse, because the model can cache the static prefix and only process the new question portion.

### Mutation
Created two prompt layouts:
- Layout A: Static context FIRST, then question (good for cache)
- Layout B: Question FIRST, then static context (bad for cache)

### Expected
Layout A should show lower TTFT on repeated requests due to better cache utilization.

### Command Runs
```powershell
# Cold baseline (layout A - static first)
.\run_experiment.ps1 -PromptFile layoutA_static1.txt

# Repeat same prompt (layout A)
.\run_experiment.ps1 -PromptFile layoutA_static1.txt

# Cold baseline (layout B - question first)
.\run_experiment.ps1 -PromptFile layoutB_questionfirst.txt

# Repeat same prompt (layout B)
.\run_experiment.ps1 -PromptFile layoutB_questionfirst.txt

# Changed question, same static (layout A)
.\run_experiment.ps1 -PromptFile layoutA_static1_changed_q.txt
```

### Results
| Run | prompt_n | ttft_est_ms | decode_tps | tokens_cached | coherent |
|------|----------|-----------|-----------|------------|------------|----------|
| cache_coldA | 602 | 1281 | 53.6 | 761 | true |
| cache_repeatA | 602 | 1336 | 51.5 | 761 | true |
| cache_coldB | 581 | 1282 | 51.7 | 740 | true |
| cache_repeatB | 581 | 1235 | 52.9 | 740 | true |
| cache_changedA | 594 | 1276 | 52.5 | 753 | true |

### Analysis
- tokens_cached IS populated - llama.cpp caching is active
- NO TTFT improvement on repeat requests - each run starts a NEW server
- Layout A shows MORE cached tokens (761 vs 740) - confirms static-first is better
- Changed question shows partial cache reuse (753 cached vs 761)

### Decision: **NO KEEP - No measurable TTFT win**
- The runner starts a fresh server for each request
- No cross-request cache persistence is possible
- tokens_cached shows internal cache works but doesn't benefit TTFT

### Reason
The current runner methodology doesn't support sustained server connections. Each request gets a fresh server, meaning there's no way to observe cross-request cache effects in this test setup. The prompt packing wins remain valid but prefix/cache reuse requires either:
1. A runner that maintains server across multiple requests, OR
2. Tests within a single long-running session