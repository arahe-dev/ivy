# IVY Memory Packet Sweep

Phase 2B.5 runs a broader real packet evaluation sweep before any prompt injection experiment.

The sweep asks whether read-only memory packets remain useful across task categories, whether policies behave differently, and whether packets overclaim or overcompress evidence. It does not change agent behavior and does not inject packets into prompts.

## Run

```powershell
python -m ivy_agent_demo.memory_packet_sweep --cases ivy_agent_demo/memory_packet_eval_real_cases.json --compare-latest --inspect-failures
```

Filter by category:

```powershell
python -m ivy_agent_demo.memory_packet_sweep --cases ivy_agent_demo/memory_packet_eval_real_cases.json --category safety --compare-latest --inspect-failures
```

Compare selected policies:

```powershell
python -m ivy_agent_demo.memory_packet_sweep --cases ivy_agent_demo/memory_packet_eval_real_cases.json --policies hybrid_default failure_first safety_first --compare-latest --inspect-failures
```

PowerShell helper:

```powershell
powershell -ExecutionPolicy Bypass -File ivy\scripts\rerun_memory_packet_sweep.ps1 -CompareLatest -InspectFailures
```

## Outputs

```text
runs/memory_packet_sweep/<timestamp>/
  sweep_report.md
  sweep_results.json
  sweep_results.csv
  sweep_config.json
  packets/
  comparisons/
    policy_comparison.md
    category_summary.md
    failure_inspection.md
```

History:

```text
runs/memory_packet_sweep/history.jsonl
runs/memory_packet_sweep/history.csv
```

## Interpreting Results

- `packet_term_hit_rate`: expected case terms appeared in packet text.
- `overclaim_risk_count`: strong language appeared with weak or missing evidence.
- `overcompression_risk_count`: grouping may have hidden distinctions.
- `empty_packet_count`: policy returned no memory.
- `best_policy_by_category`: simple comparative score, not absolute truth.

Overclaim warnings are audit signals, not hard failures. Inspect the packet text and evidence table.

Overcompression warnings mean a grouped packet may need a more specific summary or different policy.

## Phase 2C Readiness

A policy is a safer Phase 2C candidate when it has:

- low empty-packet rate
- low overclaim risk
- low overcompression risk
- high provenance
- compact packet size
- useful category-specific hits

This sweep is still preview-only. It is a gate before any opt-in prompt injection experiment.

## Coverage Backfill

Phase 2B.6 adds docs/source ingestion and coverage checks for weak safety, workflow, and runbook memories before prompt injection.

Run coverage backfill before using sweep results to choose Phase 2C policies:

```powershell
python -m ivy_agent_demo.memory_doc_ingest --all-defaults --include-source
python -m ivy_agent_demo.memory_coverage_check
python -m ivy_agent_demo.memory_packet_sweep --cases ivy_agent_demo\memory_packet_eval_real_cases.json --compare-latest --inspect-failures
```

See `ivy/docs/IVY_MEMORY_COVERAGE.md`.

## Ranking Cleanup

Phase 2B.7 adds source-family ranking and exact-field matching so docs/source memories help without drowning exact artifact-backed evidence.

Useful checks:

```powershell
python -m ivy_agent_demo.memory_packet_cli diagnose-ranking --query "qwen 4060 ctx 512 decode_tps" --policy benchmark --top-k 10
python -m ivy_agent_demo.memory_ranking_eval --cases ivy_agent_demo\memory_packet_ranking_cases.json --compare-latest
```

See `ivy/docs/IVY_MEMORY_RANKING.md`.

## Limitations

- Audits are deterministic heuristics.
- Real results depend on ingested memories.
- Docs/runbook questions may remain sparse unless docs are ingested as artifacts.
- The score is comparative only.
