# Codex Audit Reports ? 2026-05-10

Project: `C:\ivy\MoME-MoCE-Exp`

These two Codex audit agents were launched after the five-agent checkpoint plan. They inspected the project read-only and did not edit files.

## Audit A ? Technical implementation audit

Audit complete. I did not edit files.

### Blocking issues

1. **CP1 schema repair is not optional; current formal schemas do not match generated artifacts.**
   - `dataset_manifest.schema.json` requires `schema_version: context_stress_manifest.v0.1`, but generator emits `v0.2`.
   - Manifest schema has `additionalProperties: false`, but generated manifests include `authority_counts`, `staleness_counts`, `template_stats`, `file_sha256`, `generator`, `token_target_met`.
   - `corpus_item.schema.json` forbids `staleness: "decoy"`, but generated corpora contain it.
   - Corpus `provenance` contains fields like `record_key`, `record_index`, `generated_from`, `seed`, `support_index`, but schema forbids them.
   - `eval_case.schema.json` describes one case object, while actual `cases.json` is a wrapper object with `{schema_version, cases}`.
   - Current validator is a custom shape checker, not JSON Schema validation. It passes despite schema drift.

2. **CP2 route proofs before CP3 expert routing risks producing ?fake? proof fields.**
   - Current harness is still a monolithic full-corpus scan with heuristic scoring.
   - `route_trace` labels things as `MoME.sparse_lexical_memory` / `MoCE.authority_conflict_filter`, but there are no actual expert modules with independent activation, outputs, or capacities.
   - If CP2 emits `activated_experts`, `expert_outputs`, `router_scores`, etc. before CP3, those fields will likely be retrofitted and churn later.

3. **Evaluation is currently too forgiving for paper claims.**
   - Existing smoke deterministic run passes `62/62`, but scoring only checks required/forbidden IDs.
   - `expected_terms`, `forbidden_terms`, `retrieval_ratio_target`, and compactness are not enforced by `evaluate_case`.
   - Many successful cases select 5 items, often including filler/support records. That is fine for recall, but weak for ?compact admissible packet? claims.

4. **No real test harness / dependency contract.**
   - No `pyproject.toml`, requirements file, pytest suite, or JSON Schema validator dependency.
   - CP1 will need an explicit dependency decision, likely `jsonschema`, plus regression tests.

5. **Local Qwen baseline should not be a required baseline gate.**
   - Docs already note local GGUF inference is slow and sometimes selects stale/decoy evidence.
   - Keep it as optional/advisory/probe-only, not a required CP5 baseline unless capped with `--limit`.

6. **CP9 Rust and CP10 streaming are premature.**
   - Rust needs a stable route-proof/context ABI and golden traces first.
   - Streaming ingestion needs content-addressed IDs, migrations, incremental indexing, dedupe, taint policy, and concurrency semantics. None exist yet.

### Recommended changes

- **Split schema repair into schema + generator + validator + fixtures.** Do not ?fix schemas? alone.
- **Insert an explicit test checkpoint after CP1.** Minimum tests:
  - generated smoke/medium/stress validate against formal schemas;
  - manifest hashes/counts match;
  - 62-case golden selected IDs remain stable;
  - no decoy/stale evidence selected unless case requires contrast/conflict;
  - route proof validates and is internally consistent.
- **Move real expert architecture before full route proofs**, or split CP2 into a minimal proof adapter followed by final proof after CP3.
- **Enforce compactness before baselines.** Capacity/taint/packet packing should happen before final baseline tables, otherwise comparisons are not fair.
- **Cut or defer CP10.** It is outside current repo maturity.
- **Make CP9 conditional.** Only start Rust after Python indexed backend and proof ABI are stable.

### Amended plan from Audit A

1. **CP0 ? Observed baseline freeze**
   - Record current deterministic results on smoke/medium/stress.
   - Record current schema drift as known failing contract.
   - Do not treat CP0 as schema-clean baseline.

2. **CP1 ? Contract/schema repair**
   - Repair manifest/corpus/eval wrapper schemas.
   - Add `route_proof.schema.json` and `frontier_packet.schema.json` as draft contracts.
   - Update validator to run JSON Schema plus semantic checks.
   - Add dependency file and automated tests.

3. **CP2 ? Router/expert interface refactor**
   - Split monolithic scoring into named experts/gates.
   - Preserve current 62/62 behavior with golden tests.
   - Emit real `activated_experts`, `expert_claims`, candidate lists, and rejection reasons.

4. **CP3 ? Route proofs and context ABI**
   - Produce schema-valid route proofs for every case.
   - Include selected/rejected/overflowed evidence, conflict pairs, authority chain, answerability, latency, token counts.

5. **CP4 ? Capacity, compactness, taint/exposure**
   - Add token budget policy, overflow policy, taint labels, exposure rules.
   - Enforce compactness metrics and max evidence constraints.
   - Reduce filler/support over-selection.

6. **CP5 ? Baseline runner**
   - Naive BM25/top-k.
   - BM25 + source-family filter.
   - Deterministic MoCE/MoME.
   - Hybrid/local model only as optional capped experiment.
   - Produce quality/latency/token-savings tables.

7. **CP6 ? Robustness/dropout**
   - Expert dropout flags.
   - Metadata ablations: no freshness, no conflict graph, no safety labels.
   - Small mutation set for query paraphrases/anchor perturbations.

8. **CP7 ? Real Ivy mini-dataset**
   - 20?50 sanitized hand-labeled cases.
   - Must use taint/exposure rules from CP4.
   - Keep separate from synthetic benchmark to avoid contaminating deterministic fixtures.

9. **CP8 ? Indexed Python backend**
   - Inverted index / exact-anchor maps behind same expert interface.
   - Re-run proof and baseline golden tests.

10. **CP9 ? Rust prototype, conditional**
   - Only if Python indexed stress latency is insufficient.
   - Must match Python route proofs on golden cases.

11. **CP10 ? Streaming ingestion**
   - Defer/cut from near-term plan.
   - Revisit only after stable schemas, indexes, and real-data governance exist.

---

## Audit B ? Paper/product/evaluation critique

I inspected `C:\ivy\MoME-MoCE-Exp` read-only. No files edited.

### Bottom line

The checkpoint plan is directionally right, but **not paper-ready yet**. It can become defensible if we pivot the center from ?MoE analogy? to:

> **ACCA: an auditable authority-constrained context compiler for agent memory.**

MoCE/MoME should be supporting terminology, not the main novelty claim. The strongest claim is not speed or local-model recall. It is **selected/rejected evidence with provenance, authority, staleness, conflict, safety, and abstention decisions made explicit in a route proof**.

### Critical risks

#### 1. Current 62/62 result is not strong evidence

Current deterministic runs:

- smoke: `62/62`, mean ~`9 ms`
- medium: `62/62`, mean ~`31 ms`
- stress: `62/62`, mean ~`290 ms`

But the pass condition is too permissive.

Example issue:

- mean selected evidence: ~`3.5?3.9`
- mean required evidence: ~`1.1`

So the router often passes by including the required item somewhere in a broad packet. A paper reviewer can fairly call this over-retrieval.

**Fix:** add packet precision, utility/token, max evidence constraints, and over-retrieval penalty.

#### 2. Synthetic overfitting risk is high

The harness has hardcoded phrase boosts and exact synthetic anchors. That is fine for a first harness, but not enough for claims of generality.

Examples found:

- scoring has special cases for `context stress`, `decode_tps`, `ctx 8192`, `private.txt`, etc.
- generated corpus and eval cases are tightly coupled.
- no held-out query family.
- no renamed-ID adversarial split.

**Fix:** add mutation tests and at least one blind holdout set generated separately.

#### 3. Schema/contract drift blocks serious evaluation

Current contract problems:

- `dataset_manifest.schema.json` says schema const `v0.1`, generated manifests emit `v0.2`.
- `corpus_item.schema.json` omits `staleness: "decoy"`, but corpus uses it.
- validator does not enforce JSON Schema.
- smoke corpus has missing/non-normalized `conflicts_with` refs.
- `frontier_packets_smoke.json` uses wrapper dicts, but inner `packet` may be string sentinel like `"NO_CONTEXT_NEEDED"` instead of a stable context ABI.

**Fix:** CP1/CP2 are mandatory before more experiments.

#### 4. Real Ivy dataset is essential

Synthetic-only is not enough for EMNLP Industry. `C:\ivy` has enough real material to build a feasible dataset: logs, benchmark artifacts, runbooks, code, traces.

Minimum real dataset:

- 30?50 hand-labeled Ivy queries.
- Each query has:
  - expected evidence IDs/paths,
  - rejected evidence,
  - freshness/conflict labels,
  - safety/taint labels,
  - answerability label.
- Include at least:
  - 10 code/local facts,
  - 10 benchmark/run facts,
  - 5 stale/conflict cases,
  - 5 safety/private cases,
  - 5 abstain/no-context cases.

Without this, target RAGE-KG/workshop only, not EMNLP Industry.

### Venue fit

#### EMNLP 2026 Industry Track

Good fit **only if** we show real agent workflow value: latency, token savings, stale/decoy reduction, auditable packet output.

Deadline verified from the official call: June 16, 2026 AoE.  
Source: https://2026.emnlp.org/calls/industry_track/

#### RAGE-KG 2026

Better backup if we emphasize the conflict/authority graph and route proofs.

Source: https://2026.rage-kg.org/

#### EMNLP Main / ARR

Too risky unless the empirical result becomes much stronger very quickly.  
Source: https://2026.emnlp.org/calls/main_conference_papers/

### Recommended plan amendments

#### Must add before CP5

1. **Strict schemas**
   - manifest, corpus item, eval case, route proof, frontier packet.
   - CI/test must fail on schema drift.

2. **Route proof first-class artifact**
   - selected evidence,
   - rejected evidence,
   - rejection reasons,
   - expert claims,
   - shared gates,
   - conflict pairs,
   - authority chain,
   - packet tokens,
   - tokens avoided,
   - latency.

3. **Real scoring metrics**
   - evidence recall,
   - evidence precision,
   - forbidden-hit rate,
   - stale-accept rate,
   - decoy-accept rate,
   - abstention accuracy,
   - conflict-pair recall,
   - utility/token,
   - p50/p95 latency.

4. **Baselines**
   - naive BM25 top-k,
   - BM25 + source-family filter,
   - exact-anchor only,
   - local Qwen reranker only,
   - deterministic ACCA,
   - hybrid ACCA + local advisory.

5. **Mutation/dropout suite**
   - stale duplicate,
   - decoy path,
   - wrong source family,
   - missing exact ID,
   - unsafe/private evidence,
   - disabled benchmark expert,
   - disabled conflict graph,
   - disabled safety gate.

### Go/no-go gates

#### Gate 1 ? Engineering validity

Proceed only if:

- route proof and packet schemas validate on every run;
- no mixed packet sentinel strings;
- generated corpus has zero dangling relationship refs;
- deterministic smoke/medium/stress runs reproducible.

#### Gate 2 ? Evaluation validity

Proceed only if:

- ACCA beats BM25/top-k on admissibility, not just recall;
- over-retrieval is penalized;
- mutation tests expose baseline failures;
- expert dropout shows interpretable degradation.

#### Gate 3 ? Paper validity

Submit EMNLP Industry only if by writing freeze we have:

- 30+ real Ivy labeled queries;
- baseline comparison table;
- synthetic + real eval;
- p95 latency/token-savings table;
- route-proof examples;
- clear negative local-LLM result.

If not, pivot to RAGE-KG or an internal technical report.

### Final recommendation

Build next in this order:

1. **CP1 schema repair**
2. **CP2 route proof + context ABI**
3. **CP5 baseline runner**
4. **CP6 mutation/dropout tests**
5. **CP7 real Ivy query set**

Do **not** spend serious time on Rust, GPU local models, or learned routers until those are done. The novelty lives in **auditable admissibility**, not raw retrieval speed.
