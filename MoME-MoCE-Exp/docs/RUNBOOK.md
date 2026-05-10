# Context Stress Dataset Runbook

The context stress generator builds deterministic JSONL corpora from `templates/*.json` plus the seeded eval cases in `eval/cases_seed.json`. The public CLI is unchanged:

- `--scale smoke|medium|stress`
- `--seed <int>`

For a fixed scale, seed, and template/case inputs, generated corpus, cases, and manifest content are byte-stable. The manifest includes source-family/category/authority counts and SHA-256 hashes for generated files.

## Generate and validate

Generate a smoke dataset:

```powershell
cd C:\ivy\MoME-MoCE-Exp
python scripts\generate_context_stress_dataset.py --scale smoke --seed 123
python scripts\validate_context_stress_dataset.py --dataset out\context_stress_smoke
```

Generate a medium dataset:

```powershell
python scripts\generate_context_stress_dataset.py --scale medium --seed 123
python scripts\validate_context_stress_dataset.py --dataset out\context_stress_medium
```

Generate a stress dataset:

```powershell
python scripts\generate_context_stress_dataset.py --scale stress --seed 123
python scripts\validate_context_stress_dataset.py --dataset out\context_stress_stress
```

## Outputs

Each run writes:

- `corpus/corpus_items.jsonl`
- `metadata/dataset_manifest.json`
- `eval/cases.json`

The generator recreates the scale-specific output directory before writing.

## Template compatibility

The generator accepts normalized `templates` records and existing fixture sections such as `records`, `policy_records`, `override_attempts`, `json_failure_patterns`, `tool_traces`, `tool_debug_failures`, `debug_failures`, `debug_log_patterns`, and `distractors`. Additional top-level list-of-object sections are also ingested as forward-compatible template records.

## Validation report

The validator checks:

- required output files and JSON/JSONL parseability;
- corpus item shape, duplicate IDs, non-empty text, and list-valued metadata fields;
- required eval categories and required/forbidden source references;
- stale/conflict/decoy coverage;
- manifest counts, token target, file paths, and file hashes.

It prints `PASS` or `FAIL`, then a bounded list of errors/warnings plus summary counts.
