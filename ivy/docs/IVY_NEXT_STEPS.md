# IVY Next Steps

This roadmap keeps memory work staged. Do not jump directly to prompt injection or MoME/MoCE runtime integration.

## Phase 2A: Read-only memory packet preview

- MoME retrieves candidate memories.
- MoCE composes a packet.
- Packet is printed/saved only.
- No agent prompt injection.
- Implemented as `memory_packet_cli preview`; continue using it only as a dry run until packet eval quality is acceptable.

## Phase 2B: Memory packet eval

- Evaluate packet quality.
- Measure relevance, provenance, latency, and size.
- Compare policies.

## Phase 2C: Opt-in prompt injection experiment

- Gate behind explicit CLI flag.
- Compare no-memory vs keyword-only vs vector-only vs hybrid.
- Measure JSON validity, tool failures, steps, latency, and task success.

## Phase 3: Hot buffer / LRU

- Add recent memory cache.
- Track `last_used_at` and `use_count`.
- Promote and demote memories.
- Measure useful recall per latency.

## Phase 4: MoME

- Add experts:
  - episodic
  - procedural
  - failure
  - benchmark
  - safety
  - FTS
  - vector
  - recent-buffer
- Add router deciding which experts to consult.

## Phase 5: MoCE

- Add composers:
  - minimal
  - debugging
  - benchmark
  - tool-use
  - safety
  - planning
- Add context budget manager.

## Phase 6: Procedure promotion

- Promote repeated successful tool traces into candidate procedures.
- Procedures never bypass the policy gate.
- Store evidence episodes.

## Phase 7: Memory governance

- Add statuses:
  - active
  - stale
  - superseded
  - rejected
- Add confidence decay.
- Add stale-memory reports.

## Phase 8: Advanced vectors

- Keep stdlib hashed-vector fallback.
- Optionally add sqlite-vec if available.
- Optional embedding backends may be compared later, but must not be mandatory.
