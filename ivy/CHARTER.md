# CHARTER

## Project identity
IVY is a local LLM systems lab built on top of a trusted inference core.

## Project goal
Build reproducible local experiments that improve long-context behavior through KV policy work, starting with `Circular KV Lite`, with strong traceability and measurement.

## Anti-goals
- Building custom quant kernels.
- Building custom projection or attention math.
- Owning GGUF parsing or full inference internals.
- Building broad assistant UI or multimodal platform scope.
- Starting with MoE KV as first implementation.

## First flagship module
`Circular KV Lite`: a minimal KV policy module for controlled eviction/residency behavior under long context.

## First 30-day success criteria
- Baseline run flow exists and is repeatable from a manifest.
- Trace schema is implemented enough to capture per-token/layer timing and bytes moved.
- Circular KV Lite first implementation runs on at least one local model path.
- Baseline vs Circular KV Lite comparison is produced for correctness, TTFT, decode throughput, memory footprint, and long-context behavior.

