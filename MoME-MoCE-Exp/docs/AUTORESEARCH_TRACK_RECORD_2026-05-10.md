# Autoresearch Track Record

Date: 2026-05-10

## Completed This Pass

1. CP9.1 direct Rust backend is now wired into `scripts/mome_moce_harness.py` behind `--candidate-backend rust`.
2. Rust backend now supports batch preloading through the existing Rust `--cases` mode, so benchmark runs call Rust once per dataset instead of shelling out per query.
3. Ivy-real v2 was generated at `out/context_stress_ivy_real_v2` with 45 evidence items and 119 cases across all 10 categories.
4. Taint/exposure metadata is now first-class in corpus loading, route proofs, and frontier packets.
5. The first gate/packet split exists in `scripts/routing_components.py`: `TaintExposureGate` and `PacketCompiler`.
6. Added backend parity and model-facing demo scripts:
   - `scripts/run_candidate_backend_comparison.py`
   - `scripts/run_model_facing_demo.py`

## Verification Results

| Run | Result |
|---|---:|
| Ivy-real v2 indexed | 119/119, precision 1.0, forbidden hits 0, artifact errors 0 |
| Ivy-real v2 Rust | 119/119, precision 1.0, forbidden hits 0, artifact errors 0 |
| Stress Rust | 62/62, precision 1.0, forbidden hits 0, artifact errors 0 |
| Model-facing demo | ACCA passed 8/8, ACCA forbidden hits 0 |
| V2 naive BM25 top-5 | 1/119, precision 0.2376, forbidden hits 12 |
| V2 ACCA compact | 119/119, precision 1.0, forbidden hits 0 |
| Python tests | 13 passed |
| Rust tests | cargo test ok |

Rust timing after batch preload:

| Dataset | Preload | Route Mean | Route P50 | Route Max |
|---|---:|---:|---:|---:|
| Ivy-real v2 Rust | 59.793 ms | 0.953 ms | 0.977 ms | 1.984 ms |
| Stress Rust | 4483.781 ms | 1.694 ms | 1.859 ms | 3.744 ms |

Candidate comparison:

| Dataset | Indexed Quality | Rust Quality | Rust Selected Match | Candidate Jaccard |
|---|---:|---:|---:|---:|
| Ivy-real | 1.0 | 1.0 | 1.0 | 0.800216 |
| Ivy-real v2 | 1.0 | 1.0 | 1.0 | 0.635078 |
| Stress | 1.0 | 1.0 | 1.0 | 0.208443 |

Interpretation: Rust is now functionally equivalent at selected-evidence level, but its raw candidate set still diverges from Python indexed. That is acceptable for proof quality right now because Python remains final scoring/gating authority, but it is the next Rust parity problem.

## Autoresearch Notes

The strongest framing is not "memory improves retrieval." The more defensible novelty is:

> ACCA is an auditable, authority-constrained context compiler that can route, gate, compact, prove, and expose only admissible context to a frontier model.

The useful technical pieces now visible in artifacts:

- compact packet ABI instead of raw retrieval stuffing;
- selected/rejected/overflowed evidence with route proofs;
- explicit authority, freshness, safety, provenance, answerability, and budget gates;
- taint/exposure policy surviving into the packet ABI;
- Rust candidate generation without changing the Python proof authority;
- model-facing demo showing why naive BM25 recall is not enough when precision and forbidden evidence matter.

## Sidecar Research Summaries

GPT-5.4 medium architecture/QoL sidecar:

- Main issue is not "make Rust exist"; it is "make Rust cheap to call."
- Recommended persistent or batch Rust process, release binary, and loaded-once index lifecycle.
- Recommended explicit parity reporting because Python and Rust tokenization/scoring are not identical.
- Recommended extracting candidate backends, experts, gates, and packet compiler while preserving proof/packet ABI.

GPT-5.5 low pivot sidecar:

- Best near-term product framing: Agent Memory Safety Evaluator plus Context Compiler Middleware.
- Strong pivots include RAG governance/evidence audit, context-stress benchmark suite, regulated policy-gated memory, and failure-mode observability.
- Biggest weakness remains real-case breadth; Ivy-real v2 improves this but should still be expanded with sanitized real logs and failures.

## Next Optimization Points

1. Improve Rust/Python candidate parity:
   - port Python tokenizer/search text more closely to Rust;
   - add family-aware candidate expansion in Rust;
   - track Jaccard separately from selected-evidence parity.
2. Make Rust a persistent service or library call:
   - batch preload fixed benchmark cases is good enough for harnesses;
   - interactive arbitrary queries still fall back to per-query process spawn.
3. Expand Ivy-real v3 from sanitized fixtures:
   - real failed runs;
   - stale docs;
   - Signal/Litter operational incidents;
   - IVY memory-injection outputs;
   - router false positives.
4. Add answer-level model checks:
   - use frontier packet only;
   - require citations from selected evidence IDs;
   - assert abstention on no-authoritative-evidence cases.
5. Add an observability report:
   - per-case gate decisions;
   - taint/exposure counts;
   - candidate drift;
   - token savings;
   - failure taxonomy.
