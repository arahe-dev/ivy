# IVY Prompt Packing V2 Autoresearch Log

## Iteration 1: Baseline - Ultra Format
Previous validated ultra format with pipe-separated fields.

### Metrics
- Average prompt_n: 316.4
- Average TTFT: 699.1ms
- Average Decode: 53.8 tok/s
- 5/5 quality checks passed

## Iteration 2: Mutation - JSONL Format
JSON-structured prompts with key-value pairs.

### Format Example
```json
{"role":"SRE","task":"review CR answer 5 bullets"}
{"cr":{"id":"CR-2026-0425",...}}
```

### Results
- Average prompt_n: 292.6 (-7.5%)
- Average TTFT: 697.7ms (-0.2%)
- Average Decode: 53.5 tok/s

### Decision: **Revert** - Token reduction good but flat TTFT gain

## Iteration 3: Mutation - Ultra-Minimal Format
Key:Value short labels, no JSON brackets, single-line facts.

### Format Example
```
ID: CR-2026-0425 | SVC: payment-gateway-v2 | TYPE: schema_migration | ...
REV: alice-sec|approved|PII check passed|2026-04-24
```

### Results
- Average prompt_n: 195.8 (-38.1%)
- Average TTFT: 602.2ms (-13.9%)
- Average Decode: 52.5 tok/s (-2.4%)

### Quality
- policy: 651 chars coherent
- troubleshoot: 566 chars coherent
- extraction: 385 chars coherent
- support: 524 chars coherent
- architecture: 553 chars coherent

### Decision: **KEEP** - 14% TTFT improvement meets threshold

## Commands Run
```powershell
# v2 JSONL tests
.\run_experiment.ps1 -PromptFile task1_policy_v2.jsonl
# ... (5 iterations)

# v3 ultra-minimal tests  
.\run_experiment.ps1 -PromptFile task1_policy_v3.txt
# ... (5 iterations)
```

## Summary

| Format | prompt_n | TTFT | Decode | vs Ultra |
|--------|----------|------|--------|---------|
| Ultra (baseline) | 316.4 | 699.1ms | 53.8 | - |
| v2 JSONL | 292.6 | 697.7ms | 53.5 | -7.5% / -0.2% |
| v3 mini | 195.8 | 602.2ms | 52.5 | **-38% / -14%** |

### Final Decision: **KEEP V3** - Passes all rules