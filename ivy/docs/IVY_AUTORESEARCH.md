# IVY AutoResearch

## Purpose

AutoResearch is a bounded experiment harness for IVY memory packet and ranking improvements. It orchestrates small, auditable trials and records results without touching the active agent runtime.

## How it differs from active agent runtime

- It never injects memory into prompts.
- It runs offline evals and packet previews only.
- It does not modify agent loop behavior or policy gates.

## Why it is safe

- Strict allowed/forbidden file lists.
- Guardrails verify forbidden files are unchanged.
- Prompt injection checks are run after each iteration.
- It is bounded by iteration and time limits.

## Dry run

```powershell
python -m ivy_agent_demo.autoresearch --config ivy_agent_demo/autoresearch_config.json --dry-run
```

Dry-run prints the planned candidates, commands, and criteria without running evals.

## Bounded experiment

```powershell
python -m ivy_agent_demo.autoresearch --config ivy_agent_demo/autoresearch_config.json --research-target safety_packet_wording --max-iterations 3 --max-minutes 45
```

Use `--no-apply` to produce TODO stubs without changing code:

```powershell
python -m ivy_agent_demo.autoresearch --config ivy_agent_demo/autoresearch_config.json --no-apply
```

## Success and failure criteria

Each candidate defines metrics to improve and constraints to keep (e.g., overclaim risk stays 0). AutoResearch compares post-eval metrics against baseline and rejects or accepts the candidate. Failed experiments remain recorded in the reports.

## Inspecting reports

Reports are written to `runs/autoresearch/<timestamp>/` with per-iteration metrics, logs, and decisions. A rollup report summarizes the full run.

## Manual rollback

AutoResearch does not auto-revert. If a change is rejected, revert manually using `git diff` or the saved `diff.patch` in the iteration folder.

## Current first research target

`safety_packet_wording` aims to preserve exact safety policy identifiers (e.g., `write_outside_sandbox`, `unsafe_delete_network`) in packet lines while keeping overclaim risk at zero.

## Prompt injection remains blocked

AutoResearch explicitly checks agent loop files for new prompt injection paths. It does not modify or access agent runtime behavior.

## Report layout

Each run writes:

- `autoresearch_config_used.json`
- `baseline_metrics.json`
- `iteration_###/` (candidate spec, metrics, logs, decision, diff)
- `autoresearch_report.md`
- `autoresearch_results.json`

## Metrics snapshots

Use the metrics helper to capture the current latest run:

```powershell
python -m ivy_agent_demo.autoresearch_metrics snapshot --label baseline_pre_autoresearch
```
