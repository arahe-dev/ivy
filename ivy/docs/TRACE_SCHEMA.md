# TRACE SCHEMA (V0)

Each line is one event (JSONL recommended).

## Required fields
- `run_id` (string): unique run identifier.
- `token_id` (integer): token index within generation.
- `layer_id` (integer): model layer index.
- `phase` (string): e.g. `prefill`, `decode`, `kv_read`, `kv_write`.
- `timing_us` (integer): event duration in microseconds.
- `bytes_moved` (integer): bytes read/written for this event.
- `kv_policy_decision` (string): e.g. `retain`, `evict`, `rotate`, `none`.
- `notes` (string): optional short diagnostic note.

## Example event
```json
{
  "run_id": "2026-04-24-baseline",
  "token_id": 128,
  "layer_id": 17,
  "phase": "kv_write",
  "timing_us": 342,
  "bytes_moved": 2097152,
  "kv_policy_decision": "none",
  "notes": "stock baseline path"
}
```

