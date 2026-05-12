# CP74 External Generalization Gate - 2026-05-12

CP74 turns the earlier CP23 Signal/Recall external pack into a repeatable gate.

The purpose is to keep MoME/MoCE from looking good only because it memorized IVY-shaped labels. The gate regenerates a non-IVY dataset, routes every case with the indexed deterministic router, and fails unless recall, precision, decoy rejection, abstention, and latency all stay inside budget.

## What Changed

- Added `scripts/run_external_generalization_gate.py`.
- The script regenerates `out/context_stress_external_signal_recall`.
- It writes `docs/EXTERNAL_GENERALIZATION_GATE.md`.
- It can also write JSON via `--json-out`.
- Added a pytest contract that runs the gate against a temporary generated dataset.

## Result

| Metric | Value |
|---|---:|
| Cases | `9` |
| Passed | `9` |
| Quality | `1.0000` |
| Required recall | `1.0000` |
| Required-only precision | `1.0000` |
| Forbidden hits | `0` |
| Avg selected | `0.8889` |
| Mean latency | `0.406 ms` |
| P50 latency | `0.345 ms` |
| P95 latency | `0.648 ms` |
| Max latency | `0.740 ms` |

## Coverage

The gate checks external context-memory behavior across:

- Signal iPhone delivery through Tailscale Serve plus Web Push, without public VPS.
- Signal not being a cloud service or Codex-specific broker.
- Signal append-only SQLite event log as durable coordination primitive.
- Signal daemon versus worker shell-execution boundary.
- Recall Board screenshot-free AI context exports.
- Recall text graph and Graph IR.
- Recall second-brain features.
- Unsupported Recall Cloud pricing abstention.

## Interpretation

This still is not a broad internet-scale benchmark, but it is meaningfully different from an IVY-only test. It contains external product/architecture facts, negative decoys, a safety boundary case, and one unsupported commercial fact. Passing this gate means the deterministic router can transfer its policy behavior outside IVY docs without using a model call.

## Verification

```powershell
.\.venv\Scripts\python.exe -m py_compile scripts\run_external_generalization_gate.py
.\.venv\Scripts\python.exe scripts\run_external_generalization_gate.py --json-out out\cp74_external_generalization_gate.json
.\.venv\Scripts\python.exe -m pytest tests\test_cp21_cp24_cp23_contract.py -q
```

Result:

- `tests/test_cp21_cp24_cp23_contract.py`: `5 passed`.
