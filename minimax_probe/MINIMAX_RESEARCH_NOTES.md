# MiniMax M2.7 Autoresearch Notes

## Baseline Results (from prior probe)
- CPU-only (--n-gpu-layers 0): decode 1.58 tok/s, TTFT ~13.1s
- GPU small (--n-gpu-layers 10): decode 2.19 tok/s, TTFT ~9.5s, VRAM fit warning

## Key Research Findings

### From Flash-MoE (danveloper/flash-moe)
- Uses SSD expert streaming (~4 tok/s on 48GB MacBook)
- "Trust the OS" page cache achieved 71% hit rate
- Key insight: Only K=4 active experts per token are needed
- NOT APPLICABLE: No custom SSD streaming in llama.cpp

### From Llama.cpp PRs
- `--cpu-moe` or `-cmoe`: Keep ALL MoE weights in CPU
- `--n-cpu-moe N`: Keep first N MoE layers in CPU
- Tensor override pattern: `\.(ffn_up|ffn_down|gate)_exps` to CPU
- This keeps dense attention and QKV on GPU

## Hardware Context
- GPU: RTX 4060 Laptop, 8GB VRAM
- Total VRAM: 8187 MiB detected, ~7106 MiB free at load
- Model: MiniMax-M2.7-UD-IQ2_XXS (~47GB CPU-mapped when loaded)

## Hypotheses to Test

### H1: CPU-MOE via --cpu-moe flag
- Keep all MoE weights on CPU, QKV on GPU
- Hypothesis: Reduces VRAM pressure, may improve throughput vs forced GPU offload
- Expected: Small improvement or similar throughput

### H2: Selective CPU-MOE via --n-cpu-moe
- Keep some MoE layers on CPU, rest on GPU
- Use n-gpu-layers for dense layers + mixed MoE offload
- Hypothesis: Finds sweet spot between VRAM and compute

### H3: Extreme low VRAM (minimal GPU layers + CPU-MOE)
- CPU-MOE + minimal GPU layers (e.g., 5-8)
- Reduces VRAM requirement, avoids warnings
- Hypothesis: May enable larger model portion on GPU without OOM

### H4: Reduced context size
- Lower --ctx-size (e.g., 512 or 1024)
- Combined with CPU-MOE
- Hypothesis: Reduces KV cache pressure

### H5: Flash Attention toggle
- Test --flash-attn on vs off with CPU-MOE
- Hypothesis: May matter differently with CPU-MOE routing

## Practical Experiments Ranked

| Rank | Hypothesis | Expected Upside | Risk | Time |
|------|------------|-----------------|------|------|
| 1 | H1: --cpu-moe + n-gpu-layers 0 | Low | Low | Fast |
| 2 | H1: --cpu-moe + n-gpu-layers 10 | Medium | Low | Fast |
| 3 | H2: --n-cpu-moe N sweep | Medium | Medium | Med |
| 4 | H3: CPU-MOE + low n-gl | Medium | Low | Fast |

## Technical Notes
- MiniMax is an MoE with many experts per layer
- IQ2_XXS is extremely quantized (~2bit equiv)
- CPU-mapped is ~47GB, VRAM needed only for active compute
- Target: >= 8 tok/s decode

## Constraints
- Max 25 server load attempts
- Max 20 min per attempt
- Stop if 5 consecutive failures

## Repo References
- https://github.com/danveloper/flash-moe - SSD streaming concept
- https://github.com/ggml-org/llama.cpp - --cpu-moe flags
- https://github.com/karpathy/autoresearch - methodology