# EVAL PLAN

Compare two configurations on identical prompts/seeds/context settings:
- A: stock substrate baseline
- B: substrate + IVY KV policy module (future Circular KV Lite runs)

## Evaluation dimensions
- Correctness: output equivalence/semantic drift checks against baseline references.
- TTFT: time-to-first-token.
- Decode throughput: tokens/sec during decode phase.
- Memory footprint: peak and average RAM/VRAM, plus bytes moved where available.
- Long-context behavior: quality/stability under larger context windows and sustained generation.

## Test protocol (initial)
- Fix model, seed, prompt set, context length, and generation params.
- Run A then B at least 3 times each to estimate variance.
- Store all artifacts under run IDs with command/output/timings/notes.
- Use trace schema v0 to attribute regressions/improvements to KV policy decisions.

## Exit criteria for first comparison
- No correctness breakage that invalidates outputs.
- Clear measurement for TTFT/throughput/memory deltas.
- Documented long-context behavior differences with trace evidence.

