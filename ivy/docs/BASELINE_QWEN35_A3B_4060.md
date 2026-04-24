# Baseline: Qwen3.6-35B-A3B (IQ2_XXS) on RTX 4060 Laptop (8GB)

## Model
- `C:\bread_v2\gguf\Qwen3.6-35B-A3B-UD-IQ2_XXS.gguf`

## Runtime
- Stock `llama.cpp` CUDA build (`llama-server.exe`)
- `C:\Users\arahe\dev\llama.cpp\build\bin\Release\llama-server.exe`

## Frozen Flags
- `--n-gpu-layers 99`
- `--n-cpu-moe 16`
- `--flash-attn on`
- `--threads 14`
- `--threads-batch 14`
- `--ctx-size 8192`
- (server convenience) `-np 1 --no-webui`

## Measured Performance (Interactive /completion)
These numbers are from bounded confirmation runs with deterministic-ish sampling:
- `n_predict=160`, `seed=12345`, `temperature=0`, `top_k=1`, `top_p=1`, `repeat_penalty=1`

Observed ranges:
- TTFT (estimated): ~`0.60s` to `0.84s`
- Decode throughput: ~`50.7` to `54.1` tok/s
- Total wall time: ~`3.55s` to `4.00s`

## Caveat
This baseline is model + hardware specific. Re-validate after any of:
- model quant change
- llama.cpp rebuild / commit change
- driver/CUDA/runtime changes

