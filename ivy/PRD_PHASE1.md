# PRD: IVY Phase 1 — Local KV Policy Lab

## Status
Phase 1 PRD. Pre-implementation. Defines the first real version of IVY as a runnable local systems lab built on a trusted inference substrate.

## One-line product definition
IVY is a local LLM systems lab built on top of a trusted inference core, focused on reproducible runs, traceable behavior, and KV policy experiments for long-context local inference.

---

## 1. Problem

Local LLM experimentation breaks down for two reasons:

1. **Numerical substrate ownership is too expensive**
   - Custom kernels, projection math, and attention correctness consume huge effort before experiments can even begin.
   - This creates long debugging loops and blocks progress on the actual research questions.

2. **Long-context behavior is poorly instrumented**
   - It is hard to answer simple questions like:
     - what memory moved?
     - what policy made that happen?
     - why did throughput change?
     - where did correctness drift begin?
   - Existing local runtimes can run models, but they do not provide a clean, reproducible lab for KV policy experiments.

The result is that systems ideas around KV retention, eviction, promotion, and long-context behavior are difficult to test quickly and honestly.

---

## 2. Product goal

Build the smallest useful version of IVY that can:

- run a stock local model path reproducibly from a manifest
- save consistent run artifacts
- capture simple trace events
- compare baseline substrate behavior vs one experimental KV policy
- support one flagship systems experiment: **Circular KV Lite**

This phase is about creating a **researchable runtime**, not a new inference core.

---

## 3. Target user

Primary user:
- one local researcher / builder working on local LLM systems

Initial use case:
- “I want to run the same model, same prompt, same seed, same context settings, and compare stock behavior vs a KV policy experiment with enough artifacts to understand what changed.”

This phase is not for:
- end users
- broad assistant UX
- team dashboards
- cloud/distributed serving

---

## 4. Non-goals

Phase 1 explicitly does **not** include:

- custom quantization kernels
- custom projection or attention math
- custom GGUF parsing
- a new inference engine
- MoE KV as the first implementation
- multimodal platform work
- productized assistant UI
- distributed or multi-node orchestration
- training or learned routing

If a task starts pulling IVY into substrate math ownership, it is out of scope for this phase.

---

## 5. Product principles

### 5.1 Borrow the boring floor
IVY should reuse a trusted local substrate, likely `llama.cpp`, for:
- model loading
- tokenizer behavior
- baseline generation path
- normal dense inference

### 5.2 Own the experimental layer
IVY should own:
- manifests
- run orchestration
- artifact layout
- trace schema
- KV policy logic
- evaluation harness

### 5.3 Reproducibility first
Every experiment should be runnable again from:
- manifest
- command
- pinned prompt(s)
- seed
- saved outputs and notes

### 5.4 Build vertically
Every new feature must answer one end-to-end question.
Example:
- “Does Circular KV Lite change memory behavior with bounded correctness impact?”

Not:
- “make the engine smarter/faster/more modular” in the abstract.

### 5.5 Traceability is the product
If IVY cannot explain what happened, the feature is incomplete.

---

## 6. Phase 1 scope

Phase 1 has four deliverables.

### Deliverable A — Baseline run system
A baseline run can be launched from a manifest and produces:
- exact command used
- output text
- timings
- notes
- stable run id
- fixed prompt + seed metadata

### Deliverable B — Trace schema v0
IVY records lightweight event data with:
- run id
- token id
- layer id
- phase
- timing
- bytes moved
- KV policy decision
- notes

This is not a full tensor dump system.
It is a minimal event layer that enables trustworthy comparison.

### Deliverable C — Evaluation harness
IVY can compare:
- A: stock substrate baseline
- B: substrate + experimental KV policy

Comparison dimensions:
- correctness / drift
- TTFT
- decode throughput
- memory footprint
- long-context behavior

### Deliverable D — Circular KV Lite
A minimal KV policy experiment with:
- basic circular/residency logic
- retention/eviction decisions
- instrumentation hooks only
- one model
- one substrate path
- fixed prompts and seed

It is intentionally small.
It is not the full Circular KV vision.

---

## 7. Circular KV Lite definition

### Problem
Naive KV residency degrades long-context local runs through memory pressure and excessive movement.

### Phase 1 goal
Implement the smallest policy layer that can change KV retention behavior in a measurable way while remaining explainable.

### First implementation scope
- simple circular/residency behavior
- one local run path
- one model family
- no new substrate math
- no distributed coordination
- no learned policy

### Explicitly deferred
- MoE KV
- SSD-tier productization
- learned routers
- generalized cross-model KV policy engine
- complex offload orchestration

### Success condition
Circular KV Lite is worth continuing only if:
- runs are reproducible
- behavior is measurable
- trace artifacts explain the result
- correctness remains bounded enough to evaluate meaningfully

---

## 8. Core user flow

### Baseline flow
1. User selects a manifest.
2. IVY runs the stock substrate path.
3. IVY saves:
   - command
   - output
   - timings
   - notes
   - run metadata

### Experimental flow
1. User selects the same manifest with a KV policy enabled.
2. IVY runs the substrate + IVY policy path.
3. IVY saves the same artifacts plus trace events.
4. IVY compares baseline vs experiment.

### Comparison flow
1. User opens the two runs.
2. IVY reports:
   - output drift
   - TTFT delta
   - decode throughput delta
   - memory delta
   - long-context behavior notes
3. User can inspect trace events to understand where the policy helped or hurt.

---

## 9. Success metrics

## Must-have metrics
- baseline run is reproducible from a manifest
- outputs and timings are saved every run
- trace schema v0 is implemented for at least one path
- baseline vs Circular KV Lite comparison can be produced
- correctness is not broken beyond meaningful evaluation

## Decision metrics
Circular KV Lite should be judged on:
- correctness drift vs baseline
- TTFT change
- decode throughput change
- peak/average memory footprint
- long-context behavior at larger contexts

### Good first outcome
Not “huge speedup.”

A good first outcome is:
- measurable memory-behavior change
- bounded correctness impact
- clear trace explanation
- enough confidence to iterate

---

## 10. Technical boundaries

### IVY owns
- manifest format
- run ids and artifact layout
- reproducibility contract
- trace/event schema
- KV policy logic
- comparison/evaluation harness
- long-context experiment design

### IVY borrows
- trusted inference core
- model loading
- tokenization
- baseline decode path
- standard dense execution

### Not building yet
- custom kernels
- full assistant shell
- multimodal stack
- MoE KV
- distributed memory systems

---

## 11. Repo artifacts required

The repo must contain and maintain:

- `README.md`
- `CHARTER.md`
- `OWN_VS_BORROW.md`
- `ROADMAP.md`
- `manifests/`
- `runs/`
- `docs/CIRCULAR_KV_LITE.md`
- `docs/TRACE_SCHEMA.md`
- `docs/EVAL_PLAN.md`
- `notes/LESSONS.md`
- `notes/DO_NOT_TOUCH.md`
- `scripts/run_baseline.md`
- `scripts/next_steps.md`

A phase is not complete if these are out of sync with actual repo behavior.

---

## 12. Immediate roadmap

### Tonight
- finalize repo scaffold
- pin one baseline manifest
- define baseline artifact contract
- execute one manual baseline run
- save artifacts

### First 3 days
- make manifest-driven baseline execution repeatable
- capture stable outputs and timings
- implement first trace logging path
- verify reruns are stable

### First week
- implement first Circular KV Lite policy path
- run baseline vs policy A/B
- capture correctness and performance deltas
- tighten notes and artifacts for comparison

### First month
- iterate policy parameters
- expand context lengths
- stabilize trace schema
- produce keep/adjust/replace decision memo for Circular KV Lite

---

## 13. Risks

### Risk: scope drift back into substrate work
Mitigation:
- enforce anti-goals
- reject math/kernel work unless it is directly required by the chosen policy seam

### Risk: trace system becomes too broad too early
Mitigation:
- keep trace schema v0 lightweight
- do summaries and events first, not giant dumps

### Risk: Circular KV Lite is too small to show value
Mitigation:
- choose prompts and contexts where memory behavior is visible
- evaluate memory behavior and traceability, not only throughput

### Risk: results are noisy and hard to compare
Mitigation:
- fixed seed
- fixed prompts
- fixed manifest fields
- repeated runs
- strict artifact saving

---

## 14. Exit criteria for Phase 1

Phase 1 is successful when all of the following are true:

1. One baseline run can be reproduced from a manifest.
2. One experimental run with Circular KV Lite can be reproduced from a manifest.
3. Both runs produce complete artifacts.
4. IVY can compare baseline vs experiment on:
   - correctness
   - TTFT
   - throughput
   - memory footprint
   - long-context behavior
5. Trace artifacts are sufficient to explain at least one observed delta.
6. A decision can be made to:
   - continue Circular KV Lite
   - adjust it
   - or replace it

---

## 15. Final phase decision rule

If IVY reaches the point where:
- baseline is reproducible
- traces are useful
- Circular KV Lite can be measured honestly

then Phase 1 is complete, even if the first policy is not a big win.

If IVY cannot do those things, then the missing product is still the lab itself, not the policy idea.
