# IVY Memory Packet Preview

Phase 2A adds read-only memory packet preview. It is MoME/MoCE-shaped, but passive.

It does not inject memory into prompts. The agent never sees the packet. No agent runtime behavior changes.

## Definitions

- MoME asks: which memories matter?
- MoCE asks: how should those memories be packaged into context?

In Phase 2A both are dry-run only. The packet is printed and saved for evaluation.

## Architecture

```text
query/task
  -> rule-based task classifier
  -> memory policy
  -> memory experts
     keyword / vector / hybrid / recent / failure / benchmark / safety / workflow
  -> candidate dedupe and deterministic ranking
  -> composer
     minimal / debugging / benchmark / safety / workflow / planning
  -> packet.txt + packet.json
```

Every packet line includes provenance when available. Missing provenance is explicitly marked as a caution.

## Files

- `ivy_agent_demo/memory_packet.py`
- `ivy_agent_demo/memory_router.py`
- `ivy_agent_demo/context_packet.py`
- `ivy_agent_demo/memory_packet_cli.py`
- `ivy_agent_demo/memory_packet_eval.py`
- `ivy_agent_demo/memory_packet_eval_cases.json`
- `ivy_agent_demo/memory_policies/*.json`
- `ivy/scripts/preview_memory_packet.ps1`
- `ivy/scripts/rerun_memory_packet_eval.ps1`

## Preview Commands

```powershell
python -m ivy_agent_demo.memory_packet_cli preview --query "json tool call failed because qwen emitted think tags"
```

```powershell
python -m ivy_agent_demo.memory_packet_cli preview --query "benchmark qwen 4060 ctx 512 decode_tps" --policy benchmark --top-k 5
```

```powershell
python -m ivy_agent_demo.memory_packet_cli preview --query "absolute path policy violation" --policy safety_first --top-k 5
```

PowerShell helper:

```powershell
powershell -ExecutionPolicy Bypass -File ivy\scripts\preview_memory_packet.ps1 `
  -Query "json tool call failed because qwen emitted think tags" `
  -Policy failure_first `
  -TopK 5
```

## Policies

- `none`: baseline empty packet.
- `keyword_only`: FTS/keyword expert only.
- `vector_only`: hashed-vector expert only.
- `hybrid_default`: keyword, vector, hybrid, recent.
- `failure_first`: failure, keyword, vector, hybrid.
- `benchmark`: benchmark, keyword, hybrid.
- `safety_first`: safety, keyword, failure, hybrid.
- `recent_buffer`: recent items only.

## Artifacts

Preview outputs:

```text
runs/memory_packet_preview/<timestamp>/
  packet.txt
  packet.json
  candidates.json
  routing_decision.json
  packet_report.md
```

Compare outputs:

```text
runs/memory_packet_preview/<timestamp>/
  comparison_report.md
  comparison_results.json
  packet_<policy>.txt/json
```

## Packet Eval

```powershell
python -m ivy_agent_demo.memory_packet_eval --cases ivy_agent_demo/memory_packet_eval_cases.json --compare-latest
```

Outputs:

```text
runs/memory_packet_eval/<timestamp>/
  packet_eval_report.md
  packet_eval_results.json
  packet_eval_results.csv
  packet_eval_config.json
```

History:

```text
runs/memory_packet_eval/history.jsonl
runs/memory_packet_eval/history.csv
```

## Self-Test

```powershell
python -m ivy_agent_demo.memory_packet_cli self-test
```

The self-test builds a synthetic DB under `runs/memory_packet_preview/selftest_<timestamp>` and does not pollute default memory.

## Interpreting Results

- Packet term hit rate checks expected words in the composed packet.
- Provenance line rate checks how many packet lines include source evidence.
- Expert/composer hit rates check routing behavior.
- Packet chars and latency are used before any active prompt experiment.

## Known Limitations

- Task classification is rule-based.
- Ranking is deterministic and simple.
- Hashed vectors remain retrieval hints.
- Sparse real DBs can miss expected packets.
- The previous absolute-path retrieval case may still need better source memories.

## Phase 2B Packet Quality

Phase 2B adds grouping, compression, diversity controls, and packet-quality metrics. It is still preview-only.

Repeated memories are grouped before packet text is produced. For example, several Qwen benchmark response memories that all say `<think>` tags appeared before or inside generated text are compressed into one validation/debug warning line with multiple supporting artifacts.

Policy controls include:

- `enable_grouping`
- `max_groups_per_kind`
- `max_evidence_per_group`
- `min_distinct_kinds`
- `diversity_bonus`
- `duplicate_penalty`
- `max_repeated_kind_fraction`

Packet metrics include:

- raw and grouped candidate counts
- evidence count
- unique kind count
- duplicate group count
- compression ratio
- chars per evidence
- provenance line rate

Inspect `packet_report.md` for grouped evidence and raw candidate tables.

## Next Step

Run packet eval on real memory and inspect misses. Only after packet quality is stable should Phase 2B evaluate packet quality more deeply, still without prompt injection.

## Broader Sweep

Phase 2B.5 adds `memory_packet_sweep.py` for broader real task categories and policy matrix comparison.

```powershell
python -m ivy_agent_demo.memory_packet_sweep --cases ivy_agent_demo/memory_packet_eval_real_cases.json --compare-latest --inspect-failures
```

The sweep reports overclaim, overcompression, empty packet, latency, size, and policy-by-category findings.
