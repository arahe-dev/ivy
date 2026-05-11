# CP58 Tighter Wall Budgets - 2026-05-11

## What Changed

Tightened the default wall-clock budgets in the context-memory regression gate:

| Budget | Before | After |
|---|---:|---:|
| mined/feature wall | `50 ms` | `35 ms` |
| full plugin wall | `40 ms` | `25 ms` |

Updated:

```text
MoME-MoCE-Exp/scripts/run_context_memory_regression_gate.py
MoME-MoCE-Exp/tests/test_context_memory_regression_gate.py
MoME-MoCE-Exp/docs/AUTORESEARCH_REGRESSION_GATE.md
```

## Why

CP57 moved plugin wall time into the high teens. Leaving the old looser budget would allow a regression back toward the pre-cache path without failing the gate.

## Real Run

Command:

```powershell
python MoME-MoCE-Exp\scripts\run_context_memory_regression_gate.py `
  --store MoME-MoCE-Exp\out\autoresearch_loop\memory_store `
  --plugin-store MoME-MoCE-Exp\out\regression_gate_plugin_store `
  --cases MoME-MoCE-Exp\docs\AUTORESEARCH_MINED_EVAL_CASES.json `
  --source-root MoME-MoCE-Exp `
  --out MoME-MoCE-Exp\docs\AUTORESEARCH_REGRESSION_GATE.md
```

Result:

- gate passed: `true`
- mined policy avg wall: `27.633 ms`
- feature eval avg wall: `21.212 ms`
- feature avg router: `2.05 ms`
- plugin benchmark avg query wall: `16.544 ms`
- plugin avg router: `2.433 ms`

## Verification

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_context_memory_regression_gate.py tests\test_ivy_context_memory_plugin.py -q
python -m py_compile MoME-MoCE-Exp\scripts\run_context_memory_regression_gate.py
```

Result:

- `14 passed`
