# IVY MoME v0

IVY-MoME v0 is an opt-in, system-side memory router for experiments. It is not neural MoE, not active memory production, and not default agent behavior.

## Status

MoME v0 is implemented as a wrapper around the existing passive memory stack:

- SQLite memory ledger remains the source of truth.
- Existing keyword/vector/hybrid retrieval remains available.
- MoME policies select memory experts by task type.
- Existing MoCE-style packet composition builds compact advisory packets.
- Injection happens only inside `memory_injection_experiment.py` when a policy starts with `mome_` or `--mome` is passed.
- `agent_loop.py`, `validator.py`, `policy.py`, and `tools.py` are unchanged.

## Architecture

```text
task/query
  -> MoME task classifier
  -> MoME policy
  -> selected experts
  -> candidate retrieval and scoring
  -> packet composer
  -> opt-in experiment injection
  -> existing agent loop
  -> evaluator/report/history
```

## Experts

- `exact_keyword`
- `vector_fuzzy`
- `hybrid`
- `recent_buffer`
- `failure_debug`
- `benchmark`
- `safety_policy`
- `workflow_procedure`
- `runbook_docs`

All candidates keep provenance where available. Memory remains advisory and cannot bypass validation, policy gates, or tool execution rules.

## Policies

Policy files live under `ivy_agent_demo/mome_policies/`:

- `mome_none.json`
- `mome_hybrid_default.json`
- `mome_debug.json`
- `mome_benchmark.json`
- `mome_safety.json`
- `mome_workflow.json`
- `mome_runbook.json`
- `mome_auto.json`

`mome_auto` chooses experts by task type. Specialized policies are useful for controlled comparisons.

## Commands

Preview:

```powershell
python -m ivy_agent_demo.mome_cli preview --query "benchmark qwen 4060 ctx 512 decode_tps" --policy mome_auto --top-k 5
```

Compare:

```powershell
python -m ivy_agent_demo.mome_cli compare --query "What command reruns IVY memory eval?" --policies mome_none mome_runbook mome_auto
```

Diagnose:

```powershell
python -m ivy_agent_demo.mome_cli diagnose --query "write outside sandbox policy" --policy mome_safety --top-k 10
```

Packet eval:

```powershell
python -m ivy_agent_demo.mome_eval --cases ivy_agent_demo\mome_eval_cases.json --compare-latest
```

Opt-in injection:

```powershell
python -m ivy_agent_demo.memory_injection_experiment --cases ivy_agent_demo\memory_injection_cases.json --case-id runbook_memory_eval --policies none hybrid_default mome_runbook mome_auto --compare-latest
```

## First Results

MoME packet eval run:

```text
C:\ivy\runs\mome_eval\20260429_032713_478810
```

| Metric | Value |
|---|---:|
| packet_term_hit_rate | 1.0 |
| expert_selection_hit_rate | 1.0 |
| source_family_hit_rate | 1.0 |
| provenance_ok_rate | 1.0 |
| caution_hit_rate | 1.0 |
| empty_packet_count | 0 |
| overclaim_risk_count | 0 |
| overcompression_risk_count | 1 |

Bounded real injection results:

| Case | Result |
|---|---|
| benchmark_memory_question | `benchmark`, `mome_benchmark`, and `mome_auto` passed with supported `decode_tps` and caution wording; `none` did not pass. |
| runbook_memory_eval | `hybrid_default`, `mome_runbook`, and `mome_auto` recalled the exact command and artifact path; `none` was honest no-memory. |
| json_tool_debug_think_tags | all policies succeeded; legacy `failure_first` improved repairs/steps in one run, MoME matched success but was not consistently better. |
| calc_write_workflow | `none`, `hybrid_default`, and `mome_auto` succeeded. |
| safety_path_rule | `none`, `safety_first`, `mome_safety`, and `mome_auto` succeeded without tool calls. |

## Safety Notes

- MoME is not enabled by default.
- Normal agent runs do not receive memory packets.
- Memory packets are injected only through explicit experiment policy selection.
- Packets include advisory text and do not override the validator, policy gate, or tool schemas.
- Benchmark caution lines are preserved during experiment packet truncation.

## Limitations

- MoME v0 is a deterministic rules-and-scoring layer, not learned routing.
- Packet quality is still sensitive to context budget and ordering.
- `mome_benchmark` produced one packet-eval overcompression warning; inspect before broad benchmark use.
- The current JSON/tool-debug run showed MoME matched success but did not beat `failure_first`.
- Evaluators are case-specific and should be expanded before claiming broad behavior gains.

## Next Step

Run a bounded Phase 2C suite with repeated trials for the five current cases to separate deterministic improvements from model variance.
