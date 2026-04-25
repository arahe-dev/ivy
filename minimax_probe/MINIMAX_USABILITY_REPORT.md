# MiniMax M2.7 bounded usability benchmark (llama.cpp)

Date: 2026-04-25  
Model (first shard): `C:\minimax_2_7\MiniMax-M2.7-UD-IQ2_XXS-00001-of-00003.gguf`  
Runtime: `C:\Users\arahe\dev\llama.cpp\build\bin\Release\llama-server.exe`  
Artifacts root: `C:\ivy\minimax_probe\usability\`

## Goal / thresholds
Keep front-of-mind thresholds:
- **Serious/dev model:** 20+ tok/s decode + tolerable TTFT
- **Future stress target:** 10–20 tok/s or high TTFT but coherent
- **Shelve:** under 10 tok/s, unstable, or memory pressure too severe

## Prompt + decoding settings (fixed)
Prompt:
> Write a concise explanation of why MoE models can run faster than dense models on constrained hardware. Use 5 bullets.

Completion:
- `n_predict=80`
- `seed=12345`
- `temperature=0`, `top_k=1`, `top_p=1`
- `stream=false`

Notes on metrics:
- `decode_tps` is taken from server JSON as `timings.predicted_per_second`.
- TTFT is approximated by `timings.prompt_ms` (server-side prompt evaluation time). With `stream=false` the server does not provide a direct “first token” timestamp.
- `wall_ms` is total client request wall time (PowerShell `Measure-Command`).

## Results

### Config 1: CPU-only (`--n-gpu-layers 0`, `--ctx-size 2048`)
Command:
- `C:\ivy\minimax_probe\usability\cpu_ctx2048_gpu0\server_command.txt`

Logs:
- `C:\ivy\minimax_probe\usability\cpu_ctx2048_gpu0\server_stderr.txt`
- `C:\ivy\minimax_probe\usability\cpu_ctx2048_gpu0\server_stdout.txt`

Completion artifacts:
- `C:\ivy\minimax_probe\usability\cpu_ctx2048_gpu0\completion_meta.txt`
- `C:\ivy\minimax_probe\usability\cpu_ctx2048_gpu0\completion_response.json`

Metrics:
- `prompt_n=24`, `predicted_n=80`
- `TTFT_proxy_prompt_ms=13140.04`
- `wall_ms=64112`
- `decode_tps=1.57695`

Output coherence:
- Coherent bullet list, deterministic; starts with a slightly odd preamble but contains correct MoE vs dense points.

Memory / buffers (from stderr):
- CPU mapped buffers: `CPU_Mapped model buffer size = 47449.88 MiB` and `14894.99 MiB`
- CUDA compute buffer (even with `--n-gpu-layers 0`): `CUDA0 compute buffer size = 726.45 MiB`

### Config 2: GPU small (`--n-gpu-layers 10`, `--ctx-size 2048`)
Command:
- `C:\ivy\minimax_probe\usability\gpu_ctx2048_gpu10\server_command.txt`

Logs:
- `C:\ivy\minimax_probe\usability\gpu_ctx2048_gpu10\server_stderr.txt`
- `C:\ivy\minimax_probe\usability\gpu_ctx2048_gpu10\server_stdout.txt`

Completion artifacts:
- `C:\ivy\minimax_probe\usability\gpu_ctx2048_gpu10\completion_meta.txt`
- `C:\ivy\minimax_probe\usability\gpu_ctx2048_gpu10\completion_response.json`

Metrics:
- `prompt_n=24`, `predicted_n=80`
- `TTFT_proxy_prompt_ms=9502.217`
- `wall_ms=46215`
- `decode_tps=2.18622`

Output coherence:
- Coherent bullet list, deterministic; similar content to CPU-only run.

Memory / VRAM notes (from stderr):
- CPU mapped buffers: `CPU_Mapped model buffer size = 47120.17 MiB` and `5940.65 MiB`
- CUDA compute buffer: `CUDA0 compute buffer size = 489.03 MiB`
- Memory pressure warning during `-fit` step:
  - `projected to use 9845 MiB ... vs. 7106 MiB free`
  - `failed to fit ... n_gpu_layers already set by user to 10, abort`
  - This run still completed, but it indicates the configuration is near/over the GPU free-memory envelope per llama.cpp’s fit heuristic.

## Skipped configs (to stop after classification)
Configs 3 and 4 were not run:
- GPU moderate (`--n-gpu-layers 20`)
- GPU higher (`--n-gpu-layers 30`)

Reason:
- Both CPU-only and GPU(10) decode throughput is **far below 10 tok/s**, so further increasing `--n-gpu-layers` is unlikely to change the overall usability classification on this machine for this model.

## Final classification
**(3) shelve** — decode is ~**1.6–2.2 tok/s** with very high TTFT proxies (~**9.5–13.1s**), even for a short 80-token completion.

