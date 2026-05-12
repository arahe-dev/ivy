# MoME/MoCE Handoff Context

Date: 2026-05-13

## Current Checkpoint

The MoME/MoCE experiment is now in the Alexandria dogfood layer, well past CP102-era engine work. CP7/CP8/CP9/CP9.1 remain historical milestones, but they are no longer the current state.

- D-ACCA/helper-lazy is the current deterministic memory-to-context engine.
- The dogfood hook service exposes health, memory import, packet build, route proof, search, feedback, and local forget hooks.
- Alexandria harnesses validate raw engine responses and emit stable dashboard/frontend view models.
- A no-build `alexandria_simple/` console exists for local use.
- `scripts/alexandria_mcp_server.py` now exposes Alexandria over MCP for Codex and ChatGPT Developer Mode.
- Runtime state for the MCP/app setup is outside git at `C:\ivy-data\alexandria`.
- Current MCP ports: D-ACCA hooks on `127.0.0.1:8767`, MCP bridge on `127.0.0.1:8790`.
- ChatGPT tunnel URL, when active, is stored at `C:\ivy-data\alexandria\chatgpt_mcp_url.txt`.

Primary status doc:

- `docs/CP7_CP9_STATUS_2026-05-10.md`
- `docs/AUTORESEARCH_TRACK_RECORD_2026-05-10.md`

Primary continuation doc:

- `docs/NEXT_CHAT_HANDOFF.md`
- `docs/ALEXANDRIA_MCP_APP_SETUP.md`

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
pytest current:    34 passed
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
