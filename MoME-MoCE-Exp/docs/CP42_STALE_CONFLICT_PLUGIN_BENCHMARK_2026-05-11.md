# CP42 Stale Conflict Plugin Benchmark - 2026-05-11

## What Changed

CP42 uses CP41 rich note metadata to add a stale/current conflict lane to the plugin benchmark.

The benchmark now writes:

- a stale CP42 note:

```text
CP42 stale policy said any source edit requires a full plugin rebuild.
```

- a current CP42 note that supersedes/conflicts with the stale note:

```text
CP42 current policy says changed-source rebuilds should reuse unchanged file chunks and reprocess only changed files.
```

Benchmark query:

```text
What is the latest CP42 rebuild policy versus stale memory?
```

Expected:

- select both current and stale notes
- emit `contradiction_aware`
- pass expectation using the selected packet text

## Latest Benchmark

Command:

```powershell
python MoME-MoCE-Exp\scripts\run_context_memory_plugin_benchmark.py --reset
```

Result:

- Query count: `6`
- Passed expectations: `6 / 6`
- Avg query wall: `99.481 ms`
- Avg router latency: `11.69 ms`

Conflict lane:

| Query | Mode | Selected | Pass |
|---|---|---|---|
| latest CP42 rebuild policy versus stale memory | `contradiction_aware` | `note_bac5d38543dbf226`, `note_f3c939d0f7d4c74f` | true |

Negative lane:

| Query | Mode | Selected | Pass |
|---|---|---|---|
| today's Bitcoin price | `abstain_notice` | none | true |

## Verification

Focused tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ivy_context_memory_plugin.py tests\test_context_stress_contract.py tests\test_cp7_cp9_contract.py tests\test_cp26_cp28_contract.py -q
```

Result:

- `23 passed`

## Why This Matters

The plugin can now benchmark the behavior that makes ACCA meaningfully different from naive memory retrieval:

- current memory can supersede stale memory
- stale memory can still be shown when the query asks for comparison
- packet mode changes to `contradiction_aware`
- volatile external facts still abstain
