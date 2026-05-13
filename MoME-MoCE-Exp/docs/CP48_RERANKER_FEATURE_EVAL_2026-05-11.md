# CP48 Reranker Feature Eval - 2026-05-11

## What Changed

Added deterministic prefilter feature support to the context-memory plugin runtime policy.

Runtime policy path:

```text
store/policy/autoresearch_policy.json
```

Supported `prefilter_feature_weights`:

- `agent_note_boost`
- `checkpoint_match_boost`
- `agent_note_checkpoint_mismatch_penalty`
- `source_code_non_code_penalty`

Added:

```text
MoME-MoCE-Exp/scripts/run_reranker_feature_eval.py
MoME-MoCE-Exp/docs/AUTORESEARCH_RERANKER_FEATURE_EVAL.md
```

## Profiles Evaluated

| Profile | Features |
|---|---|
| `baseline` | existing agent-note boost |
| `checkpoint_guard` | checkpoint match boost and checkpoint mismatch penalty |
| `code_penalty` | checkpoint guard plus source-code penalty for non-code queries |

## Real Run

Command:

```powershell
python MoME-MoCE-Exp\scripts\run_reranker_feature_eval.py `
  --store MoME-MoCE-Exp\out\autoresearch_loop\memory_store `
  --cases MoME-MoCE-Exp\docs\AUTORESEARCH_MINED_EVAL_CASES.json `
  --out MoME-MoCE-Exp\docs\AUTORESEARCH_RERANKER_FEATURE_EVAL.md `
  --max-prefilter-items 32
```

Winner:

- profile: `code_penalty`
- passed: `5 / 5`
- avg wall: `59.736 ms`
- avg router latency: `2.133 ms`

## Verification

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_reranker_feature_eval.py tests\test_mined_case_policy_eval.py tests\test_ivy_context_memory_plugin.py -q
python -m py_compile MoME-MoCE-Exp\scripts\run_reranker_feature_eval.py plugins\ivy-context-memory\scripts\ivy_context_memory.py
```

Result:

- `13 passed`

## Why This Matters

This is the first reranker-like stage that is:

- deterministic
- policy-controlled
- evaluated against mined hard cases
- still inside the ACCA routing envelope

The next step is to let the autoresearch loop promote the winning profile into the runtime policy automatically when it beats baseline on mined cases.
