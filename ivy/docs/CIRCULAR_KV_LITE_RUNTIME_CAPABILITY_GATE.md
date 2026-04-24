# Circular KV Lite Runtime Capability Gate

Circular KV Lite must not attempt real middle-window eviction unless the runtime is partial sequence removal capable.

## Why this gate exists
- Real middle-window eviction requires range removal semantics (`seq_rm`) that can safely remove interior token ranges.
- In llama.cpp, capability varies by memory type:
  - `part`: partial range removal supported
  - `full`: only whole-sequence style behavior is safe
  - `no`: sequence removal not supported
- Qwen35/Qwen35MoE can run with hybrid/recurrent memory paths where partial removal may be unavailable.

## Current IVY policy
- IVY does not perform real KV eviction yet.
- IVY records runtime capability and policy status in `result.json.kv`:
  - `seq_rm_capability`: `unknown|part|full|no`
  - `kv_policy_status`:
    - `observability_only`
    - `eligible_for_eviction_prototype`
    - `disabled_runtime_not_part_capable`
    - `unknown_runtime_capability`
  - `kv_behavior_changed`: always `false` in v0 observability/simulation phases.

## Current detection method
- Wrapper-side log parsing in `run_experiment.ps1`.
- Known signals:
  - `"does not support partial sequence removal"` -> `full`
  - `"speculative decoding not supported by this context"` -> `no`
- If no reliable signal is found -> `unknown`.

## Future introspection need
- A small llama.cpp introspection surface would improve confidence for `part` detection.
- Until then, IVY treats missing signals as `unknown` and keeps behavior unchanged.
