# CP0 Observed Baseline Freeze

Date: 2026-05-10

This is the CP0 baseline for `C:\ivy\MoME-MoCE-Exp` before CP1 contract repair and CP2 router/expert refactor. It records the observed behavior, including known contract failures. This baseline is useful for regression comparison, but it is not schema-clean evidence.

## Dataset State

Generated datasets use seed `123`.

| Scale | Items | Estimated Tokens | Eval Cases |
|---|---:|---:|---:|
| smoke | 349 | 50,135 | 62 |
| medium | 1,086 | 200,150 | 62 |
| stress | 9,992 | 2,000,216 | 62 |

Eval case distribution:

| Category | Cases |
|---|---:|
| adversarial_decoy | 5 |
| benchmark | 8 |
| debug | 6 |
| exact_command | 6 |
| general | 7 |
| local_codebase | 8 |
| safety | 6 |
| stale_conflict | 4 |
| unanswerable | 6 |
| workflow | 6 |

## Harness Baseline

| Run | Passed | Quality | Mean Latency | P50 Latency | Max Latency | Avg Selected | Avg Required | Required-Only Precision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| smoke deterministic | 62/62 | 1.0 | 9.215 ms | 9.041 ms | 16.132 ms | 3.532 | 1.113 | 0.315 |
| medium deterministic | 62/62 | 1.0 | 30.731 ms | 29.797 ms | 54.662 ms | 3.871 | 1.113 | 0.287 |
| stress deterministic | 62/62 | 1.0 | 290.364 ms | 278.822 ms | 529.165 ms | 3.758 | 1.113 | 0.296 |
| smoke hybrid ambiguous | 62/62 | 1.0 | 587.255 ms | 9.337 ms | 35,809.841 ms | 3.532 | 1.113 | 0.315 |
| smoke hybrid advisory | 62/62 | 1.0 | 6,359.183 ms | 12.043 ms | 37,977.026 ms | 3.532 | 1.113 | 0.315 |
| smoke hybrid force-local limit 8 | 8/8 | 1.0 | 21,205.468 ms | 30,583.496 ms | 37,259.718 ms | 2.625 | 0.625 | 0.238 |

Interpretation:

- The deterministic router preserves required-evidence recall on the 62 seeded cases.
- The pass condition is too forgiving for ACCA claims because it mostly checks whether required IDs appear somewhere.
- Over-retrieval is visible: most non-general/non-abstain categories select up to 5 items even when only 1-2 are required.
- Local Qwen GGUF routing is too slow for hot-path use and should remain optional/advisory.

## Known Failing Contract

The CP0 state is intentionally recorded as not schema-clean:

- The manifest schema requires `context_stress_manifest.v0.1`, while generated manifests emit `context_stress_manifest.v0.2`.
- Generated manifests contain fields not represented by the schema: `authority_counts`, `staleness_counts`, `template_stats`, `file_sha256`, `generator`, and `token_target_met`.
- The corpus schema does not allow `staleness: "decoy"`, while generated corpora use it.
- The corpus schema forbids provenance fields used by generated support records: `generated_from`, `seed`, and `support_index`.
- Eval output is a wrapper object with `{schema_version, cases}`, but the existing schema describes a single case object.
- The custom validator passes smoke, medium, and stress despite the formal schema drift.
- Relationship integrity is incomplete: generated corpora contain dangling `conflicts_with` references.
- Frontier packets use mixed representations: structured packets for answerable cases and string sentinels such as `NO_CONTEXT_NEEDED` / `SEARCHED_NO_AUTHORITATIVE_EVIDENCE` for non-answerable paths.

## CP0 Acceptance

CP0 is complete when the current behavior is documented as an observed baseline and later CP1/CP2 changes can compare against:

- deterministic 62/62 recall behavior;
- latency range by scale;
- evidence compactness gap;
- schema drift as a known failing contract.

