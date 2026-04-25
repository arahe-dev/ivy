# llama.cpp MoE Autotune Results

Mode: benchmark
Reasoning: disabled (--reasoning-budget 0 injected)

## Machine summary
- OS: Windows-10-10.0.26200-SP0
- CPU: 13th Gen Intel(R) Core(TM) i7-13650HX
- RAM total bytes: 51233284096
- GPU 0: NVIDIA GeForce RTX 4060 Laptop GPU total=8188 MiB free=7956 MiB

## Model summary
- Path: C:\minimax_2_7\MiniMax-M2.7-UD-IQ2_XXS-00001-of-00003.gguf
- Size bytes: 8237824
- Architecture: minimax-m2
- Name: Minimax-M2.7
- Layers/block count: 62
- Context length: 196608
- Experts: 256
- Experts used: 8

## Supported flags
- `--cpu-moe`: True
- `--direct-io`: True
- `--fit`: True
- `--fit-ctx`: True
- `--fit-target`: True
- `--mmap`: True
- `--n-cpu-moe`: True
- `--no-display-prompt`: True
- `--override-tensor`: True
- `--reasoning-budget`: True
- `--seed`: True
- `--single-turn`: True
- `-ctk`: True
- `-ctv`: True
- `-ngl`: True
- `-ub`: True

## Tested candidates
- Candidate count generated: 1
- Candidate count executed: 1

## Top 5 configs
- Rank 1: candidate 0 `survival_smoke` outcome=timeout decode_tps=None wall_s=124.835 score=-1100.0

## Failed configs summary
- timeout: 1

## Interpretation
- Prefer the best config only if it is stable across repeated short prompts.
- Treat estimated decode rates as lower confidence than parsed llama.cpp timings.

## Next recommended experiments
- Re-run the top 2 configs with a longer but still bounded prompt set.
- If GPU memory warnings appear, reduce `-ngl`, context, batch, or KV precision before increasing scope.
- Consider tensor override experiments only after tensor categories are identified with confidence.
