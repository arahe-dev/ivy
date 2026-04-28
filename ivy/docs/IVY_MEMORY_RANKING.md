# IVY Memory Ranking

Phase 2B.7 cleans up packet ranking after docs/source memory backfill.

This remains passive. Ranking affects read-only packet preview and eval tools only. It does not inject memory into prompts and does not change the agent loop, validator, policy gate, or tools.

## Why This Exists

Phase 2B.6 added source-provenanced docs/source memories and improved coverage to `1.0`, but it also increased retrieval noise:

- empty packets improved from `14` to `9`
- packet term hit rate dropped from `0.82` to `0.74`
- safety hit rate dropped from `0.6667` to `0.5833`

The issue was not missing memory. The issue was that generic docs/runbook/source memories could outrank exact benchmark, safety, or workflow evidence.

## Source Families

Candidates are classified at routing time. No DB migration is required.

Families:

- `benchmark_artifact`
- `run_artifact`
- `doc_memory`
- `source_code`
- `runbook`
- `safety_policy`
- `workflow_trace`
- `unknown`

Classification uses memory kind, source artifact path, run id, and text patterns.

Examples:

- `runs/qwen36_4060_bench` or `benchmark_result` -> `benchmark_artifact`
- `policy.py`, `validator.py`, safety rules -> `safety_policy`
- `ivy/docs` or README -> `doc_memory`
- `ivy/scripts` or command examples -> `runbook`
- `runs/phase1_agent_demo` or workflow/tool memories -> `workflow_trace` or `run_artifact`

## Task-Type Preferences

Ranking applies deterministic source-family priors:

- benchmark: prefer benchmark artifacts, then run artifacts/runbooks
- safety: prefer safety policy/source code and policy-failure artifacts
- workflow: prefer workflow traces and run artifacts
- tool debug: prefer run artifacts, Qwen benchmark failures, validator/failure memories
- planning/general repo: prefer docs and runbooks

Policy JSON files can add weights through `source_family_weights` and source-specific bonuses.

## Exact Matching

Structured queries get extra boosts for exact fields:

- benchmark: `ctx=512`, `decode_tps`, `n_gpu_layers`, `cache_k`, `cache_v`, `cpu_moe`
- safety: write outside sandbox, path traversal, absolute path, delete, network, sandbox-relative
- workflow: `fs_read`, `json_validate`, `fs_write`, `calc_eval`
- runbook: `memory_eval`, `memory_packet_sweep`, ingest commands, artifact paths

Exact matching is a ranking signal, not a source of truth.

## Diagnostics

Inspect a query:

```powershell
python -m ivy_agent_demo.memory_packet_cli diagnose-ranking --query "qwen 4060 ctx 512 decode_tps" --policy benchmark --top-k 10
python -m ivy_agent_demo.memory_packet_cli diagnose-ranking --query "write outside sandbox policy" --policy safety_first --top-k 10
```

Outputs:

```text
runs/memory_ranking_diagnostics/<timestamp>/
  ranking_report.md
  ranking_results.json
  ranking_results.csv
```

Candidate JSON includes:

- `source_family`
- `base_score`
- `exact_match_score`
- `source_family_score`
- `provenance_score`
- `task_type_score`
- `final_score`
- `matched_terms`
- `ranking_notes`

## Regression Eval

Run known-miss ranking cases:

```powershell
python -m ivy_agent_demo.memory_ranking_eval --cases ivy_agent_demo\memory_packet_ranking_cases.json --compare-latest
```

PowerShell helper:

```powershell
powershell -ExecutionPolicy Bypass -File ivy\scripts\rerun_memory_ranking_eval.ps1 -CompareLatest
```

Outputs:

```text
runs/memory_ranking_eval/<timestamp>/
  ranking_eval_report.md
  ranking_eval_results.json
  ranking_eval_results.csv
  ranking_eval_config.json
```

Metrics:

- top-1 source-family hit rate
- top-3 source-family hit rate
- term hit rate
- provenance rate
- known-miss recovery rate
- average latency

## Limitations

- Source-family classification is heuristic.
- Exact matching is string-based.
- Ranking diagnostics explain candidate order; they do not prove truth.
- This phase does not change active agent behavior.
