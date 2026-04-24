# ROADMAP

## Tonight
- Create repo scaffold, charter, boundaries, and manifest.
- Define baseline run folder and artifact contract.
- Write Circular KV Lite first-scope doc and trace schema.
- Execute one manual stock-substrate baseline run and save artifacts.

## First 3 days
- Wire manifest fields into a repeatable run command path.
- Record baseline metrics for one model/prompt set using fixed seed.
- Add first trace logging path for token/layer timing + bytes moved.
- Validate that reruns with same manifest produce stable outputs/metrics.

## First week
- Implement Circular KV Lite minimal policy path (single-node local run).
- Run A/B: stock baseline vs Circular KV Lite on same prompts and seed.
- Capture correctness deltas and performance deltas in run artifacts.
- Tighten artifact layout and notes so experiments are comparable.

## First month
- Iterate Circular KV Lite policy parameters across multiple context lengths.
- Expand long-context stress scenarios and document failure modes.
- Stabilize trace schema and add lightweight analysis scripts.
- Produce a decision memo: keep/adjust/replace Circular KV Lite based on measured results.

