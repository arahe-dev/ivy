# Agent Memory Burn-In

Generated: `2026-05-12T03:05:47Z`

| Check | Value |
|---|---:|
| OK | `True` |
| Initial deltas | `4` |
| After-test deltas | `1` |
| Before-task selected | `1` |
| Packet-v2 selected | `1` |
| Total wall | `399.67 ms` |

```mermaid
flowchart LR
  Session["Codex/OpenCode session"] --> Ingest["session-ingest"]
  Ingest --> Deltas["memory_deltas.jsonl"]
  Deltas --> Notes["safe notes"]
  Task["before_task hook"] --> Packet["context_packet v0.2"]
  Notes --> Packet
  Packet --> Agent["agent plan/edit/test"]
  Agent --> AfterTest["after_test hook"]
  AfterTest --> Deltas
```

## Meaning

The plugin can now capture a real agent session, distill it into safe durable memory, retrieve it before work, and remember verified outcomes after tests without stuffing the raw transcript into the model context.
