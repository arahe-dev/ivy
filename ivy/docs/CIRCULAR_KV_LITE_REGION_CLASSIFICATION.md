# Circular KV Lite v0 Region Classification (Observability Only)

This step classifies logical KV windows for traceability only.  
It does not evict, move, or rewrite KV state.

## Constants
- `window_size = 64` tokens
- `pinned_prefix_cap = 512` tokens
- `recent_tokens = 512` tokens

## Inputs
- `prompt_n` from llama-server completion timings
- `predicted_n` from llama-server completion timings

## Derived values
- `pinned_tokens = min(512, prompt_n)`
- `total_logical_tokens = prompt_n + predicted_n` (when `predicted_n` exists)
- `total_windows = ceil(total_logical_tokens / 64)`

## Logical regions
- `pinned_prefix`: first `pinned_tokens`
- `recent`: last `min(512, total_logical_tokens)` tokens, but never before pinned region
- `middle`: all tokens between pinned and recent

## Artifacts
- `result.json` includes a `kv` summary:
  - `kv_policy_mode`
  - `window_size`
  - `pinned_tokens`
  - `recent_tokens`
  - `total_logical_tokens`
  - `total_windows`
  - `pinned_windows`
  - `middle_windows`
  - `recent_windows`
  - `kv_behavior_changed = false`
- `kv_trace.jsonl` includes one no-op event per region:
  - `kv_policy_mode`
  - `kv_region`
  - `kv_action = retain`
  - `window_start`
  - `window_end`
  - `window_count`
  - `bytes_moved = 0`
  - `notes = region_classification_noop`

## Non-goals
- No KV eviction
- No KV movement
- No llama.cpp source/runtime behavior change
