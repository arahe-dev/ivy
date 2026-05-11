# CP37 Negative Memory Benchmark - 2026-05-11

## What Changed

CP37 extends the plugin benchmark with a negative retrieval case:

```text
What is today's Bitcoin price?
```

Expected behavior:

- select no local memory
- avoid treating source-code occurrences of the benchmark query as authoritative market data

## Bug Found

The first run failed:

```text
Passed expectations: 4 / 5
Selected: ing_mome_moce_exp_run_context_memory_plugin_be_1_583454a3b472
```

The router selected the benchmark script itself because the script contained the Bitcoin query string. That is exactly the sort of benchmark feedback loop we want to catch.

## Fix

The volatile commercial/current-fact gate now:

- treats `today`, `today's`, `now`, and `live` as current/volatile triggers
- recognizes market entities such as `bitcoin`, `btc`, `ethereum`, and `stock`
- rejects `source_code` items as support for live/current commercial facts

## Latest Benchmark

Command:

```powershell
python MoME-MoCE-Exp\scripts\run_context_memory_plugin_benchmark.py --reset
```

Result:

- Query count: `5`
- Passed expectations: `5 / 5`
- Avg query wall: `92.131 ms`
- Avg router latency: `10.728 ms`

Output:

```text
C:\ivy\MoME-MoCE-Exp\out\plugin_benchmarks\context_memory_plugin_benchmark_20260511T170607Z.md
```

## Why This Matters

This is a small but important quality move. A memory/context system should not only retrieve relevant internal memory; it must also abstain when the query needs live external data. Otherwise it becomes a confident local-context hallucination machine.
