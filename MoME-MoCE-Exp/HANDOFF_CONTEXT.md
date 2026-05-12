# MoME/MoCE Handoff Context

Date: 2026-05-12

## Current Checkpoint

The MoME/MoCE experiment is now in the CP102-era context-memory sidecar phase. CP9/CP9.1 are historical milestones, not the current frontier. The current build includes `ivy-context-memory`: a Codex/OpenCode-facing local memory sidecar with ACCA packets, route proofs, write barriers, MCP/API/daemon surfaces, session ingest, lifecycle hooks, batch ingest, freshness scan, long-session drill, readiness doctor, and answer-level A/B checks.

Current state:

- Core ACCA routing remains deterministic and authority-constrained: selected evidence, rejected evidence, route proof, answerability, taint/exposure labels, and stale/current conflict behavior.
- CP9.1 Rust batch remains a useful historical speed result, but the active path is the plugin/daemon lifecycle around `plugins/ivy-context-memory`.
- CP45-CP82 added real-conversation autoresearch, a 10M-token sharded-memory capacity rating, external generalization gates, no-exact-anchor ablations, paraphrase gates, negative controls, and source-removal sensitivity checks.
- CP83-CP92 added agent session capture, memory deltas, packet v2, before/after hooks, daemon/MCP surfaces, and burn-in.
- CP93-CP102 added adapter lifecycle, targeted answer-quality A/B, batch session ingest, freshness scan, long-session drill, readiness doctor, and refreshed usage docs.

Primary status doc:

- `docs/AUTORESEARCH_LOOP_SCOREBOARD.md`
- `docs/PLUGIN_BENCHMARK_SCOREBOARD.md`
- `docs/PLUGIN_SUPERCHARGE_TRACK_RECORD_2026-05-11.md`
- `plugins/ivy-context-memory/README.md`

Primary continuation doc:

- `docs/NEXT_CHAT_HANDOFF.md`

## Verified Results

```text
Ivy-real v2 ACCA:             119/119, required-only precision 1.0, forbidden hits 0
Stress Rust batch:            62/62, required-only precision 1.0, route mean 1.694 ms
Plugin benchmark:             6/6 expected behaviors
Plugin benchmark latency:     avg query wall 15.535 ms, avg router 2.478 ms
Hot repeated plugin wall:     about 7.5-7.7 ms
Regression gate:              passed
Regression gate plugin wall:  19.351 ms
Regression gate plugin route: 3.747 ms
Daemon post-warm query wall:  10.142 ms
Daemon post-warm router:      4.638 ms
External generalization:      9/9 combined gate
No-exact-anchor gate:         9/9
Semantic paraphrase gate:     9/9
Semantic + no-exact gate:     9/9
Negative controls:            5/5 abstain, avg selected 0.0
Source-removal gate:          8/8 abstain, avg selected 0.0
Agent session ingest:         verified
Agent hook packet v2:         verified
Agent answer A/B:             packet-v2 memory 3/3, no-memory 0/3
Batch session ingest:         verified, single rebuild
Long-session drill:           1000 records -> 3 deltas, 3.179 ms packet wall
Agent memory doctor:          verified
Focused tests:                28 passed
Capacity rating:              10M tokens as sharded external memory, not one prompt
```

## Litter / Phone Access Setup

The PC-side Litter setup uses Tailscale plus Windows OpenSSH.

Connection details:

```text
Host: 100.69.245.47
MagicDNS: ari-legion.taild0cc8e.ts.net
User: arahe
Port: 22
Project path: C:\ivy\MoME-MoCE-Exp
```

`sshd` is installed from `Microsoft.OpenSSH.Preview`, runs automatically, and the firewall rule `OpenSSH-Tailscale` allows TCP/22 only from `100.64.0.0/10`.

Litter expected a Windows-friendly Codex command wrapper, so this file exists:

```text
C:\Users\arahe\.litter\bin\codex.cmd
```

It calls:

```text
C:\Users\arahe\AppData\Roaming\npm\codex.cmd
```

## Kittylitter Server Wrapper

The Codex app-server for Litter is wrapped as a PATH command:

```powershell
kittylitter start
kittylitter status
kittylitter stop
kittylitter restart
kittylitter logs
kittylitter foreground
```

Implementation:

```text
C:\Users\arahe\AppData\Roaming\npm\kittylitter.cmd
C:\ivy\MoME-MoCE-Exp\kittylitter.cmd
C:\ivy\MoME-MoCE-Exp\scripts\kittylitter-server.ps1
```

Default server endpoint:

```text
ws://127.0.0.1:8390
```

Logs:

```text
%TEMP%\codex-mobile-server-8390-manual.log
%TEMP%\codex-mobile-server-8390-manual-err.log
```

If Litter gets stuck on "starting", run:

```powershell
kittylitter restart
kittylitter status
kittylitter logs
```

Then force-close and reopen Litter on the phone so it does not reuse stale SSH bootstrap state.

## Next Engineering Steps

1. Run a fresh-machine replay: install plugin, ingest sources, warm daemon, query, remember, and compare packet hashes.
2. Wire `ivy-context-memory` into the normal Codex/OpenCode pre-task and post-verification workflow.
3. Expand answer-level A/B tests where the final model must use ACCA packets correctly, not just retrieve the right evidence.
4. Grow external generalization corpora beyond IVY docs while keeping negative controls and source-removal gates.
5. Lower plugin wall latency further without weakening authority, freshness, conflict, safety, or abstention behavior.
6. Decide whether Rust should become a persistent service/library for larger corpora, or remain a historical benchmark backend while the Python plugin path is optimized.
