# MoCE / MoME Research Notes

Date: 2026-05-10
Project: `C:\ivy\MoME-MoCE-Exp`

## Executive summary

The strongest framing is not “fast RAG” or “small model retrieves for a big model.” The strongest framing is:

> **MoCE/MoME is an MoE-style sparse routing architecture over external context and memory experts for frontier-model agents.**

A neural MoE saves compute by activating only the relevant parameter experts. MoCE/MoME saves context, latency, and failure risk by activating only the relevant external memory/context experts, then compiling a compact admissible packet for the frontier model.

The current implementation already demonstrated:

- deterministic routing over a synthetic ~2M-token corpus;
- 62/62 expected evidence cases on smoke/medium/stress after iteration;
- stress mean latency around 0.29s in Python;
- local Qwen3-4B Q4_K_M GGUF loads, but CPU generative reranking is too slow and unsafe as an authority mechanism;
- correct role for small/local models is advisory routing/classification, not truth authority.

## Core definitions

### MoCE: Mixture of Context Experts

MoCE is the context router/compiler. It decides:

- whether the query needs external context;
- which context/memory experts should activate;
- how much latency and token budget each expert gets;
- whether stale, decoy, conflicting, unsafe, or unsupported evidence is admissible;
- whether the system should answer, abstain, reject a decoy, or resolve a conflict;
- what compact proof/context packet the frontier model receives.

MoCE is analogous to the MoE router/gate, but it routes task/query state to external context experts rather than tokens to neural FFN experts.

### MoME: Mixture of Memory Experts

MoME is the external memory expert pool. It proposes candidate evidence through specialized retrieval systems:

- exact-anchor memory: commands, paths, filenames, function names, dates, ctx values;
- sparse lexical memory: BM25/BM25F/inverted index;
- source-code memory;
- runbook memory;
- benchmark memory;
- safety-policy memory;
- workflow-trace memory;
- debug/failure memory;
- conflict graph memory;
- optional learned route classifier or local reranker.

MoME proposes. MoCE disposes.

## MoE mapping

| Neural MoE concept | MoCE/MoME equivalent |
|---|---|
| Token representation | User query + task state |
| Router logits | MoCE expert scores |
| Top-k expert activation | Activated memory/context experts |
| Expert FFNs | External memory experts |
| Shared expert | Always-on authority/provenance/safety gates |
| Capacity factor | Token budget + latency budget + max evidence items |
| Load balancing | Avoid overusing slow/general experts; encourage specialized experts |
| Expert output combine | Evidence packet packing |
| Residual stream | Frontier model context window |
| Auxiliary routing loss | Route correctness + stale/decoy avoidance + latency loss |
| Expert dropout/failure | Missing, stale, poisoned, untrusted, or conflicting memory |

## Architecture target

```text
User query
  -> MoCE context gate
     - no context?
     - exact local evidence needed?
     - safety/policy involved?
     - stale/decoy/conflict likely?
     - latency/token budget?
  -> MoME expert activation
     - exact anchors
     - BM25F/inverted index
     - source-family experts
     - conflict graph expansion
     - optional local/learned router
  -> MoCE admissibility compiler
     - reject stale unless conflict/staleness query
     - reject decoy unless decoy-rejection query
     - enforce safety hierarchy
     - detect unanswerable exact identifiers
     - build authority chain
  -> Route proof
     - router scores
     - activated experts
     - selected evidence
     - rejected evidence
     - rejection reasons
     - conflict pairs
     - answerability
     - latency and token savings
  -> Compact frontier context packet
  -> Frontier model final synthesis
```

## Why this is better than ordinary RAG

Ordinary RAG generally optimizes semantic or lexical similarity:

```text
query -> retrieve similar chunks -> answer
```

MoCE/MoME should optimize admissible answerability:

```text
query -> activate sparse external experts -> retrieve candidate evidence -> compile only admissible context -> answer or abstain
```

The novelty should be in context admissibility, not raw retrieval speed.

Key claim:

> **Relevance is not enough for agent memory. Agent context must be authority-aware, freshness-aware, conflict-aware, safety-aware, abstention-aware, latency-bounded, and auditable.**

## Current implementation findings

### Deterministic router

Current Python harness results after iteration:

| Scale | Items | Approx tokens | Quality | Mean latency |
|---|---:|---:|---:|---:|
| smoke | ~349 | ~50k | 62/62 | ~9 ms |
| medium | ~1086 | ~200k | 62/62 | ~31 ms |
| stress | ~9992 | ~2M | 62/62 | ~290 ms |

Interpretation:

- This is an engineering useful result, not theoretical novelty by itself.
- Fast retrieval over a 2M-token corpus is expected with indexing/search methods.
- The paper-worthy part is admissibility under stale/decoy/conflict/safety/abstention constraints.

### Local Qwen GGUF

Model path tested:

```text
C:\Users\arahe\Downloads\Qwen3-4B-Q4_K_M.gguf
```

Findings:

- The GGUF loads through `llama-cpp-python`.
- CPU probe took roughly 18 seconds.
- Forced generative reranking over small candidate lists took roughly 18-37 seconds per call.
- Forced local reranking sometimes selected stale/decoy evidence on normal “latest/current” questions.

Conclusion:

- Do not put generative Qwen on the hot path.
- Use local models only as advisory rerankers for ambiguous cases, or better, distill a tiny route classifier from deterministic oracle traces.
- Deterministic MoCE gates must remain after any local model output.

Rule:

> Small/local model proposes. MoCE verifies. Frontier model answers.

## Algorithm research and implementation plan

### 1. Exact-anchor indexes

Highest ROI for coding-agent memory.

Dedicated indexes for:

- commands;
- paths;
- filenames;
- function/module names;
- benchmark IDs;
- ctx values;
- dates;
- run IDs.

Suggested structures:

- hash maps for exact anchors;
- prefix trie or finite-state transducer for paths/commands;
- trigram index for fuzzy code/path lookup.

### 2. BM25F inverted index

Replace full-ish scanning with a field-weighted inverted index.

Fields:

- `id`;
- `tags`;
- `source_family`;
- `authority`;
- `staleness`;
- `text`;
- `provenance`.

Base score:

```text
score = BM25F(text/id/tags/provenance)
      + exact_anchor_bonus
      + source_family_bonus
      + authority_bonus
      + freshness_bonus
      - stale_penalty
      - decoy_penalty
      - wrong_family_penalty
```

### 3. WAND / Block-Max WAND

Use dynamic pruning for fast top-k retrieval:

- WAND;
- MaxScore;
- Block-Max WAND;
- impact-ordered indexes.

This matters more when corpus grows beyond the current synthetic 2M-token scale.

### 4. Conflict/authority graph

Represent relationships explicitly:

```text
current_record --supersedes--> stale_record
real_record --conflicts_with--> decoy_record
policy_record --overrides--> memory_claim
```

Routing should retrieve relevant nodes and expand to conflict neighbors when needed.

### 5. Budgeted packet packing

After retrieval, choose evidence under frontier-token budget.

Objective:

```text
maximize admissible evidence utility
subject to token_budget, latency_budget, mandatory_evidence, and conflict-pair constraints
```

Start with greedy utility/token packing; later formalize as budgeted maximum coverage or constrained knapsack.

### 6. Learned route classifier

Distill deterministic oracle traces into a tiny classifier.

Input:

- query tokens;
- exact-anchor features;
- source-family cues;
- safety/conflict markers.

Output labels:

- `no_context`;
- `retrieve_runbook`;
- `retrieve_source_code`;
- `retrieve_benchmark`;
- `retrieve_policy`;
- `retrieve_debug`;
- `retrieve_workflow`;
- `retrieve_conflict_pair`;
- `abstain`.

This is a better small-model hot-path role than generative reranking.

## Rust refactor plan

Do not rewrite the full project first. Keep Python for dataset generation, orchestration, paper tables, and plots.

Port only the hot router:

```text
router-rs/
  load corpus_items.jsonl
  build indexes
  answer query with route_proof JSON
```

Rust should implement:

- exact-anchor maps;
- BM25F inverted index;
- optional WAND/Block-Max WAND;
- authority/staleness/decoy gates;
- conflict graph expansion;
- packet packing;
- route proof output.

Expected performance:

| Implementation | Expected stress latency |
|---|---:|
| Current Python full-ish scan | ~290 ms |
| Python inverted index | ~50-150 ms |
| Rust naive scan | ~30-100 ms |
| Rust inverted index | ~5-30 ms |
| Rust + WAND/Block-Max WAND | potentially <5-20 ms at larger scale |

Rust is a Phase 3 optimization. First make proof traces and baselines paper-ready.

## MoE-adjacent design ideas to borrow

### Sparse top-k routing

Activate only top-1 to top-3 experts per query.

Example:

```json
{
  "router_scores": {
    "runbook_expert": 0.92,
    "source_code_expert": 0.41,
    "benchmark_expert": 0.03,
    "safety_expert": 0.01
  },
  "activated_experts": ["runbook_expert", "source_code_expert"]
}
```

### Shared experts vs routed experts

Always-on shared experts:

- authority gate;
- provenance gate;
- safety gate;
- abstention gate;
- token-budget gate.

Routed experts:

- runbook;
- source code;
- benchmark;
- debug;
- workflow;
- safety-policy retrieval.

### Expert Choice routing

Some experts should be able to claim a query if exact anchors fire.

Examples:

- query mentions `C:/ivy/private.txt` -> safety expert claims;
- query mentions `ctx=8192 decode_tps` -> benchmark expert claims;
- query mentions `old_eval_runner` -> runbook/stale-conflict expert claims.

### Hash routing

Exact anchors can route without learned models:

```text
hash(command) -> runbook expert
hash(file path) -> source/path expert
hash(ctx value) -> benchmark expert
hash(policy phrase) -> safety expert
```

### Mixture of Depths

Allocate variable context effort:

- easy query -> no context;
- anchored query -> one memory expert;
- conflict query -> conflict graph + proof trace;
- low-confidence query -> optional local model or frontier clarification.

### Speculative decoding analogy

Speculative decoding uses a small/draft model and a larger verifier.

MoCE/MoME analogy:

```text
small/deterministic router drafts evidence
MoCE verifies admissibility
frontier model verifies/synthesizes final answer
```

## Paper positioning

### Best paper framing

Avoid:

- “We invented MoME.”
- “Fast retrieval from 2M tokens.”
- “Small model remembers for the frontier model.”
- “Brain-like memory.”

Use:

> **Authority-aware context compilation for frontier-model coding agents.**

or:

> **MoE-style sparse routing over external memory experts for agent context.**

Potential title:

> **Authority-Aware Context Compilation for Frontier-Model Coding Agents**

Alternative:

> **MoCE/MoME: External Sparse Expert Routing for Agent Memory**

### Core contributions

1. MoE-style external expert routing architecture for agent context.
2. Authority/staleness/decoy/safety-aware context compilation.
3. Route proof output with selected/rejected evidence and conflict pairs.
4. Context-stress benchmark with stale, decoy, conflict, safety, and abstention cases.
5. Negative deployment result: local generative GGUF is too slow/unsafe as a hot-path authority; it should be advisory/classification-only.

### Required additions for paper readiness

1. `schemas/route_proof.schema.json`.
2. Proof traces from harness:
   - router scores;
   - activated experts;
   - selected evidence;
   - rejected evidence;
   - rejection reasons;
   - conflict pairs;
   - authority chain;
   - answerability;
   - packet token count;
   - full-context tokens avoided;
   - latency.
3. Baseline runner:
   - naive BM25/top-k;
   - BM25 + source-family filter;
   - local Qwen reranker only;
   - deterministic MoCE/MoME;
   - hybrid MoCE/MoME + local advisory reranker.
4. Real Ivy/coding-agent query mini-dataset, 20-50 hand-labeled examples.
5. Token-savings and latency-quality Pareto tables.

## Suggested 1-3 venue targets

### 1. EMNLP 2026 Industry Track

Best primary target.

Why it fits:

- real-world language system;
- latency/cost constraints;
- system orchestration;
- negative results;
- evaluation methodology;
- deployment lessons.

Important verified details:

- Conference: October 24-29, 2026, Budapest, Hungary.
- Submission deadline: June 16, 2026 AoE.
- Industry papers: max 6 pages, excluding references/limitations/ethics/appendix.
- Double-blind.
- Does not use ARR.
- Do not submit closely related work to multiple EMNLP tracks.

Source:

- https://2026.emnlp.org/calls/industry_track/

### 2. EMNLP 2026 Main / ARR May Cycle

Moonshot target if we can produce stronger empirical novelty quickly.

Verified details:

- ARR submission deadline: May 25, 2026.
- Reviewer registration deadline for all authors: May 27, 2026.
- Author response/discussion: July 7-13, 2026.
- EMNLP commitment deadline: August 2, 2026.
- Notification: August 20, 2026.
- Camera-ready: September 20, 2026.
- Conference: October 24-29, 2026.

Source:

- https://2026.emnlp.org/calls/main_conference_papers/

### 3. RAGE-KG 2026

Best backup/workshop fit, especially if we add explicit authority/conflict graphs.

Verified details:

- Topics include RAG architectures leveraging knowledge graphs, GraphRAG, AI agents, structured data, neurosymbolic approaches, and bold proposals for RAG systems.
- Short papers: 4-6 pages excluding references.
- Full papers: 8-12 pages excluding references.
- Abstracts due: July 17, 2026.
- Papers due: July 24, 2026.
- Acceptance notification: August 17, 2026.
- Camera-ready: September 1, 2026.
- Workshop dates: October 25-26, 2026.

Source:

- https://2026.rage-kg.org/

### Not viable now: NeurIPS 2026 Main

As of 2026-05-10, the main NeurIPS 2026 deadlines have passed.

Verified details:

- Abstract deadline: May 4, 2026 AoE.
- Full paper deadline: May 6, 2026 AoE.
- Notification: September 24, 2026 AoE.

Source:

- https://nips.cc/Conferences/2026/CallForPapers

## Funding note

These venues are publication venues, not development grants.

Possible support paths:

- student volunteer roles;
- diversity/inclusion subsidies;
- registration/travel assistance if offered;
- university/employer travel support after acceptance;
- sponsor outreach after paper acceptance.

Do not assume EMNLP or RAGE-KG will fund development or travel by default.

## Resource list: MoE and adjacent techniques

### Sparse MoE / conditional computation

- Shazeer et al., “Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer”  
  https://arxiv.org/abs/1701.06538
- Switch Transformer  
  https://arxiv.org/abs/2101.03961
- GShard  
  https://arxiv.org/abs/2006.16668
- GLaM  
  https://arxiv.org/abs/2112.06905
- Mixtral of Experts  
  https://arxiv.org/abs/2401.04088
- DeepSeekMoE  
  https://arxiv.org/abs/2401.06066
- DeepSeek-V2  
  https://arxiv.org/abs/2405.04434
- Qwen MoE family / Qwen1.5-MoE technical reports: verify latest official source before citing.

### Routing, balance, and expert assignment

- Expert Choice Routing  
  https://arxiv.org/abs/2202.09368
- BASE Layers  
  https://arxiv.org/abs/2103.16716
- Hash Layers for Large Sparse Models  
  https://arxiv.org/abs/2106.04426
- Stable and Transferable Sparse Expert Models / ST-MoE: verify final citation before paper use.

### Large expert/memory retrieval

- Product Key Memory  
  https://arxiv.org/abs/1907.05242
- PEER / Mixture of a Million Experts  
  https://arxiv.org/abs/2407.04153
- Memorizing Transformers  
  https://arxiv.org/abs/2203.08913
- RETRO  
  https://arxiv.org/abs/2112.04426

### Adaptive compute / depth / decoding analogies

- Mixture of Depths  
  https://arxiv.org/abs/2404.02258
- Speculative decoding  
  https://arxiv.org/abs/2211.17192
- Medusa  
  https://arxiv.org/abs/2401.10774
- Self-speculative decoding  
  https://arxiv.org/abs/2309.08168

## Resource list: RAG, memory, and routing

### RAG and retrieval-augmented models

- Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks  
  https://arxiv.org/abs/2005.11401
- REALM  
  https://arxiv.org/abs/2002.08909
- RETRO  
  https://arxiv.org/abs/2112.04426
- Self-RAG  
  https://arxiv.org/abs/2310.11511
- Adaptive-RAG  
  https://arxiv.org/abs/2403.14403
- Corrective RAG / CRAG  
  https://arxiv.org/abs/2401.15884
- FLARE  
  https://arxiv.org/abs/2305.06983
- HyDE  
  https://arxiv.org/abs/2212.10496
- FrugalGPT / model cascades  
  https://arxiv.org/abs/2305.05176

### Agent memory systems and benchmarks

- MemGPT  
  https://arxiv.org/abs/2310.08560
- Generative Agents  
  https://arxiv.org/abs/2304.03442
- LongMemEval: verify final link before paper use.
- LoCoMo: verify final link before paper use.
- RULER long-context benchmark: verify final link before paper use.
- RAGRouter-Bench: verify final link before paper use.
- 2026 memory survey mentioned in prior research: verify final link/citation before paper use.

### Existing names that overlap

- Lamini “Mixture of Memory Experts” paper/resource: verify final citation before using the exact MoME name.
- MoICE / Mixture of In-Context Experts: verify final citation before using the exact MoCE/MoICE comparison.

## Resource list: search and indexing algorithms

- BM25 / probabilistic relevance framework overview  
  https://ir.webis.de/anthology/2009.ftir_journal-ir0anthology0volumeA3A4.0/
- WAND / MaxScore / Block-Max WAND family: verify exact papers before formal citation.
- SPLADE sparse retrieval  
  https://arxiv.org/abs/2107.05720
- ColBERT late interaction  
  https://arxiv.org/abs/2004.12832
- HNSW approximate nearest neighbor search  
  https://arxiv.org/abs/1603.09320
- Reciprocal Rank Fusion: verify final citation before formal paper use.
- LambdaMART / learning to rank: verify final citation before formal paper use.


## Naming stack: MoCE, MoME, ACCA, and ESCAPE

Use these names for different layers, not as competing replacements.

```text
MoCE/MoME = architecture
ACCA      = core algorithm
ESCAPE    = optional prototype/system branding
```

### MoCE

**MoCE = Mixture of Context Experts.**

MoCE is the MoE-style router/compiler. It scores and activates context experts, enforces context capacity, applies always-on authority/provenance/safety gates, and decides whether the final frontier packet should answer, abstain, reject a decoy, or resolve a conflict.

### MoME

**MoME = Mixture of Memory Experts.**

MoME is the external expert pool. It contains sparse retrieval experts such as runbook memory, source-code memory, benchmark memory, safety-policy memory, workflow traces, debug memories, exact-anchor indexes, and conflict-graph memory.

### ACCA

**ACCA = Authority-Constrained Context Assembly.**

ACCA is the core algorithm that turns MoME candidate outputs into an admissible frontier context packet.

ACCA steps:

```text
1. score/query route with MoCE router
2. activate sparse MoME experts
3. retrieve candidate evidence
4. expand conflict/supersession neighbors when needed
5. reject inadmissible stale/decoy/unsafe/wrong-family evidence
6. classify answerability
7. pack selected evidence under token/latency budget
8. emit route proof and compact frontier packet
```

Paper sentence:

> We implement MoCE/MoME, an MoE-style external expert architecture for agent memory. Its core algorithm, Authority-Constrained Context Assembly (ACCA), activates sparse memory experts and compiles admissible evidence packets under authority, freshness, conflict, safety, token, and latency constraints.

### ESCAPE

**ESCAPE = External Sparse Context And Provenance Experts.**

ESCAPE is optional branding for the prototype system. It is more memorable but less technically precise than ACCA.

Recommended use:

```text
Architecture: MoCE/MoME
Algorithm: ACCA
Prototype/system: ESCAPE, optional
```

Example:

> ESCAPE is a prototype implementation of ACCA over a MoCE/MoME external expert architecture.

Do not lead a paper with ESCAPE unless we want a heavily branded systems paper. For EMNLP Industry, lead with ACCA and MoCE/MoME, and mention ESCAPE only as the implementation name.

## Companion design notes

- `docs/ACCA_ESCAPE_SUPERCHARGED_DESIGN.md` — MoE-adjacent concepts mapped to ACCA/ESCAPE, including capacity factor, expert choice, context depth, route proofs, taint, context ABI, and evaluation metrics.

## Implementation next steps

Recommended order:

1. Add `schemas/route_proof.schema.json`.
2. Refactor harness output into MoE-style route proof:
   - `router_scores`;
   - `activated_experts`;
   - `shared_experts`;
   - `expert_outputs`;
   - `selected_evidence`;
   - `rejected_evidence`;
   - `conflict_pairs`;
   - `authority_chain`;
   - `answerability`;
   - `latency_ms`;
   - `frontier_packet_tokens`;
   - `tokens_avoided`.
3. Add baseline retrievers:
   - naive BM25/top-k;
   - BM25 + source-family filter;
   - local Qwen reranker only;
   - deterministic MoCE/MoME;
   - hybrid MoCE/MoME + advisory local model.
4. Add comparison runner and tables.
5. Add real Ivy query set with 20-50 hand-labeled cases.
6. Then build Rust indexed router prototype.
7. Then train/distill tiny route classifier from deterministic oracle traces.

## One-sentence project direction

> Build MoCE/MoME as an MoE-style external sparse expert router that compiles admissible, provenance-backed, latency-bounded context packets for frontier-model coding agents.


