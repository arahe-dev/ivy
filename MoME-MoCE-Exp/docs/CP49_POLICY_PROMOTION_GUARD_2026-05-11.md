# CP49 Policy Promotion Guard - 2026-05-11

## What Changed

Extended the deterministic reranker feature evaluator with an optional guarded promotion path:

```powershell
python MoME-MoCE-Exp\scripts\run_reranker_feature_eval.py `
  --store MoME-MoCE-Exp\out\autoresearch_loop\memory_store `
  --cases MoME-MoCE-Exp\docs\AUTORESEARCH_MINED_EVAL_CASES.json `
  --out MoME-MoCE-Exp\docs\AUTORESEARCH_RERANKER_FEATURE_EVAL.md `
  --max-prefilter-items 32 `
  --promote
```

Promotion is allowed only when the winning profile:

- is not `baseline`
- passes all mined hard cases
- does not regress pass count versus baseline
- improves router latency versus baseline

## Real Run

Winner:

- profile: `code_penalty`
- passed: `5 / 5`
- avg wall: `56.511 ms`
- avg router latency: `2.018 ms`

Baseline:

- passed: `5 / 5`
- avg wall: `58.432 ms`
- avg router latency: `2.167 ms`

Promotion:

- promoted: `true`
- reason: `winner preserves pass rate and improves router latency`
- runtime policy: `MoME-MoCE-Exp\out\autoresearch_loop\memory_store\policy\autoresearch_policy.json`

The runtime policy now includes:

```json
{
  "prefilter_feature_profile": "code_penalty",
  "prefilter_feature_weights": {
    "agent_note_boost": 500.0,
    "checkpoint_match_boost": 160.0,
    "agent_note_checkpoint_mismatch_penalty": -220.0,
    "source_code_non_code_penalty": -180.0
  }
}
```

## Verification

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_reranker_feature_eval.py tests\test_mined_case_policy_eval.py tests\test_ivy_context_memory_plugin.py -q
python -m py_compile MoME-MoCE-Exp\scripts\run_reranker_feature_eval.py
```

Result:

- `14 passed`

## Why This Matters

CP48 found a better deterministic profile. CP49 turns that into a repeatable promotion mechanism, so autoresearch can move a tested policy into runtime without manual JSON edits.
