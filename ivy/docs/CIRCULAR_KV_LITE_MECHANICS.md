# Circular KV Lite v0 Mechanics

This is the implementation-facing mechanics spec for the first minimal Circular KV policy.

## 1) KV Unit (v0 choice)
- **Unit:** `window` (contiguous token ranges of fixed size).
- **v0 window size:** `W = 64` tokens.

Why this unit for v0:
- Token-level management is too fine-grained and expensive for a first pass.
- Block-level tied to internal allocator details is less stable across runtime internals.
- Fixed windows are simple to index, rotate, trace, and reason about in logs.

## 2) Memory Regions
v0 partitions logical KV retention into three regions:

- **Pinned Prefix Region**
  - Earliest windows from the prompt, up to `P` tokens.
  - Never rotated in v0.
  - Intended to preserve instruction/system and stable task context.

- **Recent Sliding Window**
  - Most recent windows near the decode head, up to `R` tokens.
  - Always retained while active generation continues.
  - Moves forward as decoding advances.

- **Rotating Middle Region**
  - Windows between pinned prefix and recent region.
  - Eligible for rotation/eviction under pressure.
  - Managed as FIFO by logical age.

Default v0 bounds (initial values):
- `P = min(512, prompt_n)` tokens pinned.
- `R = 512` tokens recent.
- Middle = everything between pinned and recent.

## 3) Retention Rule
- Always resident:
  - Pinned Prefix Region.
  - Recent Sliding Window.
- Allowed to rotate:
  - Rotating Middle Region.
- Never evicted in v0:
  - Prefix windows in pinned region.
  - Active recent windows in recent region.

## 4) Rotation / Eviction Rule (exact v0)
Trigger condition:
- KV pressure is detected when a new window cannot be admitted without exceeding effective KV capacity.

Eviction order (deterministic):
1. Evict oldest window from Rotating Middle Region (FIFO).
2. Repeat step 1 until there is enough space.
3. If middle is empty and still over capacity:
   - do **not** evict pinned or recent in v0.
   - mark overflow condition and fall back to baseline behavior for that step (implementation-defined fallback path).

No scoring, no adaptive ranking, no recency weighting beyond the explicit recent region in v0.

## 5) Smallest Behavior Change vs Baseline
Compared to stock handling, v0 adds only this behavior:
- Under KV pressure, eviction is constrained to **middle-region FIFO windows** while preserving pinned prefix and recent windows.

Everything else remains baseline:
- Same model/runtime/sampling path.
- Same request flow and artifact schema.
- No changes to cross-run behavior.

## 6) Explicitly Deferred (out of v0 scope)
- SSD/disk KV tiering.
- Learned routing or learned retention policies.
- MoE-specific KV policies.
- Adaptive/scored eviction heuristics.
- Cross-session KV reuse.
- Multi-request/global KV sharing.
- Compression/quantized KV transformations as a policy feature.
- Any asynchronous background migration pipeline.

## 7) Required Trace Evidence (minimum)
Each policy decision event must emit a trace record with:
- `kv_policy_mode` (e.g. `circular_kv_lite_v0`)
- `kv_region` (`pinned_prefix` | `recent` | `middle`)
- `kv_action` (`retain` | `rotate` | `evict` | `fallback`)
- `window_id` (monotonic logical window index)
- `bytes_moved` (0 for pure retain; non-zero for move/evict operations)
- `notes` (short reason; e.g. `pressure`, `middle_fifo`, `middle_empty_fallback`)

Recommended minimal counters (run summary):
- `kv_middle_evictions`
- `kv_fallback_events`
- `kv_pinned_tokens`
- `kv_recent_tokens`

