# IVY Memory Coverage

Phase 2B.6 backfills passive memory coverage for safety, docs/runbook, and workflow topics before any prompt injection experiment.

This phase still does not change agent runtime behavior. It only ingests source-provenanced project material into the SQLite memory ledger and checks whether the memory DB can answer expected coverage targets.

## Why This Exists

The Phase 2B.5 packet sweep found useful packets overall, but weak coverage in safety and general repo/runbook queries:

- overall packet term hit rate: `0.82`
- safety hit rate: `0.6667`
- general repo hit rate: `0.5714`
- empty packet count: `14`
- overclaim risks: `0`
- overcompression risks: `0`

The weak areas were mostly missing source-provenanced memories, not a reason to inject memory into prompts.

## Source-Provenance Rule

Every inserted memory item must come from a real source:

- existing docs
- existing source files
- existing run artifacts
- existing benchmark artifacts
- existing eval or sweep reports

The docs/source ingester stores compact summaries with `source_artifact_path`. It does not invent memory state and does not trust model JSON as canonical memory.

## Ingest Docs And Source

Dry run:

```powershell
cd C:\ivy
python -m ivy_agent_demo.memory_doc_ingest --all-defaults --dry-run
```

Ingest default docs, selected source files, and scripts:

```powershell
python -m ivy_agent_demo.memory_doc_ingest --all-defaults --include-source
```

Equivalent memory CLI command:

```powershell
python -m ivy_agent_demo.memory_cli ingest-docs --all-defaults --include-source
```

Selected source files include `policy.py`, `validator.py`, `tools.py`, optional `schemas.py`, docs, README files, and scripts. They are parsed conservatively with text rules only.

## Check Coverage

All categories:

```powershell
python -m ivy_agent_demo.memory_coverage_check
```

Safety only:

```powershell
python -m ivy_agent_demo.memory_coverage_check --category safety
```

JSON output:

```powershell
python -m ivy_agent_demo.memory_coverage_check --json
```

Outputs are written under:

```text
runs/memory_coverage/<timestamp>/
  coverage_report.md
  coverage_results.json
  coverage_results.csv
```

History is append-only:

```text
runs/memory_coverage/history.jsonl
runs/memory_coverage/history.csv
```

## Coverage Targets

Safety:

- write outside sandbox
- path traversal
- absolute path rejection
- unsafe delete intent
- network string blocking
- sandbox-relative path rule

Workflow:

- `fs_read` then `json_validate`
- `fs_write` only under `out/`
- `calc_eval` then `fs_write`
- tool-call validation before policy execution

Runbook/docs:

- rerun memory eval command
- rerun packet sweep command
- ingest `phase1_agent_demo` runs
- ingest Qwen benchmark runs
- benchmark memory policy guidance
- where memory artifacts are saved
- where packet preview artifacts are saved
- where packet sweep artifacts are saved

## Rerun Packet Sweep

After ingestion:

```powershell
python -m ivy_agent_demo.memory_packet_sweep --cases ivy_agent_demo\memory_packet_eval_real_cases.json --compare-latest --inspect-failures
python -m ivy_agent_demo.memory_packet_sweep --cases ivy_agent_demo\memory_packet_eval_real_cases.json --category safety --compare-latest --inspect-failures
```

PowerShell helper:

```powershell
powershell -ExecutionPolicy Bypass -File ivy\scripts\rerun_memory_coverage.ps1 -AllDefaults -IncludeSource -RunSweepAfter -CompareLatest
```

## Interpreting Results

- Coverage means at least one source-provenanced memory item matches the target terms.
- A coverage miss is a source/documentation gap or parser gap, not permission to invent memory.
- Packet sweep improvement should show fewer empty packets and better category hit rates without adding overclaim risk.
- If coverage improves but packet sweep does not, inspect routing policy and packet terms before changing retrieval logic.
- If docs/source ingestion increases retrieval noise, run the Phase 2B.7 ranking diagnostics in `ivy/docs/IVY_MEMORY_RANKING.md`.

## Limitations

- Parsing is deterministic and shallow.
- Coverage matching is term-based.
- Source memories may be generic unless docs/source files contain exact wording.
- This phase remains preview-only. No memory is injected into the agent prompt.
