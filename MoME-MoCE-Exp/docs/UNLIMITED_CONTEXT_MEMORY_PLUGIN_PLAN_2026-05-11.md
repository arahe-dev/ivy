# Unlimited Context/Memory Plugin Plan - 2026-05-11

This document scopes the next deep build session around the new `plugins/ivy-context-memory` sidecar.

The goal is not to make the model context window infinite. The goal is to make the agent's *working memory* effectively unbounded by keeping source material outside the prompt, compiling only the relevant evidence into small ACCA packets, and remembering verified outcomes after work completes.

## What Was Built Now

`plugins/ivy-context-memory`:

- Codex plugin manifest and marketplace entry.
- Codex skill instructions.
- OpenCode command notes.
- Local CLI:
  - `init`
  - `ingest`
  - `build`
  - `remember`
  - `query`
  - `status`
  - `serve`
- Local HTTP API:
  - `GET /health`
  - `GET /status`
  - `POST /ingest`
  - `POST /remember`
  - `POST /query`
  - `POST /build`
- Backing store at `.ivy-context-memory`.
- ACCA dataset generated from registered source roots and safe notes.
- Query packets rendered through MoME/MoCE and CP24/CP28 packet formats.

## Deep Session Roadmap

The next 3-4 hour build should target CP29-CP48. The order below is designed to convert the plugin from MVP to daily-driver agent infrastructure.

| CP | Build | Why It Matters |
|---:|---|---|
| CP29 | Persisted two-stage index for plugin datasets | CP26 ingestion hit 13.857 ms p50 on 821 chunks; large stores need sub-5 ms routing. |
| CP30 | Adaptive packet compiler in the router, not only scripts | Make compact/proof/contradiction-aware packet choice first-class. |
| CP31 | Live OpenRouter/DeepSeek final-answer A/B through CP28 | Verify actual model answer quality, not just deterministic proxy. |
| CP32 | Incremental ingestion cache | Avoid full rebuild after every note/source change. |
| CP33 | Source-root trust profiles | Mark repos/docs as high/medium/low authority before ingestion. |
| CP34 | Memory namespaces | Separate project, user, agent, experiment, and global memory. |
| CP35 | Multi-agent write ledger | Track Codex/OpenCode authorship, timestamp, run ID, and verification state. |
| CP36 | Conflict-aware note insertion | New notes can supersede or conflict with old notes explicitly. |
| CP37 | Stale-note sweeper | Detect old current notes that need freshness review. |
| CP38 | Query explain UI artifact | Emit small HTML/MD showing selected/rejected/overflowed evidence. |
| CP39 | OpenCode wrapper command | One command that OpenCode can call before/after tasks. |
| CP40 | Codex bootstrap skill install path | Make plugin usable from any repo, not only `C:\ivy`. |
| CP41 | HTTP API auth token | Localhost is okay for dev; durable sidecar needs token protection. |
| CP42 | Background daemon wrapper | `ivy-memoryd.cmd` or PowerShell startup with logs and health checks. |
| CP43 | Compact packet budget tuner | Auto-fit packet to token budget while preserving conflict/safety evidence. |
| CP44 | Runtime task transcript ingestion | Convert verified agent transcripts into safe memory records. |
| CP45 | Memory quality eval pack | Test poisoning, stale notes, namespace leakage, and agent-author conflicts. |
| CP46 | Recall Board integration | Send route proofs and memory graphs to Recall as visual second-brain artifacts. |
| CP47 | Signal integration | Ping phone with high-value memory events and accept reply-to-remember. |
| CP48 | Fresh-machine replay | Clone repo, install plugin, ingest sources, run same query, compare packet hash. |

## Success Criteria

By the end of that session:

- The plugin can handle thousands to tens of thousands of chunks without noticeable wait.
- Codex and OpenCode have a clear before-task and after-task command.
- Memory writes are safe, attributed, and reversible.
- Query packets are reproducible and auditable.
- Live model A/B confirms whether the packets improve real answers.

## Design Principle

The agent should never ask the model to remember everything. The agent should ask the memory sidecar for a small admissible evidence packet, use it, and then write back only verified outcomes.
