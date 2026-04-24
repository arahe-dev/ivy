# IVY

IVY is now a local LLM systems lab, not a from-scratch inference engine.

It uses a trusted inference substrate (likely `llama.cpp`) and focuses on experiment manifests, reproducible runs, trace/event logging, KV policy experiments, and long-context memory behavior.

First flagship module: `Circular KV Lite`.

This repo is the operational workspace for running baseline substrate measurements, implementing KV policy experiments, and comparing results with reproducible artifacts.
