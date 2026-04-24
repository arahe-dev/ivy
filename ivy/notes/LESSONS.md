# LESSONS FROM BREAD V2/V3

- Memory movement and residency were the real bottlenecks; raw compute optimization was not the limiting factor.
- Owning the custom numerical substrate (kernels/projections/attention internals) cost too much time for too little leverage.
- Correctness risk was high in custom optimized paths (GPU Q/K projection mismatches vs CPU/reference).
- Observability and reproducibility were underpowered; this blocked fast iteration and trustworthy comparisons.
- The highest-leverage axis is KV policy plus long-context memory behavior, measured with disciplined traces and repeatable runs.

