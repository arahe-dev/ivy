# Next Chat Handoff ? MoME/MoCE / ACCA / ESCAPE

Date: 2026-05-10
Project path: `C:\ivy\MoME-MoCE-Exp`
Previous working directory: `C:\Users\arahe`

## Update after CP7/CP8/CP9 build

CP7 and CP8 are implemented and verified. CP9 has a working Rust candidate-index prototype and probe, but it is not yet integrated as the authoritative proof-producing router backend. Read `docs/CP7_CP9_STATUS_2026-05-10.md` before continuing.

Current verified checkpoint:

```text
ivy_real scan:     30/30, required-only precision 1.0, artifact_errors 0
ivy_real indexed:  30/30, required-only precision 1.0, artifact_errors 0
smoke indexed:     62/62, required-only precision 1.0, artifact_errors 0
medium indexed:    62/62, required-only precision 1.0, artifact_errors 0
stress indexed:    62/62, required-only precision 1.0, artifact_errors 0
stress scan:       62/62, required-only precision 1.0, artifact_errors 0
rust ivy_real:     recall@32 1.0, failed_cases 0
rust stress:       recall@32 1.0, failed_cases 0
pytest:            10 passed
```

New artifacts and reports:

- `out\context_stress_ivy_real\`
- `out\harness_ivy_real_cp7.json`
- `out\harness_ivy_real_cp8_indexed.json`
- `out\harness_smoke_cp8_indexed.json`
- `out\harness_medium_cp8_indexed.json`
- `out\harness_stress_cp8_scan.json`
- `out\harness_stress_cp8_indexed.json`
- `out\rust_index_probe_ivy_real.json`
- `out\rust_index_probe_stress.json`

The next implementation batch should start after CP9:

1. make Rust an optional direct backend instead of a `cargo run` probe;
2. compare Rust and Python candidates against golden traces before trusting Rust in route proofs;
3. split Python router internals into explicit expert/gate classes;
4. expand taint/exposure-policy fields and add more Ivy-real cases.

## Update after CP3/CP4/CP5/CP6 build

CP3, CP4, CP5, and CP6 have now been implemented and verified. Read `docs/CP3_CP6_STATUS_2026-05-10.md` before continuing.

Current verified checkpoint:

```text
smoke:  62/62, required-only precision 1.0, artifact_errors 0
medium: 62/62, required-only precision 1.0, artifact_errors 0
stress: 62/62, required-only precision 1.0, artifact_errors 0
pytest: 7 passed
```

New artifacts and reports:

- `out\routing_artifacts_smoke\index.json`
- `out\routing_artifacts_medium\index.json`
- `out\routing_artifacts_stress\index.json`
- `out\baseline_comparison_smoke.md`
- `out\baseline_comparison_stress.md`
- `out\mutation_dropout_smoke.md`
- `out\mutation_dropout_stress.md`

This batch led into CP7/CP8/CP9:

1. build a hand-labeled Ivy-real dataset from actual runbooks, commands, logs, and source references;
2. split the router into explicit expert/gate classes behind the stable proof/packet ABI;
3. add richer taint/exposure-policy fields beyond authority/staleness/provenance;
4. optimize retrieval only after the ABI remains stable.

## Earlier update after CP0/CP1/CP2 build

CP0, CP1, and CP2 have now been implemented and verified in this repo. Read `docs/CP0_BASELINE_2026-05-10.md` and `docs/CP1_CP2_STATUS_2026-05-10.md` before continuing.

The next implementation batch should start at CP3/CP4:

1. make route proofs the primary persisted artifact for every harness mode;
2. enforce compactness/capacity/taint/exposure as pass/fail metrics;
3. add baseline runners and comparison tables after compactness is enforced.

## Read this first in a new chat

Use this prompt:

```text
Read `C:\ivy\MoME-MoCE-Exp\docs\NEXT_CHAT_HANDOFF.md`, then inspect the project. Continue from the amended plan. Do not use Paseo; use Codex-native tools/subagents only if delegation is explicitly requested. Start after CP9 unless I say otherwise.
```

Important docs already saved:

- `docs/MOCE_MOME_RESEARCH_NOTES.md` ? MoCE/MoME core framing, MoE mapping, local Qwen result, research notes.
- `docs/ACCA_ESCAPE_SUPERCHARGED_DESIGN.md` ? ACCA/ESCAPE architecture, MoE-adjacent concepts, route-proof/context-ABI framing, resources.
- `docs/AUDIT_REPORTS_2026-05-10.md` ? two Codex audit agents' full critiques and amended recommendations.
- `docs/CP3_CP6_STATUS_2026-05-10.md` ? persisted artifacts, compactness, baselines, mutation/dropout results.
- `docs/CP7_CP9_STATUS_2026-05-10.md` ? Ivy-real dataset, indexed backend, Rust probe results.
- `docs/NEXT_CHAT_HANDOFF.md` ? this checkpoint.

## Operating preferences / constraints

- User explicitly said: **do not use Paseo subagent workflow; use Codex**.
- If using agents, use Codex-native `spawn_agent`; only delegate when explicitly requested.
- Current backend in prior chat: `kimi-k2.6` via the `opencode-go` provider.
- Keep communication direct, pragmatic, and rigorous.
- Do not overclaim novelty or paper-readiness.

## Current project state

Folder:

```text
C:\ivy\MoME-MoCE-Exp
```

Key files:

```text
docs\MOCE_MOME_RESEARCH_NOTES.md
docs\ACCA_ESCAPE_SUPERCHARGED_DESIGN.md
docs\HARNESS.md
docs\PROJECT_BRIEF.md
docs\RUNBOOK.md
scripts\mome_moce_harness.py
scripts\generate_context_stress_dataset.py
scripts\generate_ivy_real_dataset.py
scripts\validate_context_stress_dataset.py
scripts\run_rust_index_probe.py
rust\acca_index\
schemas\*.json
eval\cases_seed.json
```

Current compact harness results:

```text
ivy_real scan:    30/30, required-only precision 1.0, artifact_errors 0, ~1.9 ms mean
ivy_real indexed: 30/30, required-only precision 1.0, artifact_errors 0, ~1.1 ms mean
smoke indexed:    62/62, required-only precision 1.0, artifact_errors 0, ~4.6 ms mean
medium indexed:   62/62, required-only precision 1.0, artifact_errors 0, ~13.7 ms mean
stress indexed:   62/62, required-only precision 1.0, artifact_errors 0, ~124.4 ms mean
stress scan:      62/62, required-only precision 1.0, artifact_errors 0, ~307.3 ms mean
```

Important caveat: the Ivy-real set is still small and hand-curated. CP9 Rust currently proves candidate recall only; it does not yet emit route proofs or frontier packets.

Local GGUF path:

```text
C:\Users\arahe\Downloads\Qwen3-4B-Q4_K_M.gguf
```

Observed local Qwen result:

```text
GGUF loads, but CPU generative reranking is too slow: roughly 18?37s per local rerank call.
```

Conclusion: local Qwen should be optional/advisory/probe-only, not hot-path authority.

## Core research framing

The best framing is:

> **ACCA is an auditable authority-constrained context compiler for agent memory.**

MoCE/MoME are the supporting architecture terms:

- **MoCE**: Mixture of Context Experts ? router/compiler/gates deciding what context is needed and admissible.
- **MoME**: Mixture of Memory Experts ? external memory expert pool proposing evidence.
- **ACCA**: Authority-Constrained Context Assembly ? algorithm/compiler that filters, ranks, rejects, packs, and proves evidence choices.
- **ESCAPE**: optional prototype/system name ? External Sparse Context And Provenance Experts.

Strong novelty claims:

- authority-aware context compilation;
- selected and rejected evidence in route proofs;
- external sparse expert routing mapped from MoE concepts;
- explicit handling of stale, decoy, conflict, safety, taint, and abstention;
- compact frontier context ABI;
- negative result: local LLM reranking is not a safe/fast authority mechanism.

Avoid claims:

- ?we invented MoME?;
- ?new neural MoE method?;
- ?small model remembers for big model?;
- ?fast RAG? as the main claim;
- ?synthetic 62/62 proves general reliability.?

## MoE-mapped concepts to preserve

These are already in the research docs and should remain part of ACCA/ESCAPE design:

1. Context capacity factor.
2. Expert overflow policies.
3. Router confidence margin.
4. Anti-routing-collapse / expert load balancing.
5. Shared experts vs routed experts.
6. Expert-choice routing, where experts can claim a query.
7. Mixture of depths for context work.
8. Residual/no-context path.
9. Expert dropout / missing-expert robustness.
10. Admissibility/routing loss.
11. Authority-weighted routing logits.
12. Expert locality / memory placement.
13. All-to-all cost analogy for memory expert coordination.
14. Speculative context routing, with small models as proposers only.
15. Conflict graph as an expert memory, not postprocessing.
16. Taint tracking for context.
17. Memory TTL and supersession semantics.
18. Context ABI / packet interface.
19. Route proof schema as a first-class artifact.
20. WAND / Block-Max WAND as internal retrieval optimization, not novelty.
21. Learned sparse retrieval as optional future expert.
22. Late-interaction expert, e.g. ColBERT-style semantic recall.
23. Cascaded/frugal routing.
24. Authority-chain compression.
25. Mutation testing for memory systems.
26. Memory write barrier.
27. Evidence quorum.
28. Abstention as a routing outcome.
29. Evidence utility per token.
30. Frontier exposure budget.

## Relevance of SubQ/SSA-style idea

The user asked about `https://subq.ai/how-ssa-makes-long-context-practical` but does not trust it. Treat it as inspiration only, not authority.

Potentially useful transferable ideas:

- segment/state summaries;
- sparse access to relevant context regions;
- routing before full context exposure;
- memory placement and compression;
- keeping a compact state rather than re-reading everything.

Do not cite or rely on it as a primary source unless verified. ACCA should be grounded in route proofs, admissibility, classic retrieval, MoE analogies, and local eval.

## Hard blockers found by Codex audit agents

1. Schema drift is blocking.
   - Manifest schema expects `context_stress_manifest.v0.1`, generator emits `v0.2`.
   - Manifest schema forbids generated fields like `authority_counts`, `staleness_counts`, `template_stats`, `file_sha256`, `generator`, `token_target_met`.
   - Corpus schema forbids `staleness: "decoy"`, but generated corpora use it.
   - Corpus `provenance` has fields absent from schema.
   - Eval schema describes a single case object, but actual eval files wrap cases as `{schema_version, cases}`.
   - Validator is custom shape checking, not strict JSON Schema validation.

2. Route proofs cannot be fake.
   - Current harness is mostly monolithic scoring.
   - It labels `MoME.sparse_lexical_memory` / `MoCE.authority_conflict_filter`, but there are not yet real independent expert modules.
   - Real expert/gate interface should come before final proof claims.

3. Evaluation is too forgiving.
   - `expected_terms`, `forbidden_terms`, `retrieval_ratio_target`, and compactness are not enforced enough.
   - Many successful cases select 5 items when only 1?2 are required.

4. No real test/dependency contract yet.
   - Need `pyproject.toml` or requirements.
   - Need `jsonschema` dependency or equivalent.
   - Need regression tests/golden outputs.

5. Local Qwen should not be a required baseline gate.
   - Keep optional and capped.

6. Rust and streaming are premature.
   - Rust only after stable proof/context ABI and Python golden traces.
   - Streaming requires content-addressed IDs, migrations, incremental indexing, dedupe, taint policy, and concurrency semantics.

## Amended build plan

Status: CP0 through CP8 are complete. CP9 has a verified candidate-recall prototype, but still needs direct-backend integration before it can replace Python candidate generation in route-proof runs.

### CP0 ? Observed baseline freeze

- Record current deterministic smoke/medium/stress results.
- Record current schema drift as known failing contract.
- Do not treat current baseline as schema-clean.

### CP1 ? Contract/schema repair

- Repair manifest/corpus/eval wrapper schemas.
- Add `route_proof.schema.json` and `frontier_context_packet.schema.json` as draft contracts.
- Update validator to run JSON Schema plus semantic checks.
- Add dependency file and automated tests.

### CP2 ? Router/expert interface refactor

- Split monolithic scoring into named experts/gates.
- Preserve current 62/62 behavior with golden tests.
- Emit real `activated_experts`, `expert_claims`, candidate lists, and rejection reasons.

### CP3 ? Route proofs and context ABI

Produce schema-valid route proofs for every case with:

- selected evidence;
- rejected evidence;
- overflowed evidence;
- conflict pairs;
- authority chain;
- answerability;
- latency;
- token counts.

### CP4 ? Capacity, compactness, taint/exposure

- Add token budget policy.
- Add overflow policy.
- Add taint labels.
- Add exposure rules.
- Enforce compactness metrics and max evidence constraints.
- Reduce filler/support over-selection.

### CP5 ? Baseline runner

Compare:

- naive BM25/top-k;
- BM25 + source-family filter;
- exact-anchor only;
- deterministic ACCA;
- optional local Qwen reranker;
- optional hybrid ACCA + local advisory.

Produce tables for:

- evidence recall;
- evidence precision;
- forbidden-hit rate;
- stale-accept rate;
- decoy-accept rate;
- abstention accuracy;
- conflict-pair recall;
- utility/token;
- p50/p95 latency;
- token savings.

### CP6 ? Robustness/dropout

- Expert dropout flags.
- Metadata ablations: no freshness, no conflict graph, no safety labels.
- Mutation tests:
  - stale duplicate;
  - decoy path;
  - wrong source family;
  - missing exact ID;
  - unsafe/private evidence;
  - disabled benchmark expert;
  - disabled conflict graph;
  - disabled safety gate.

### CP7 ? Real Ivy mini-dataset

- Complete: `out\context_stress_ivy_real` has 37 evidence items and 30 labeled cases.
- Includes expected evidence IDs/paths, rejected evidence, freshness/conflict labels, safety labels, and answerability labels.

Distribution is 3 cases for each benchmark category.

### CP8 ? Indexed Python backend

- Complete: `--candidate-backend indexed` adds token postings, family indexes, ID maps, and conflict/supersession expansion behind the existing proof/packet ABI.
- Verified on Ivy-real, smoke, medium, and stress with exact quality preserved.

### CP9 ? Rust prototype, conditional

- Prototype complete: `rust\acca_index` and `scripts\run_rust_index_probe.py` preserve required-evidence recall@32 on Ivy-real and stress.
- Not complete as a backend: it does not yet emit ACCA route proofs/frontier packets or run without `cargo run` overhead.

### CP9 follow-up ? Direct Rust backend

- Compile once and call the binary directly.
- Emit stable candidate diagnostics.
- Compare Rust/Python candidate sets on golden cases.
- Wire Rust behind `candidate_backend` only after candidate parity is stable.

### CP10 ? Streaming ingestion/write barrier

- Defer for now.
- Revisit after stable schemas, indexes, and real-data governance exist.

## Go/no-go gates

### Gate 1 ? Engineering validity

Proceed only if:

- route proof and packet schemas validate on every run;
- no mixed packet sentinel strings;
- generated corpus has zero dangling relationship refs;
- deterministic smoke/medium/stress runs are reproducible.

### Gate 2 ? Evaluation validity

Proceed only if:

- ACCA beats BM25/top-k on admissibility, not just recall;
- over-retrieval is penalized;
- mutation tests expose baseline failures;
- expert dropout shows interpretable degradation.

### Gate 3 ? Paper validity

Submit EMNLP Industry only if by writing freeze there is:

- 30+ real Ivy labeled queries;
- baseline comparison table;
- synthetic + real eval;
- p95 latency/token-savings table;
- route-proof examples;
- clear negative local-LLM result.

If not, pivot to RAGE-KG or an internal technical report.

## Venue notes

Prior chat verified these URLs on 2026-05-10; recheck before final submission.

- EMNLP 2026 Industry Track: https://2026.emnlp.org/calls/industry_track/
  - deadline noted: 2026-06-16 AoE.
- RAGE-KG 2026: https://2026.rage-kg.org/
  - better backup if emphasizing authority/conflict graph and route proofs.
- EMNLP main/ARR: possible but too risky unless empirical results improve quickly.

## Immediate next implementation batch

Start here unless the user changes direction:

1. CP0: create observed baseline artifacts.
2. CP1: add dependency contract and strict JSON Schema validation.
3. Repair schemas/generator/validator together.
4. Add golden regression tests.
5. CP2: refactor harness into explicit experts/gates.
6. Preserve current recall but add precision/compactness metrics.

Do not start with Rust, GPU local models, or learned routers.
