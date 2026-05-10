# MoME-MoCE Context Stress Experiment

This experiment builds a synthetic evidence-routing benchmark for IVY.

The goal is not to create one giant long-context prompt. The goal is to create
a large local corpus with known provenance, authority, conflicts, decoys, stale
records, and gold eval cases so MoME/MoCE can be tested on whether it finds the
right small working set from a much larger evidence space.

## Benchmark Contract

A valid run must test routing, not memorization. Each answerable case should be
solvable from a compact evidence packet whose source IDs, source families,
authority levels, and provenance metadata are known in advance. Each
unanswerable or general-knowledge case should make retrieval optional or
unwanted and should penalize invented local facts.

The benchmark should preserve these invariants:

- Every corpus item has a stable ID, a source family, an authority level, a
  creation date, staleness status, safety label, provenance, tags, and text.
- Current records should identify stale records through `supersedes` when the
  generator has that relationship. Conflicting records should identify peers
  through `conflicts_with` when the conflict is intentional.
- Decoys must be explicit: use `authority: decoy`, `source_family: distractor`,
  or `safety_label: unsafe_decoy` as appropriate. They should look plausible in
  text but remain mechanically identifiable for scoring.
- Safety-policy records outrank memory, workflow traces, and distractors. A
  successful past trace is never evidence that a safety rule can be ignored.
- Benchmark artifacts must carry enough provenance to distinguish latest,
  stale, single-run, and conflicting measurements.

## Target Scales

| Scale | Approx tokens | Purpose |
|---|---:|---|
| smoke | 50k | Validate schemas, generation, and eval plumbing. |
| medium | 200k | Exercise retrieval/ranking quality and case coverage. |
| stress | 2m | Measure routing degradation, latency, and compression under load. |

## Evidence Families

- `doc_memory`: architecture notes, stable explanations, project docs.
- `runbook`: exact commands, artifact locations, operational steps.
- `benchmark_artifact`: timestamped benchmark measurements and configs.
- `safety_policy`: sandbox/tool/policy rules and override traps.
- `workflow_trace`: successful and failed tool sequences.
- `debug_failure`: validation failures, JSON contamination, repair patterns.
- `source_code`: synthetic module/function notes.
- `distractor`: plausible but wrong or low-authority evidence.

## Required Phenomena

- Exact command/path recall.
- Latest-vs-stale benchmark selection.
- Conflict detection and decoy resistance.
- Safety policy priority over memory claims.
- Workflow/procedure recall.
- Debug failure recall.
- Unanswerable cases that require abstention.
- General cases where retrieval should be skipped.

## Eval Case Requirements

Each case should state:

- `should_retrieve`: whether local evidence is needed at all.
- `required_source_ids`: the minimum authoritative records expected in the
  evidence packet.
- `forbidden_source_ids`: records that must not be treated as authoritative.
- `expected_terms` and `forbidden_terms`: lightweight answer-shape checks.
- `must_abstain`: whether the correct behavior is to refuse a local claim.
- Optional routing hints such as `required_source_families`, expected authority,
  staleness requirements, safety priority, and conflict expectations.

For conflict cases, the required set may include both sides of the conflict, but
the answer must still choose the authoritative/current record and cite why stale
or decoy evidence was rejected. For unanswerable cases, `required_source_ids`
should normally be empty and `must_abstain` true.

## Evaluation Principle

Each case must declare the source IDs that should be retrieved and the source IDs
that must not be treated as authoritative. The benchmark should reward compact,
provenance-backed packets and penalize unsupported exact claims, stale claims,
unsafe policy overrides, and decoy-derived answers.

A good answer cites or otherwise preserves provenance for exact local claims. A
bad answer may be fluent but will over-retrieve, cite stale evidence as current,
accept a distractor, ignore conflict metadata, or invent unavailable local facts.

## Non-Goals

- No real secrets or proprietary facts.
- No dependence on remote APIs for dataset generation.
- No use of model output as ground truth without deterministic metadata.
- No assumption that a model can ingest the entire corpus as context.
- No hidden scoring rules that are absent from schemas or deterministic metadata.
