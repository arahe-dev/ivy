# CP30 Adaptive Packet And Note Priority - 2026-05-11

## What Changed

CP30 makes packet formatting and direct memory priority first-class router behavior.

### Packet Mode

`frontier_context_packet.schema.json` now requires `packet_mode`.

Allowed modes:

- `compact_default`: single clear answer packet.
- `proof_lite`: low-confidence or multi-evidence packet that should expose routing proof.
- `contradiction_aware`: conflict/stale/decoy-sensitive packet.
- `abstain_notice`: empty or non-answerable packet.

The router sets this mode inside `_frontier_packet()`, and the `ivy-context-memory` plugin uses it when `--variant auto` is selected.

### Direct Agent Note Priority

The router now gives strong matching `agent_note` records a selection pass before generic evidence selection.

This matters because CP29 showed the prefilter could rank the explicit note first, while the downstream router still selected a generic high-authority runbook chunk. CP30 fixes that policy gap for direct note hits.

## Verification

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ivy_context_memory_plugin.py tests\test_context_stress_contract.py -q
python -m py_compile C:\ivy\plugins\ivy-context-memory\scripts\ivy_context_memory.py C:\ivy\MoME-MoCE-Exp\scripts\mome_moce_harness.py
```

Result:

- `7 passed`
- Python compile checks passed

## Smoke Result

Query:

```text
What did CP28 show about final answer packet formats?
```

Observed after CP30:

- `selected_ids`: `note_651ce93b6060d428`
- `variant`: `proof_lite`
- `packet_mode`: `proof_lite`
- plugin router latency: about `12.367 ms`
- route proof latency: about `11.7388 ms`
- prefilter candidates: `192 / 537`

The selected evidence is now the direct CP28 agent note:

```text
CP28 showed contradiction-aware packets won final-answer A/B on conflict cases.
```

## Why This Matters

This moves the system closer to a practical memory layer rather than only a retrieval benchmark:

- Memory notes can now win when they are direct answers.
- Packet formatting is explicit and machine-readable.
- Codex/OpenCode/plugin callers can inspect `packet_mode` instead of reverse-engineering the right prompt format from route proof details.

## Next Targets

- Carry prefilter scores into route proof for explainability.
- Add an incremental ingest cache so repeated builds do not rescan unchanged files.
- Add a small benchmark that measures build time, query time, note-hit selection, and packet mode correctness together.
