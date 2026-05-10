# ACCA / ESCAPE Supercharged Design Notes

Date: 2026-05-10
Project: `C:\ivy\MoME-MoCE-Exp`

## Purpose

This note maps MoE and MoE-adjacent techniques onto the MoCE/MoME architecture and ACCA/ESCAPE implementation plan.

Summary:

> **ACCA is an authority-constrained context compiler over a sparse mixture of external memory experts. ESCAPE is the optional prototype/system branding for implementing ACCA over MoCE/MoME.**

The right combo is not “just BM25” and not “local LLM reranks everything.” The strongest combo is:

```text
MoCE router
  + expert-claim routing
  + context-depth allocation
  + MoME expert pool
  + shared ACCA admissibility gates
  + capacity/overflow policies
  + route proof schema
  + frontier context ABI
  + optional learned/speculative router
```

## Recommended final stack

```text
Architecture: MoCE/MoME
Algorithm:    ACCA, Authority-Constrained Context Assembly
Prototype:    ESCAPE, External Sparse Context And Provenance Experts
```

## Best combined architecture

```text
User query
  -> MoCE Router
     - router scores
     - confidence margin
     - expert claims
     - context depth decision
     - context capacity factor

  -> MoME Expert Pool
     - exact anchors
     - BM25F / WAND / learned sparse retrieval
     - source-code memory
     - benchmark memory
     - runbook memory
     - safety-policy memory
     - debug/workflow trace memory
     - conflict graph memory

  -> Shared ACCA Gates
     - authority gate
     - freshness/supersession gate
     - safety/privacy/taint gate
     - provenance gate
     - answerability gate
     - exposure-budget gate

  -> Packet Compiler
     - utility/token packing
     - overflow policy
     - authority chain compression
     - evidence quorum check

  -> Route Proof
     - router scores
     - activated experts
     - expert claims
     - selected evidence
     - rejected evidence
     - overflowed evidence
     - conflict pairs
     - authority chain
     - answerability
     - context depth
     - latency/tokens saved

  -> Frontier Context ABI
     - compact admissible packet
     - synthesis instructions
```

## Concept fit map

### 1. Context Capacity Factor

Borrowed from MoE expert capacity. In external context routing:

```text
context_capacity_factor = allowed_context_tokens / expected_required_evidence_tokens
```

Why it fits:

- makes context overload measurable;
- explains why evidence is packed, summarized, dropped, or deferred;
- maps directly to MoE capacity-factor thinking.

Route proof fields:

```json
{
  "frontier_context_budget": 6000,
  "mandatory_evidence_tokens": 1800,
  "optional_evidence_tokens": 1200,
  "context_capacity_factor": 1.67
}
```

Implementation priority: **high**.

### 2. Expert Overflow Policies

MoE overflow maps to context overflow.

ACCA policies:

| Overflow case | Policy |
|---|---|
| too many benchmark records | keep latest authoritative; reject stale |
| too many source files | keep exact-anchor files first |
| too many conflicts | include mandatory conflict pair; defer extra neighbors |
| unsafe/private evidence | reject or local-only exposure |
| too much relevant evidence | utility/token packing or summarization |
| no admissible evidence | abstain |

Route proof field:

```json
{
  "overflow_policy": "mandatory_first_then_utility_per_token",
  "overflowed_evidence": [
    {"id": "bench_old", "reason": "capacity_overflow_lower_authority"}
  ]
}
```

Implementation priority: **high**.

### 3. Router Confidence Margin

MoE routers choose top-k experts by score. ACCA should expose:

```text
router_margin = score(top_1_expert) - score(top_2_expert)
```

Policy:

| Margin | Action |
|---|---|
| high | top-1 expert |
| medium | top-2 experts |
| low | add conflict/debug/general expert |
| confused | abstain or clarify |

Route proof field:

```json
{
  "router_scores": {"benchmark_memory": 0.91, "runbook_memory": 0.38},
  "router_margin": 0.53,
  "routing_confidence": "high"
}
```

Implementation priority: **high**.

### 4. Anti-Routing-Collapse / Load Balancing

Neural MoEs can collapse into overusing a few experts. External memory systems can collapse too:

```text
everything -> BM25
everything -> vector search
everything -> frontier model
```

Metrics:

```json
{
  "expert_activation_histogram": {
    "exact_anchor": 412,
    "bm25": 821,
    "source_code": 104,
    "conflict_graph": 77,
    "safety_gate": 52
  },
  "expert_entropy": 1.82,
  "dominant_expert_ratio": 0.56
}
```

Use this to prove MoCE/MoME is not fake MoE.

Implementation priority: **medium-high**.

### 5. Shared Experts vs Routed Experts

Central taxonomy.

Shared experts, always on:

- authority gate;
- provenance gate;
- safety/privacy gate;
- freshness gate;
- answerability gate;
- packet budget gate.

Routed experts, activated sparsely:

- exact-anchor memory;
- BM25F memory;
- source-code memory;
- benchmark memory;
- runbook memory;
- debug trace memory;
- workflow memory;
- conflict graph memory.

Paper sentence:

> Unlike standard retrieval routers, ACCA separates always-on shared admissibility experts from sparsely activated memory experts.

Implementation priority: **high**.

### 6. Expert Choice Routing

Normal MoE: tokens choose experts.
Expert Choice MoE: experts can claim tokens.

External version:

```text
queries choose experts, but experts can also claim queries when trigger anchors fire.
```

Examples:

| Expert | Claim trigger |
|---|---|
| safety | private path, secret, token, API key |
| benchmark | TPS, ctx, latency, profile.json |
| source-code | function/module/path name |
| conflict | latest, current, old, changed, superseded |
| runbook | command, setup, install, reproduce |

Route proof field:

```json
{
  "expert_claims": [
    {"expert": "benchmark_memory", "claim_strength": 0.94, "trigger": "ctx=32768 decode_tps"},
    {"expert": "freshness_gate", "claim_strength": 0.88, "trigger": "latest"}
  ]
}
```

Implementation priority: **very high**. This fits coding-agent memory extremely well.

### 7. Mixture of Depths for Context Work

Not every query deserves the same retrieval depth.

Context-depth levels:

| Depth | Behavior |
|---:|---|
| 0 | no retrieval |
| 1 | exact anchor only |
| 2 | exact anchor + BM25 |
| 3 | source family + freshness gates |
| 4 | conflict graph expansion |
| 5 | local advisory classifier/reranker |
| 6 | frontier clarification or abstention |

Route proof field:

```json
{
  "context_depth": 4,
  "depth_reason": "query asks for latest result and matching stale record exists",
  "activated_stages": ["exact_anchor", "benchmark_memory", "freshness_gate", "conflict_graph"]
}
```

Implementation priority: **very high**.

### 8. Residual / No-Context Path

MoE has a residual stream. MoCE/MoME should preserve the frontier model’s no-context path.

Route proof examples:

```json
{
  "answerability": "no_context_needed",
  "frontier_packet": null,
  "residual_path": "frontier_model_general_reasoning"
}
```

or:

```json
{
  "answerability": "unanswerable_with_available_context",
  "residual_path": "abstain"
}
```

Implementation priority: **high**.

### 9. Expert Dropout / Missing-Expert Robustness

Evaluate degradation by disabling experts:

- benchmark memory disabled;
- exact-anchor disabled;
- conflict graph disabled;
- freshness metadata disabled;
- safety metadata disabled.

Metrics:

```json
{
  "expert_dropout": "benchmark_memory_disabled",
  "answerability_accuracy_delta": -0.18,
  "stale_rejection_delta": -0.31,
  "latency_delta_ms": -42
}
```

Implementation priority: **medium** for paper evaluation.

### 10. Admissibility Loss / Routing Loss

Define an offline routing objective:

```text
ACCA_loss =
  5.0 * unsafe_accept
+ 4.0 * decoy_accept
+ 3.0 * stale_accept
+ 2.0 * conflict_miss
+ 1.0 * evidence_miss
+ 0.1 * token_overrun
+ 0.05 * latency_ms
```

Use it to train/distill a learned route classifier from deterministic oracle traces.

Implementation priority: **medium-high**.

### 11. Authority-Weighted Routing Logits

Candidate scores should not be raw relevance.

```text
score = relevance
      + authority
      + freshness
      + exactness
      + provenance
      - stale
      - decoy
      - unsafe
      - unresolved_conflict
```

Route proof field:

```json
{
  "candidate": "bench_run_old.json",
  "raw_relevance": 0.92,
  "authority_adjusted_score": 0.21,
  "penalties": {"stale": -0.45, "superseded": -0.20}
}
```

Implementation priority: **high**.

### 12. Expert Locality / Memory Placement

MoE systems care where experts live. ACCA/ESCAPE should track memory placement.

| Expert | Placement |
|---|---|
| exact anchors | in-process hash maps |
| BM25F | local Tantivy/SQLite index |
| source code | repo-local index |
| benchmark memory | append-only JSONL/SQLite |
| safety policy | immutable local file |
| long-term notes | external DB |
| heavy semantic search | optional remote/vector service |

Route proof field:

```json
{
  "expert": "exact_anchor",
  "placement": "in_process",
  "p50_latency_ms": 0.3,
  "p95_latency_ms": 1.1
}
```

Implementation priority: **medium-high**, especially for Rust/Tantivy plan.

### 13. All-to-All Cost Analogy

Distributed MoEs pay dispatch/communication cost. External experts pay coordination cost.

Track:

```json
{
  "coordination_cost": {
    "experts_called": 4,
    "disk_reads": 12,
    "index_queries": 3,
    "graph_expansions": 2,
    "serialization_bytes": 8421
  }
}
```

Implementation priority: **medium**.

### 14. Speculative Context Routing

Map speculative decoding to context routing:

```text
draft router proposes evidence
ACCA verifier rejects/accepts
frontier model synthesizes
```

Modes:

| Mode | Draft | Verifier |
|---|---|---|
| deterministic | exact anchors/BM25 | ACCA gates |
| learned | tiny classifier | ACCA gates |
| hybrid | local Qwen advisory | ACCA gates |
| expensive | frontier self-query | ACCA + human-visible proof |

Paper sentence:

> We use small models only as speculative evidence proposers; admissibility remains deterministic and auditable.

Implementation priority: **high** for framing, medium for implementation.

### 15. Conflict Graph as Expert Memory

Do not treat conflicts as postprocessing. Make `conflict_graph_expert` a real MoME expert.

Edges:

- `supersedes`;
- `conflicts_with`;
- `derived_from`;
- `invalidates`;
- `same_benchmark_family`;
- `older_than`;
- `authority_overrides`;
- `private_version_of`.

Route proof field:

```json
{
  "conflict_pairs": [
    {"current": "run_2026_05_10_q8kv", "stale": "run_2026_04_27_q4kv", "edge": "supersedes"}
  ]
}
```

Implementation priority: **very high**.

### 16. Taint Tracking for Context

Treat context as tainted evidence before exposure to the frontier model.

Taint labels:

- private;
- stale;
- synthetic;
- unverified;
- user_provided;
- generated_by_agent;
- benchmark_artifact;
- secret_like.

Rules:

```text
private -> local-only unless allowed
secret -> never expose
synthetic -> cannot support real-world claim alone
stale -> only historical/conflict use
generated_by_agent -> lower authority than raw log
```

Implementation priority: **high** for systems/paper novelty.

### 17. Memory TTL and Supersession Semantics

Add explicit validity policy:

```json
{
  "ttl_policy": {
    "benchmark_result": "valid_until_superseded",
    "install_command": "valid_for_90_days",
    "path": "valid_until_missing",
    "policy": "valid_until_replaced"
  }
}
```

Implementation priority: **high** because stale memory is core.

### 18. Context ABI / Packet Interface

Define stable interface between MoCE and frontier model:

```json
{
  "packet_version": "acca.packet.v1",
  "task": "...",
  "answerability": "...",
  "selected_evidence": [],
  "rejected_evidence_summary": [],
  "constraints": [],
  "instructions_to_frontier": []
}
```

Implementation priority: **very high**.

### 19. Route Proof Schema as First-Class Artifact

Minimum schema sections:

```json
{
  "query_id": "...",
  "router_scores": {},
  "activated_experts": [],
  "shared_experts": [],
  "expert_claims": [],
  "selected_evidence": [],
  "rejected_evidence": [],
  "overflowed_evidence": [],
  "conflict_pairs": [],
  "authority_chain": [],
  "answerability": "...",
  "context_depth": 0,
  "frontier_packet_tokens": 0,
  "tokens_avoided": 0,
  "latency_ms": 0
}
```

Implementation priority: **very high**.

### 20. Dynamic Pruning: WAND / Block-Max WAND

WAND/BMW are internal MoME retrieval-engine optimizations, not novelty by themselves.

Use to support latency-bounded expert activation.

Implementation priority: **medium** now, **high** for Rust scaling.

### 21. Learned Sparse Retrieval Expert

SPLADE-style learned sparse retrieval can be an optional MoME expert:

```text
learned_sparse_expert(query) -> high-recall lexical-semantic candidates
```

ACCA still verifies admissibility.

Implementation priority: **future**.

### 22. Late Interaction Expert

ColBERT-style late interaction can be a semantic recall expert.

Use as:

```text
semantic_recall_expert(query) -> candidates
```

Not authority.

Implementation priority: **future**.

### 23. Cascaded Routing / Frugal Routing

Use a stage cascade with early exits:

```text
Stage 0: no-context classifier
Stage 1: exact anchors
Stage 2: BM25F
Stage 3: source-family filter
Stage 4: conflict graph
Stage 5: learned sparse / dense recall
Stage 6: local advisory model
Stage 7: frontier clarification
```

Route proof field:

```json
{"stage": "exact_anchor", "exit_reason": "sufficient_authoritative_evidence"}
```

Implementation priority: **very high**.

### 24. Authority Chain Compression

Pack the authority chain rather than all supporting evidence.

Example:

```json
{
  "claim": "q8_0 KV is current recommended setting",
  "authority_chain": ["latest_benchmark_run", "supersedes_old_q4_run", "manual_acceptance_note"]
}
```

Implementation priority: **medium-high**.

### 25. Mutation Testing for Memory Systems

Generate controlled corruptions:

| Mutation | Expected behavior |
|---|---|
| stale duplicate | reject stale |
| decoy path | reject decoy |
| wrong source family | reject wrong family |
| conflicting benchmark | include conflict pair |
| private secret | reject unsafe |
| missing exact ID | abstain |
| synthetic-only evidence | lower confidence |

Metric:

```text
admissibility_robustness = passed_mutations / total_mutations
```

Implementation priority: **high** for paper evaluation.

### 26. Memory Write Barrier

Agent memory writes should not become authoritative immediately.

States:

```text
proposed -> observed -> validated -> superseded -> archived
```

Rule:

```text
agent-generated memory cannot support high-authority answers until validated
```

Implementation priority: **medium-high** for real agent integration.

### 27. Evidence Quorum

High-risk claims require multiple evidence types.

| Claim type | Quorum |
|---|---|
| benchmark recommendation | benchmark artifact + acceptance note |
| setup command | runbook + successful trace |
| safety/private claim | policy + path classifier |
| current status | latest timestamp + not superseded |

Route proof field:

```json
{
  "quorum_policy": "benchmark_recommendation_v1",
  "required": ["benchmark_artifact", "acceptance_note"],
  "satisfied": true
}
```

Implementation priority: **medium-high**.

### 28. Abstention as a Routing Outcome

Abstention is a valid route, not failure.

```json
{
  "answerability": "abstain_missing_exact_identifier",
  "reason": "query references run_id not present in exact-anchor index"
}
```

Implementation priority: **high**.

### 29. Evidence Utility per Token

Define:

```text
utility_per_token = admissibility_score / packed_token_count
```

Use for packet packing and overflow.

Implementation priority: **medium-high**.

### 30. Frontier Exposure Budget

Not all admissible evidence should be exposed to a remote frontier model.

```json
{
  "exposure_policy": {
    "private": "local_only",
    "secret": "never_expose",
    "benchmark": "expose_summary",
    "source_code": "expose_snippet",
    "policy": "expose_exact"
  }
}
```

Implementation priority: **high**, especially for coding agents.

## Best combo to build first

Do not build all 30 independently. Build this minimal supercharged core:

```text
1. Shared vs routed experts
2. Expert Choice claims
3. Context depth levels
4. Capacity factor and overflow policy
5. Authority-weighted routing logits
6. Conflict graph expert
7. Taint/exposure policy
8. Context ABI
9. Route proof schema
10. Cascaded routing with early exits
```

This gives the strongest paper/system gain with the least implementation sprawl.

## ACCA v2 algorithm sketch

```python
def acca_route(query, task_state):
    route = moce_router.score(query, task_state)
    claims = collect_expert_claims(query)
    depth = choose_context_depth(route, claims)
    capacity = assign_context_capacity(query, depth)

    candidates = []
    for expert in activate_experts(route, claims, depth):
        candidates += expert.retrieve(query, capacity.for_expert(expert))

    if needs_conflict_resolution(query, candidates):
        candidates += conflict_graph.expand(candidates)

    selected, rejected = shared_gates.filter(
        candidates,
        authority=True,
        freshness=True,
        safety=True,
        taint=True,
        exposure=True,
    )

    quorum = check_evidence_quorum(query, selected)
    answerability = classify_answerability(query, selected, rejected, quorum)

    packet = pack_context(
        selected,
        budget=capacity.frontier_tokens,
        policy="mandatory_first_then_utility_per_token",
    )

    return route_proof(
        route=route,
        claims=claims,
        depth=depth,
        capacity=capacity,
        selected=packet.selected,
        rejected=rejected,
        overflowed=packet.overflowed,
        conflict_pairs=extract_conflicts(candidates),
        authority_chain=compress_authority_chain(packet.selected),
        answerability=answerability,
        context_abi=build_frontier_packet(packet),
    )
```

## Best paper framing after this upgrade

> **ACCA is an authority-constrained context compiler over a sparse mixture of external memory experts. It adapts MoE concepts such as top-k routing, expert choice, shared experts, capacity factors, overflow handling, routing confidence, expert dropout, load-balancing diagnostics, and adaptive depth to the problem of frontier-agent context assembly.**

This is significantly stronger than “RAG router.”

## Resource links

### MoE concepts

- Aman AI MoE primer: https://aman.ai/primers/ai/mixture-of-experts/
- Hugging Face MoE explainer: https://huggingface.co/blog/moe
- Sparsely-Gated MoE: https://arxiv.org/abs/1701.06538
- Comprehensive MoE survey: https://arxiv.org/html/2503.07137v4
- Mixture of Experts in LLMs survey: https://arxiv.org/html/2507.11181v2
- Expert Choice Routing: https://papers.neurips.cc/paper_files/paper/2022/file/2f00ecd787b432c1d36f3de9800728eb-Paper-Conference.pdf
- Mixture of Depths: https://arxiv.org/abs/2404.02258
- GShard: https://arxiv.org/abs/2006.16668
- Distributed MoE / expert parallelism: https://brunomaga.github.io/Mixture-of-Experts

### Retrieval / pruning / sparse recall

- Block-Max WAND / BMW paper copy: https://user.ceng.metu.edu.tr/~isikligil/ceng334/HW3/outputs/recover1/bmw.pdf
- Faster Learned Sparse Retrieval with Block-Max Pruning: https://arxiv.org/pdf/2405.01117
- SPLADE: https://arxiv.org/abs/2107.05720
- ColBERT: https://arxiv.org/abs/2004.12832

### Adaptive RAG / routing adjacent

- Adaptive-RAG: https://arxiv.org/abs/2403.14403
- Self-RAG: https://arxiv.org/abs/2310.11511
- FrugalGPT: https://arxiv.org/abs/2305.05176
