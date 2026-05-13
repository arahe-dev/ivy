# LLM Mental Model Truths for D-ACCA

Date: 2026-05-12

This note captures the LLM and inference architecture ideas that appear worth applying to D-ACCA/DD-ACCA, plus the ideas that should be treated carefully. The goal is not to imitate LLM internals for their own sake. The useful transfer is the latency-quality systems pattern: spend almost no compute on obvious cases, spend adaptive compute on ambiguity, and distill repeated wins back into the deterministic engine.

## The Core Test

An LLM mental model is worth implementing in D-ACCA only if it satisfies most of these:

1. It improves precision, freshness correctness, contradiction handling, or no-context correctness.
2. It keeps normal-case p95 latency under roughly 5 ms.
3. It can be tested with black-box packets.
4. It can be distilled into deterministic behavior over time.
5. It does not require calling an LLM on every request.

If an idea fails these checks, it may still be useful offline, but it should not become part of the default runtime path.

## Highest Priority Patterns

### Early Exit / Adaptive Compute

Easy cases should resolve immediately. The engine should return one of three outcomes:

- `accept`: context is relevant, current, and safe enough to admit.
- `no_context`: the model should answer without injected memory.
- `escalate_librarian`: ambiguity is high enough to justify a smarter sidecar.

This is probably the most important runtime pattern. It preserves the sub-ms/sub-5ms philosophy while giving hard cases a path upward.

### Confidence Gating

The system needs a deterministic confidence gate that decides when the librarian wakes up. Candidate features:

- Top candidate score.
- Margin between first and second candidate.
- Fresh vs stale evidence conflict.
- Current evidence present but weakly matched.
- Forbidden/stale hit count.
- Alias strength.
- Query-to-evidence lexical gap.
- Contradiction count.
- No-context likelihood.

The gate is more important than the librarian itself. A good librarian called too often becomes latency bloat. A good librarian called too rarely misses the hard cases.

### Cascade Inference

D-ACCA should behave like a cheap-to-expensive cascade:

```text
no-context detector
  -> deterministic D-ACCA
  -> DD-rule
  -> helper-lazy
  -> DeepSeek/librarian
  -> frontier model only for rare cases
```

Each stage should only run if the previous stage cannot produce a confident decision. This matches the target tradeoff: 9/10 correct in under 5 ms is often more valuable than 10/10 correct in 10 seconds.

### Contrastive Evidence

The engine should ask:

```text
What evidence proves this answer instead of the nearest wrong answer?
```

This is especially important for stale, contradictory, and decoy records. The system should explicitly compare:

- Current vs stale.
- Allowed vs forbidden.
- Exact entity vs nearby entity.
- Strong evidence vs vague mention.
- Project-specific answer vs generic answer.

This is one of the strongest ways to improve real precision instead of merely improving retrieval hit rate.

### Distillation Loop

The librarian should not be a permanent tax on every request. It should solve hard cases, then teach the deterministic engine.

```text
hard query
  -> librarian rewrite / judgment
  -> verified context decision
  -> extract alias/rule/test case
  -> future similar case handled deterministically
```

Every librarian intervention should produce a durable artifact:

- New alias.
- New negative constraint.
- New freshness rule.
- New contradiction pattern.
- New black-box test case.
- New confidence-gate threshold adjustment.

This is how adaptive intelligence becomes engine improvement.

## Worth Building Soon

### Context Packet Pruning

After admission, the engine should return the smallest useful packet, not the largest matching memory blob. This improves final model answer quality and reduces prompt bloat.

Useful packet fields:

- Minimal evidence span.
- Source id/path.
- Freshness marker.
- Confidence reason.
- Contradiction/staleness notes.
- Why it was admitted.

### Prefix/KV-Style Cache

Stable user/project/agent state should stay pre-indexed and reusable. Only the new query delta should be routed. This aligns directly with IVY hot-session cache work.

Practical translation:

- Keep stable corpus indexes warm.
- Keep entity/alias maps loaded.
- Cache no-context patterns.
- Cache recent route decisions.
- Avoid recomputing static project memory structure.

### Speculative Execution

While the main agent is working, a sidecar can precompute likely next context needs. This should be background-only and should never block the fast path.

Useful examples:

- The agent reads a file, so prefetch nearby project docs.
- The user discusses Signal/Tailscale, so prewarm phone-bridge context.
- A stale/current conflict appears, so prepare a contrastive packet.

## Maybe Later

### Beam Search Over Context Packets

This may help when there are multiple plausible interpretations, but it risks complexity and latency. It should come after confidence gating and contrastive evidence.

Useful only if the engine can cheaply generate a small set of candidate packets:

- Project-doc packet.
- Recent-chat packet.
- Code-evidence packet.
- No-context packet.

Then a verifier can choose. This should not become a default broad search over everything.

### Model Verifier

A verifier model could improve quality, but only if lazy-gated. Running a model verifier on every request defeats the point of D-ACCA.

Good uses:

- Contradictory evidence.
- High-value answer.
- Low confidence but high recall.
- Unseen phrasing.

Bad use:

- Every query.
- Obvious exact matches.
- Obvious no-context prompts.

### Attention-Style Scoring

This may be useful if grounded in explicit features such as entities, dates, files, task state, and source authority. It should not become vague "semantic importance" scoring without testable behavior.

### Quantization Tiers

The practical version is not literal numeric quantization. It means maintaining cheap and rich feature tiers:

- Cheap tier: entity ids, aliases, source type, recency, exact anchors.
- Rich tier: summaries, contradiction notes, learned rewrite hints, evidence spans.

Use cheap tiers for fast routing. Use rich tiers only when needed.

### Continuous Batching

Useful for background indexing and maintenance, less important for immediate query latency.

Good background jobs:

- Summarize new conversations.
- Detect contradictions.
- Generate aliases.
- Produce black-box cases from failures.
- Update freshness/authority metadata.

## Not Worth Building Yet

### Rejection Sampling

Generating multiple packets and rejecting bad ones is too expensive for the default runtime. It may be useful offline for dataset generation or report-quality analysis.

### Full Beam Search Everywhere

Most requests should resolve to one of:

- No context.
- One strong packet.
- Escalate librarian.

Full beam search on every request is overkill.

### LLM Verifier on Every Call

This kills the latency thesis. The model should be called only when deterministic confidence says the case is genuinely ambiguous or high risk.

### Heavy Learned Router Immediately

Do not replace the deterministic router before the confidence features and failure corpus are mature. First collect hard cases, librarian interventions, and black-box failures. Then train or tune from real pressure.

## Current Best Architecture Hypothesis

```text
D-ACCA Engine
  -> fast deterministic route
  -> confidence gate
    -> accept immediately
    -> no-context immediately
    -> lazy librarian for uncertainty
      -> contrastive verification
      -> context packet pruning
      -> distill lesson into rules, aliases, and tests
```

The key product thesis is:

```text
Spend almost no compute on obvious context.
Spend adaptive compute only on ambiguity.
Turn solved ambiguity into faster future deterministic behavior.
```

## Next Build Candidates

1. Confidence Gate v1.
2. Contrastive Evidence Layer.
3. Lazy DeepSeek Librarian Runtime.
4. Distillation Log.
5. Context Packet Pruner.
6. Metadata ablation test for helper-lazy.
7. Held-out alias test.
8. Real conversation replay packet.

The next serious proof should not be another synthetic best-case run. It should test whether the system survives missing metadata, unseen aliases, and real conversation phrasing.
