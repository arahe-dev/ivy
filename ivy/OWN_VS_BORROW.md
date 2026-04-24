# OWN VS BORROW

## IVY owns
| Area | Concrete ownership |
|---|---|
| Experiment control | Manifest format, run orchestration, run IDs, artifact layout |
| Reproducibility | Seeds, fixed prompts, run metadata capture, comparable outputs |
| Observability | Trace/event schema, logging hooks, timings, bytes-moved accounting |
| KV policy research | Circular KV Lite policy logic and evaluation harness |
| Long-context experiments | Stress prompts, context window experiments, analysis notes |

## IVY borrows
| Area | Borrowed component |
|---|---|
| Core inference | `llama.cpp` (or equivalent trusted local runtime) |
| Model formats | Existing GGUF ecosystem/tooling |
| Tokenization and decode internals | Substrate implementation |
| Baseline generation path | Stock substrate execution path |

## Not building yet
| Area | Deferred work |
|---|---|
| Numerical substrate | Custom kernels, projection math, attention math |
| Platform/UI | Broad assistant UX, productized multi-surface app |
| Advanced policy complexity | MoE KV policy, distributed orchestration, SSD expert streaming integration in this phase |
| Multimodal | Vision/audio pipelines and eval stack |

