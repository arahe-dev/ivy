# TRACE SCHEMA (CIRCULAR KV LITE V0 OBSERVABILITY)

Each line is one event in `kv_trace.jsonl`.

## Required fields
- `run_id` (string): unique run identifier.
- `kv_policy_mode` (string): policy mode requested by the run manifest.
- `kv_region` (string): logical KV region (`pinned_prefix`, `middle`, `recent`).
- `kv_action` (string): policy action (`retain`, `would_evict`, `fallback`).
- `window_start` (integer): first logical 64-token window index for this region (`-1` when empty).
- `window_end` (integer): last logical 64-token window index for this region (`-1` when empty).
- `window_count` (integer): number of logical windows in this region.
- `bytes_moved` (integer): bytes moved by policy. For v0 no-op: `0`.
- `notes` (string): short diagnostic marker (`region_classification_noop`, `pressure_sim_middle_fifo`, `middle_empty_fallback`).

## V0 classification expectation
If `kv_policy_mode` is absent, `kv_trace.jsonl` is not required.  
If `kv_policy_mode=circular_kv_lite_v0`, emit one event per region (`pinned_prefix`, `middle`, `recent`) with no-op action.

## Pressure simulation expectation
If `experiment.kv_capacity_windows` is present and `total_windows > kv_capacity_windows`:
- emit `would_evict` event for oldest middle windows first
- emit `fallback` event when middle windows are insufficient for required evictions

## Example event
```json
{
  "run_id": "20260425_120001",
  "kv_policy_mode": "circular_kv_lite_v0",
  "kv_region": "middle",
  "kv_action": "retain",
  "window_start": 8,
  "window_end": 10,
  "window_count": 3,
  "bytes_moved": 0,
  "notes": "region_classification_noop"
}
```
