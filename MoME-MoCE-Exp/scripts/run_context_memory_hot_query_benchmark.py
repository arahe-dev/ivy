from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from run_context_memory_plugin_benchmark import run_benchmark, load_plugin
except ModuleNotFoundError:
    from scripts.run_context_memory_plugin_benchmark import run_benchmark, load_plugin


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE = ROOT / "out" / "hot_query_benchmark_store"
DEFAULT_OUT = ROOT / "docs" / "HOT_QUERY_BENCHMARK.md"


HOT_QUERIES = [
    "What did CP28 show about final answer packet formats?",
    "What MCP tools does ivy-context-memory expose?",
    "What did CP29 change about generated output ingestion?",
    "How does CP32 make repeated plugin builds faster?",
    "What is the latest CP42 rebuild policy versus stale memory?",
    "What is today's Bitcoin price?",
]


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def measure_query(plugin: Any, store: Path, query: str) -> dict[str, Any]:
    started = time.perf_counter()
    result = plugin.query_store(store, query=query, variant="auto", top_k=5)
    wall_ms = round((time.perf_counter() - started) * 1000, 3)
    return {
        "query": query,
        "wall_ms": wall_ms,
        "plugin_wall_ms": result.get("wall_ms"),
        "router_latency_ms": result.get("latency_ms"),
        "packet_mode": result.get("packet_mode"),
        "selected_count": result.get("selected_count"),
        "timings_ms": result.get("timings_ms", {}),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    timing_names = ["prefilter", "corpus", "router_init", "route", "render", "packet_write", "total"]
    return {
        "query_count": len(rows),
        "avg_wall_ms": round(sum(float(row["wall_ms"]) for row in rows) / max(1, len(rows)), 3),
        "avg_plugin_wall_ms": round(sum(float(row.get("plugin_wall_ms") or 0.0) for row in rows) / max(1, len(rows)), 3),
        "avg_router_latency_ms": round(sum(float(row.get("router_latency_ms") or 0.0) for row in rows) / max(1, len(rows)), 3),
        "avg_timings_ms": {
            name: round(sum(float(row.get("timings_ms", {}).get(name, 0.0) or 0.0) for row in rows) / max(1, len(rows)), 3)
            for name in timing_names
        },
    }


def run_hot_query_benchmark(store: Path, *, source_root: Path, passes: int, reset: bool) -> dict[str, Any]:
    setup = run_benchmark(store, source_root=source_root, reset=reset)
    plugin = load_plugin()
    pass_rows = []
    for pass_index in range(1, passes + 1):
        rows = [measure_query(plugin, store, query) for query in HOT_QUERIES]
        pass_rows.append({"pass": pass_index, "summary": summarize(rows), "rows": rows})
    return {
        "schema_version": "ivy_context_memory.hot_query_benchmark.v0.1",
        "created_at": utc_now(),
        "store": str(store),
        "source_root": str(source_root),
        "setup_summary": setup["summary"],
        "passes": pass_rows,
    }


def write_report(result: dict[str, Any], out: Path) -> None:
    lines = [
        "# IVY Context Memory Hot Query Benchmark",
        "",
        f"Created: `{result['created_at']}`",
        "",
        "## Summary",
        "",
        "| Pass | Avg wall ms | Avg plugin wall ms | Avg router ms | Prefilter ms | Corpus ms |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["passes"]:
        summary = row["summary"]
        timings = summary["avg_timings_ms"]
        lines.append(
            f"| {row['pass']} | {summary['avg_wall_ms']} | {summary['avg_plugin_wall_ms']} | "
            f"{summary['avg_router_latency_ms']} | {timings['prefilter']} | {timings['corpus']} |"
        )
    lines.extend(["", "## Rows", ""])
    for pass_row in result["passes"]:
        lines.append(f"### Pass {pass_row['pass']}")
        lines.append("")
        lines.append("| Query | Wall ms | Router ms | Mode | Selected |")
        lines.append("|---|---:|---:|---|---:|")
        for row in pass_row["rows"]:
            lines.append(f"| {row['query']} | {row['wall_ms']} | {row['router_latency_ms']} | {row['packet_mode']} | {row['selected_count']} |")
        lines.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure repeated hot query behavior for the IVY context-memory plugin.")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--passes", type=int, default=3)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    result = run_hot_query_benchmark(args.store.resolve(), source_root=args.source_root.resolve(), passes=args.passes, reset=args.reset)
    write_report(result, args.out.resolve())
    print(json.dumps({"ok": True, "report": str(args.out), "passes": [row["summary"] for row in result["passes"]]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
