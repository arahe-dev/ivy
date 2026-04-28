# IVY Mem0 Experiment

## What Is Mem0?

Mem0 (https://github.com/mem0ai/mem0) is an open-source memory layer for AI agents. This experiment tests whether it can produce useful memory packets faster/more reliably than IVY-native SQLite/FTS/vector.

## Why Is It Optional?

Mem0 is an **optional** import for comparison purposes only:
- IVY-native memory remains the default
- No requirement to install Mem0
- No runtime changes without explicit opt-in
- Graceful fallback if Mem0 unavailable

## How To Install Mem0 (Optional)

```powershell
pip install mem0
```

Or for local-only (no cloud):
```powershell
pip install mem0[local]
```

Note: Mem0 may require API keys for cloud features. Review Mem0 docs for configuration.

## How To Run Without Mem0

All IVY commands work without Mem0:
- Native packet preview: `python -m ivy_agent_demo.memory_packet_cli preview ...`
- Native packet sweep: `python -m ivy_agent_demo.memory_packet_sweep ...`
- Native injection experiment: `python -m ivy_agent_demo.memory_injection_experiment ...`

Mem0 is NOT required for any IVY function.

## Comparison: IVY-Native vs Mem0

| Aspect | IVY-Native | Mem0 |
|--------|------------|------|
| Storage | SQLite + FTS | Mem0 backend |
| Search | FTS/vector hybrid | Mem0 search |
| Packet | Custom composer | Mem0 retrieval |
| Local | Yes | Requires config |
| Offline | Yes | Depends on config |
| Dependencies | stdlib | Optional pip |
| Provenance | Native support | Via metadata |

## What Data Gets Ingested

The Mem0 adapter only ingests from existing IVY memory:
- Compact memory_item text (not raw tool args)
- metadata: source_artifact_path, kind, run_id
- Avoids huge artifacts
- Preserves provenance via metadata

No new data collection. Only imports existing memory from SQLite.

## Privacy/Locality Caveats

- If using Mem0 cloud: data leaves local machine
- Review Mem0 privacy policy
- Local-only Mem0 configuration may be available
- IVY-native memory stays local by default

## How To Remove/Disable Mem0

1. Do NOT install Mem0 pip package
2. Use IVY-native commands only
3. Comparison harness reports Mem0 unavailable gracefully
4. No runtime changes occur

## Comparison Commands

```powershell
# Dry-run comparison
python -m ivy_agent_demo.memory_backend_compare --cases ivy_agent_demo\memory_injection_cases.json --backends ivy_native,mem0 --dry-run

# Real comparison with eval cases
python -m ivy_agent_demo.memory_backend_compare --cases ivy_agent_demo\memory_packet_eval_real_cases.json --backends ivy_native,mem0
```

## Expected Outcomes

- IVY-native should work reliably (baseline)
- Mem0 may show improvement if installed and configured
- If Mem0 unavailable, harness reports gracefully
- Both should respect safety constraints

## Rollback/Safety

After experiment:
```powershell
git diff -- ivy_agent_demo\validator.py ivy_agent_demo\policy.py ivy_agent_demo\tools.py
```

If diff is non-empty, abort and report.

## Criteria For Deeper Integration

Before replacing IVY-native with Mem0, require:
1. Measurable success rate improvement (not just term hit)
2. Comparable or better latency
3. Privacy/locality preserved
4. No provenance metadata loss
5. Clear user consent mechanism
6. Graceful fallback if Mem0 unavailable

Current Phase: Experimentation only. No production integration planned.