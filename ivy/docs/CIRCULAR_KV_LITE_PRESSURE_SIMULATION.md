# Circular KV Lite v0 Pressure Simulation (Observability Only)

This step simulates pressure decisions only.  
It does not evict KV, move memory, or modify inference behavior.

## Inputs
- `window_size = 64`
- region classification output (`pinned_prefix`, `middle`, `recent`)
- optional `experiment.kv_capacity_windows`

## Rules
- If `kv_capacity_windows` is absent:
  - do not simulate pressure decisions
- If `total_windows <= kv_capacity_windows`:
  - `pressure_detected = false`
  - no `would_evict`/`fallback` events
- If `total_windows > kv_capacity_windows`:
  - `pressure_detected = true`
  - `needed_evictions = total_windows - kv_capacity_windows`
  - select oldest `middle` windows first (FIFO)
  - emit one simulated eviction event for selected middle windows:
    - `kv_region = middle`
    - `kv_action = would_evict`
    - `notes = pressure_sim_middle_fifo`
  - if `middle` has fewer windows than needed:
    - emit fallback event:
      - `kv_region = none`
      - `kv_action = fallback`
      - `notes = middle_empty_fallback`

## Result fields (`result.json.kv`)
- `kv_capacity_windows`
- `pressure_detected`
- `needed_evictions`
- `simulated_evicted_windows`
- `fallback_events`
- `kv_behavior_changed = false`

## Trace fields (`kv_trace.jsonl`)
- existing region retain events remain
- pressure simulation events are appended when applicable
