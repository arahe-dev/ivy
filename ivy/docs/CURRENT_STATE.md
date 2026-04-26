# IVY Current State

## Current Best Model And Config

Current local agent/tool candidate:

```text
Qwen3.6-35B-A3B-UD-Q4_K_M.gguf
```

Runtime:

```text
C:\Users\arahe\dev\llama.cpp\build\bin\Release\llama-server.exe
```

Model:

```text
C:\bread_v2\gguf\Qwen3.6-35B-A3B-UD-Q4_K_M.gguf
```

Flags:

```powershell
--n-gpu-layers 50
--n-cpu-moe 32
--threads 14
--threads-batch 14
--flash-attn on
--ctx-size 8192
--cache-type-k q4_0
--cache-type-v q4_0
--reasoning off
--reasoning-budget 0
--cache-prompt
```

Measured baseline:

- Selected Q4_K_M config: about 32.159 tok/s.
- Prompt timing / TTFT proxy in optimization report: about 359 ms.
- Reasoning-off behavior: clean in tested chat path.
- Tool benchmark: 25 cases, 96% raw strict pass, 100% final pass with validator/retry.
- Markdown fences / `<think>` tags: not observed in the selected tested path.

## Current Agent Path

Main agent path:

```text
Q4_K_M + stock llama.cpp + q4 KV cache + reasoning off + hot-session runner
```

Request pattern:

- long-lived `llama-server`
- fixed `id_slot`
- `cache_prompt=true`
- stable IVY static prefix first
- dynamic task suffix last

Hot-session validation:

| Run | prompt_n | prompt_ms | decode_tps | Classification |
|---|---:|---:|---:|---|
| cold | 683 | 3263.614 | 31.818 | `cold_or_lost_reuse` |
| repeat same | 4 | 77.850 | 31.456 | `likely_hot_reuse` |
| changed tail | 514 | 1782.776 | 31.173 | `partial_reuse` |

Decision: adopt Q4_K_M hot-session runner as IVY's main local agent path.

## Tool Safety Baseline

Q4_K_M now has a measured 25-case tool benchmark:

| Metric | Value |
|---|---:|
| Raw strict pass rate | 96% |
| Final pass rate with one retry | 100% |
| Retry count | 1 |
| Average decode speed | 33.246 tok/s |

The only raw failure was an unsafe-command case where the model selected `run_shell` instead of `ask_user`. The validator caught the failure and the repair pass produced the expected `ask_user` call.

Decision: Q4_K_M is usable as the local tool agent with parser/validator/retry. Raw model output should not be executed directly.

## Backburner Items

| Item | Status | Reason |
|---|---|---|
| Q2/IQ2 raw tool path | Backburner | Fast, but not trusted for strict raw tool calling |
| Q2/IQ2 human prose path | Available | Useful for fast human-facing prose/chat/research |
| V7.1 prompt format | Rejected | Overfit after fresh held-out failures |
| Output packing | Backburner | Quality/tooling issues |
| MiniMax M2.7 | Shelved as practical model | Loads and runs, but local speed is about 2 tok/s |
| Circular KV Lite eviction | Observability-only | Runtime lacks partial sequence removal support for this model |

## Next Three Build Steps

1. Expand Q4_K_M tool testing from 25 cases to a larger adversarial suite.
2. Add optional slot save/restore or session persistence experiment.
3. Build execution gating around validator verdicts and human-confirmation requirements.
