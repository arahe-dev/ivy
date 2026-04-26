# IVY Results

This document summarizes the main IVY findings so far. It is more detailed than the README but intentionally avoids raw log dumps.

## Test Environment

- RTX 4060 Laptop GPU, 8 GB VRAM
- about 48 GB RAM
- Intel i7-13650HX
- Windows
- stock `llama.cpp` CUDA build

## Q2/IQ2 Track

Model:

```text
C:\bread_v2\gguf\Qwen3.6-35B-A3B-UD-IQ2_XXS.gguf
```

Key findings:

- Very fast when tuned with MoE-aware placement.
- Earlier best practical speed was roughly 50+ tok/s.
- Prompt Packing V7 reduced prompt tokens by about 58% versus the original and reduced TTFT by about 27%.
- V7.1 was rejected as overfit after fresh held-out failures.

Why it is not the main agent path:

- `<think>` contamination appeared in raw tool workflows.
- Markdown fences appeared where strict JSON was required.
- JSON/tool safety was not reliable enough for the main agent/tool path.

Decision:

Q2/IQ2 is on the backburner for raw tool use. It remains useful for fast human-facing prose, chat, and research workflows.

## Q4_K_M Track

Model:

```text
C:\bread_v2\gguf\Qwen3.6-35B-A3B-UD-Q4_K_M.gguf
```

Best selected stock `llama.cpp` config:

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

Optimization findings:

| Attempt | Decode tok/s | Notes |
|---|---:|---|
| Q2 placement transfer: `ngl99 ncmoe16` | 7.534 | Poor transfer to Q4_K_M |
| `ncmoe24` | 10.373 | Still slow |
| `ngl99 ncmoe32` | 29.907 | Near practical threshold |
| `ngl50 ncmoe32` | 31.794 | Good placement |
| selected q4 KV | 32.159 | Best TTFT/decode tradeoff |
| `b1024 ub256` | 32.212 | Absolute fastest measured 160-token decode |
| `cpu-moe` safe fallback | 29.124 | Lower VRAM pressure |

Selected result:

- Practical stock `llama.cpp` baseline around 32 tok/s.
- Prompt timing / TTFT proxy around 359 ms in the optimization report.
- Clean reasoning-off behavior in the tested chat path.
- 25-case tool benchmark: 96% raw strict pass, 100% final pass with validator/retry.
- No `<think>` tags or markdown fences in the tested path.

Decision:

Q4_K_M is the main local agent/tool candidate with parser/validator/retry.

## Q4_K_M Tool Safety Benchmark

Benchmark report:

```text
C:\ivy\ivy\docs\results\Q4KM_TOOL_BENCHMARK_25.md
```

Summary:

| Metric | Value |
|---|---:|
| Total cases | 25 |
| Raw strict pass rate | 96% |
| Cleaned pass rate | 96% |
| Repaired pass rate | 100% |
| Final pass rate | 100% |
| Retry count | 1 |
| Average prompt_ms | 1837.218 |
| Average wall_ms | 3343.540 |
| Average decode_tps | 33.246 |

The benchmark covered simple tool selection, missing-information `ask_user` cases, unsafe command handling, second-turn tool-result-to-action prompts, and nested schema/enum/argument-shape cases.

The only raw failure was an unsafe-command case where Q4_K_M selected `run_shell` instead of `ask_user`. The validator caught `forbidden_tool:run_shell`, `wrong_tool:run_shell`, a missing required `question` argument, and an invented `command` argument. One repair attempt produced the expected `ask_user` JSON.

Decision:

Q4_K_M is usable as a local tool agent with validator/retry. It should not be treated as safe for direct raw tool execution.

## Q4_K_M Hot-Session Track

Validated pattern:

- long-lived `llama-server`
- fixed `id_slot`
- `cache_prompt=true`
- stable static prefix first
- dynamic task suffix last

Validation results:

| Run | prompt_n | prompt_ms | decode_tps | Classification |
|---|---:|---:|---:|---|
| cold | 683 | 3263.614 | 31.818 | `cold_or_lost_reuse` |
| repeat same | 4 | 77.850 | 31.456 | `likely_hot_reuse` |
| changed tail | 514 | 1782.776 | 31.173 | `partial_reuse` |

Key reductions:

- Exact repeat prompt time reduction: about 97.6%.
- Changed-tail prompt time reduction: about 45.4%.

Decision:

Adopt the Q4_K_M hot-session runner as IVY's main local agent path.

## MiniMax M2.7 Track

Model:

```text
MiniMax-M2.7 IQ2_XXS split GGUF
```

Findings:

- It loads locally.
- Tiny completions work.
- CPU-only usability benchmark was around 1.58 tok/s.
- GPU-assisted `--n-gpu-layers 10` was around 2.19 tok/s.

Decision:

Shelve MiniMax as a practical development model on this hardware. Keep it as a behemoth/stress research target.

## Circular KV Lite

Built:

- mechanics spec
- region classification
- pressure simulation
- runtime capability gate

Finding:

The Qwen35MoE runtime reports partial sequence removal is not supported. Real middle-window eviction is disabled for this model.

Decision:

Circular KV Lite remains observability/simulation-only for now.

## Autoresearch Lessons

- Prompt Packing V7 was adopted; V7.1 was rejected as overfit.
- Prefix/cache reuse failed in an early one-shot runner shape, then succeeded when tested with the correct hot-server architecture.
- Output packing failed due quality/tooling issues.
- Reporting autoresearch now produces pass/warn/fail-style recommendations.
- The Q4_K_M optimization loop found a practical 32 tok/s stack.
- Hot-session benchmarking proved that large prompt-time reductions are available without changing `llama.cpp` or the GGUF.

## Current Recommendation

Use Q4_K_M hot-session mode for local agent/tool workflows. Keep Q2/IQ2 as a fast non-tool lane. Keep MiniMax and Circular KV Lite as research tracks, not production paths.
