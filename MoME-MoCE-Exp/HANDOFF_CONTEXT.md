# MoME/MoCE Handoff Context

Date: 2026-05-10

## Current Checkpoint

The MoME/MoCE experiment is past the CP7/CP8/CP9 checkpoint and now includes the CP9.1 Rust backend integration, Ivy-real v2, taint/exposure packet ABI, and model-facing demo artifacts.

- CP7 is complete: `out/context_stress_ivy_real` has 37 curated IVY evidence items and 30 labeled cases.
- CP8 is complete: `--candidate-backend indexed` preserves exact quality and improves stress latency.
- CP9 is complete as a candidate-index prototype: Rust candidate recall is verified.
- CP9.1 is complete as an optional Rust candidate backend: `--candidate-backend rust` is routed through Python proof/gate/packet authority.
- Ivy-real v2 is complete: `out/context_stress_ivy_real_v2` has 45 items and 119 cases.
- Taint/exposure fields now survive into route proofs and frontier packets.

Primary status doc:

- `docs/CP7_CP9_STATUS_2026-05-10.md`
- `docs/AUTORESEARCH_TRACK_RECORD_2026-05-10.md`

Primary continuation doc:

- `docs/NEXT_CHAT_HANDOFF.md`

## Verified Results

```text
ivy_real scan:     30/30, required-only precision 1.0, artifact_errors 0
ivy_real indexed:  30/30, required-only precision 1.0, artifact_errors 0
smoke indexed:     62/62, required-only precision 1.0, artifact_errors 0
medium indexed:    62/62, required-only precision 1.0, artifact_errors 0
stress indexed:    62/62, required-only precision 1.0, artifact_errors 0
stress scan:       62/62, required-only precision 1.0, artifact_errors 0
rust ivy_real:     recall@32 1.0, failed_cases 0
rust stress:       recall@32 1.0, failed_cases 0
ivy_real_v2 idx:   119/119, required-only precision 1.0, forbidden hits 0
ivy_real_v2 rust:  119/119, required-only precision 1.0, forbidden hits 0
stress rust batch: 62/62, required-only precision 1.0, route mean 1.694 ms, preload 4483.781 ms
model demo:        ACCA 8/8, naive BM25 forbidden hits 1 in representative demo
v2 naive BM25:     precision 0.2376, forbidden hits 12
v2 ACCA compact:   precision 1.0, forbidden hits 0
pytest:            13 passed
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

1. Make CP9 a real optional backend: compile Rust once, call it directly, and compare Rust/Python candidate parity.
2. Improve raw Rust/Python candidate parity. Selected evidence parity is 1.0, but candidate Jaccard is still low on stress.
3. Replace benchmark batch preload with a persistent Rust process or library binding for arbitrary interactive queries.
4. Expand Ivy-real v3 using actual sanitized run outputs and failure logs.
5. Add answer-level model checks that consume only the frontier packet and cite selected evidence IDs.
