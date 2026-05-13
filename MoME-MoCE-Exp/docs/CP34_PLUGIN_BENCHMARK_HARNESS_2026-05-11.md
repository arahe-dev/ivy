# CP34 Plugin Benchmark Harness - 2026-05-11

## What Changed

Added a repeatable benchmark harness:

```text
MoME-MoCE-Exp/scripts/run_context_memory_plugin_benchmark.py
```

It creates a plugin benchmark store, registers `MoME-MoCE-Exp` as source, writes checkpoint notes, builds the memory dataset, then measures representative queries.

## Why This Matters

The prior plugin work was verified by focused tests and ad hoc smoke commands. CP34 adds a repeatable track-record artifact for:

- query wall latency
- router latency
- selected evidence IDs
- packet mode
- expectation pass/fail
- benchmark JSON and Markdown report output

This is useful for future “supercharge” sessions because each routing change can be measured against the same small set of practical memory questions.

## Latest Run

Command:

```powershell
python MoME-MoCE-Exp\scripts\run_context_memory_plugin_benchmark.py --reset
```

Output:

```text
C:\ivy\MoME-MoCE-Exp\out\plugin_benchmarks\context_memory_plugin_benchmark_20260511T170103Z.md
```

Summary:

- Query count: `4`
- Passed expectations: `4 / 4`
- Avg query wall: `101.363 ms`
- Avg router latency: `11.865 ms`

| Query | Wall ms | Router ms | Mode | Selected |
|---|---:|---:|---|---|
| CP28 final-answer packets | `117.577` | `12.382` | `proof_lite` | `note_651ce93b6060d428` |
| MCP tools exposed | `87.091` | `7.744` | `proof_lite` | `note_76de75586f91c809` |
| CP29 generated output ingestion | `109.487` | `13.627` | `proof_lite` | `note_c6d2da6960a255cf` |
| CP32 repeated build cache | `91.299` | `13.708` | `proof_lite` | `note_5806b2ca5c492ccc` |

## Finding During Build

The first benchmark draft exposed an over-broad note-priority bug: a CP33 note could be promoted for a CP32 query because it matched generic terms like `plugin` and `build`.

Fix applied:

- checkpoint-specific queries now only promote `agent_note` records containing the same checkpoint number.

Focused tests after the fix:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ivy_context_memory_plugin.py tests\test_context_stress_contract.py tests\test_cp7_cp9_contract.py tests\test_cp26_cp28_contract.py -q
```

Result:

- `18 passed`

## Next Benchmark Extensions

- Add MCP `tools/call` query latency into the benchmark.
- Add negative cases where no memory should be selected.
- Add stale/contradictory evidence cases from CP20-CP24.
- Preserve a rolling Markdown scoreboard under `docs/`.
