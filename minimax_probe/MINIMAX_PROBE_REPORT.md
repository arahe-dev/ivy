# MiniMax M2.7 split-GGUF loadability probe (llama.cpp)

Date: 2026-04-25  
Workspace: `C:\ivy\minimax_probe\`  
Model dir: `C:\minimax_2_7\`

## Question answered
**Yes** — this MiniMax split GGUF **loads** and can produce a **tiny completion** on this machine using **stock `llama.cpp`** by pointing `llama-server.exe` at **the first shard**.

Final classification: **(1) loadable and tiny completion works**

## 1) Verify files (shards)
Shards found (paths + exact sizes in bytes) are recorded in:
- `C:\ivy\minimax_probe\02_shard_check.txt`

Observed shard sizes:
- `C:\minimax_2_7\MiniMax-M2.7-UD-IQ2_XXS-00001-of-00003.gguf` = **8,237,824** bytes
- `C:\minimax_2_7\MiniMax-M2.7-UD-IQ2_XXS-00002-of-00003.gguf` = **49,754,838,912** bytes
- `C:\minimax_2_7\MiniMax-M2.7-UD-IQ2_XXS-00003-of-00003.gguf` = **15,618,537,024** bytes

First shard path (used as `-m` input):
- `C:\minimax_2_7\MiniMax-M2.7-UD-IQ2_XXS-00001-of-00003.gguf`

Directory listing captured in:
- `C:\ivy\minimax_probe\01_model_dir_listing.txt`

## 2) Confirm tools exist
Binary existence + sizes:
- `C:\ivy\minimax_probe\04_llama_bins_check.txt`

`llama-server.exe --version` output:
- `C:\ivy\minimax_probe\05_llama_server_version.txt`

## 3) CPU-only loadability probe (attempt #1)
Command (exact):
- `C:\ivy\minimax_probe\cpu_server_command.txt`

Logs:
- `C:\ivy\minimax_probe\cpu_server_stdout.txt`
- `C:\ivy\minimax_probe\cpu_server_stderr.txt`

Result:
- Split/sharded GGUF loading **worked** when pointing at shard `00001-of-00003` (the loader reports “additional 2 GGUFs metadata loaded” in `cpu_server_stderr.txt`).

### Note: transient HTTP 503 during warmup/slot init (not a model load failure)
Immediately after startup, the server returned **HTTP 503** to `/completion` and `/v1/completions` while it was still warming up / initializing slots:
- Evidence in `C:\ivy\minimax_probe\cpu_server_stderr.txt`:
  - `common_init_from_params: warming up the model with an empty run - please wait ...`
  - `srv  log_server_r: done request: POST /completion 127.0.0.1 503`
  - `srv  log_server_r: done request: POST /v1/completions 127.0.0.1 503`
  - later: `srv    load_model: initializing slots, n_slots = 4`

This was resolved by waiting and retrying the same tiny completion once (see next section).

## 4) CPU-only tiny completion
Prompt:
- `Say OK.`

Params:
- `n_predict=8`, `temperature=0`, `top_k=1`, `top_p=1`, `stream=false`

Request metadata:
- First request failures: `C:\ivy\minimax_probe\cpu_completion_meta.txt` (503s)
- Successful retry: `C:\ivy\minimax_probe\cpu_completion_retry_meta.txt`

Successful response JSON:
- `C:\ivy\minimax_probe\cpu_completion_response_retry.json`

Observed output (from `.content` in the JSON):
- ` The system will ask you to confirm the`

Timings (from server JSON):
- `prompt_ms ≈ 2761.599`, `predicted_ms ≈ 4228.932` (see `cpu_completion_response_retry.json`)

Server stop status:
- `C:\ivy\minimax_probe\cpu_server_stopped.txt`
- `C:\ivy\minimax_probe\cpu_server_taskkill_status.txt`

## 5) Merge attempt
Not attempted.

Reason:
- Split loading worked when pointing at the first shard, so merging was unnecessary.

## 6) Memory / OOM check
CPU-only load did **not** fail with OOM in this probe.

One notable observation from `cpu_server_stderr.txt`:
- The loader reports very large **CPU_Mapped model buffer sizes** (tens of GiB), consistent with the model being extremely large (metadata indicates `model params = 228.69 B`).

## 7) GPU-assisted probe (attempt #2)
Command (exact):
- `C:\ivy\minimax_probe\gpu_server_command.txt`

Key settings:
- `--n-gpu-layers 10`
- `--ctx-size 512`

Logs:
- `C:\ivy\minimax_probe\gpu_server_stdout.txt`
- `C:\ivy\minimax_probe\gpu_server_stderr.txt`

Tiny completion:
- Request metadata: `C:\ivy\minimax_probe\gpu_completion_meta.txt`
- Response JSON: `C:\ivy\minimax_probe\gpu_completion_response.json`

Observed output (from `.content`):
- ` The system will ask you to confirm the`

Server stop status:
- `C:\ivy\minimax_probe\gpu_server_stopped.txt`

## Summary (what this means for the original Unsloth Studio failure)
On this machine, `llama-server.exe` can load the split GGUF shards and generate text.

If a client reports “llama-server failed to start” for this same folder, the most plausible concrete failure mode consistent with these logs is **treating transient HTTP 503 during startup warmup/slot initialization as a hard failure**, rather than waiting for the server/model to become ready.

