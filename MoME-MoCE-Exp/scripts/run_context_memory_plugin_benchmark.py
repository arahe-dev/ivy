from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
PLUGIN_SCRIPT = REPO_ROOT / "plugins" / "ivy-context-memory" / "scripts" / "ivy_context_memory.py"
DEFAULT_STORE = ROOT / "out" / "plugin_benchmark_store"
DEFAULT_OUT = ROOT / "out" / "plugin_benchmarks"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_plugin() -> Any:
    spec = importlib.util.spec_from_file_location("ivy_context_memory_plugin_bench", PLUGIN_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load plugin script: {PLUGIN_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def measure(label: str, fn) -> dict[str, Any]:
    started = time.perf_counter()
    payload = fn()
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    return {"label": label, "wall_ms": elapsed_ms, "payload": payload}


def case(query: str, *, expect_any: list[str] | None = None, should_select: bool = True) -> dict[str, Any]:
    return {"query": query, "expect_any": expect_any or [], "should_select": should_select}


def run_benchmark(store: Path, *, source_root: Path, reset: bool) -> dict[str, Any]:
    if reset and store.exists():
        if ROOT not in store.resolve().parents:
            raise RuntimeError(f"refusing to reset store outside MoME-MoCE-Exp: {store}")
        shutil.rmtree(store)

    plugin = load_plugin()
    setup: list[dict[str, Any]] = []
    setup.append(measure("init", lambda: plugin.init_store(store)))
    setup.append(measure("ingest_register", lambda: plugin.add_source(store, source_root, build=False)))
    setup.append(
        measure(
            "remember_cp28",
            lambda: plugin.remember(
                store,
                text="CP28 showed contradiction-aware packets won final-answer A/B on conflict cases.",
                source_path="root/notes/cp28.md",
                tags=["cp28", "final-answer"],
                authority="medium",
            ),
        )
    )
    setup.append(
        measure(
            "remember_cp29",
            lambda: plugin.remember(
                store,
                text="CP29 added a persisted prefilter index and skipped generated output directories so plugin stores do not ingest their own packets.",
                source_path="root/notes/cp29.md",
                tags=["cp29", "prefilter", "generated-output"],
                authority="medium",
            ),
        )
    )
    setup.append(
        measure(
            "remember_cp32",
            lambda: plugin.remember(
                store,
                text="CP32 added build fingerprint caching so unchanged plugin builds reuse the existing dataset and query index.",
                source_path="root/notes/cp32.md",
                tags=["cp32", "build-cache", "fingerprint"],
                authority="medium",
            ),
        )
    )
    setup.append(
        measure(
            "remember_cp33",
            lambda: plugin.remember(
                store,
                text="CP33 exposed ivy-context-memory as MCP stdio tools: query, remember, ingest, build, and status.",
                source_path="root/notes/cp33.md",
                tags=["cp33", "mcp", "plugin"],
                authority="medium",
            ),
        )
    )
    stale_cp42 = measure(
        "remember_cp42_stale",
        lambda: plugin.remember(
            store,
            text="CP42 stale policy said any source edit requires a full plugin rebuild.",
            source_path="root/notes/cp42-stale.md",
            tags=["cp42", "stale-policy"],
            authority="low",
            staleness="stale",
        ),
    )
    setup.append(stale_cp42)
    stale_cp42_id = stale_cp42["payload"]["note"]["id"]
    setup.append(
        measure(
            "remember_cp42_current",
            lambda: plugin.remember(
                store,
                text="CP42 current policy says changed-source rebuilds should reuse unchanged file chunks and reprocess only changed files.",
                source_path="root/notes/cp42-current.md",
                tags=["cp42", "current-policy", "chunk-cache"],
                authority="medium",
                staleness="current",
                supersedes=[stale_cp42_id],
                conflicts_with=[stale_cp42_id],
            ),
        )
    )
    setup.append(measure("build_cache_probe", lambda: plugin.build_store(store)))

    queries = [
        case("What did CP28 show about final answer packet formats?", expect_any=["note_", "cp28"]),
        case("What MCP tools does ivy-context-memory expose?", expect_any=["note_", "cp33", "mcp"]),
        case("What did CP29 change about generated output ingestion?", expect_any=["generated junk", "generated output", "prefilter"]),
        case("How does CP32 make repeated plugin builds faster?", expect_any=["fingerprint", "cache", "unchanged build"]),
        case("What is the latest CP42 rebuild policy versus stale memory?", expect_any=["unchanged file chunks", "stale policy", "changed files"]),
        case("What is today's Bitcoin price?", should_select=False),
    ]

    query_results = []
    for query_case in queries:
        measured = measure(
            query_case["query"],
            lambda q=query_case["query"]: plugin.query_store(store, query=q, variant="auto", top_k=5),
        )
        payload = measured["payload"]
        haystack = " ".join(
            [
                " ".join(payload.get("selected_ids", [])),
                payload.get("packet_text", ""),
            ]
        ).lower()
        selected_ids = payload.get("selected_ids", [])
        if query_case["should_select"]:
            measured["passed_expectation"] = bool(selected_ids) and any(term.lower() in haystack for term in query_case["expect_any"])
        else:
            measured["passed_expectation"] = not selected_ids
        measured["summary"] = {
            "selected_ids": payload.get("selected_ids", []),
            "variant": payload.get("variant"),
            "packet_mode": payload.get("packet_mode"),
            "router_latency_ms": payload.get("latency_ms"),
            "packet_words": payload.get("packet_words"),
            "prefilter": payload.get("prefilter", {}),
        }
        query_results.append(measured)

    return {
        "schema_version": "ivy_context_memory.plugin_benchmark.v0.1",
        "created_at": utc_now(),
        "store": str(store),
        "source_root": str(source_root),
        "setup": setup,
        "queries": query_results,
        "summary": {
            "query_count": len(query_results),
            "passed_expectations": sum(1 for row in query_results if row["passed_expectation"]),
            "avg_query_wall_ms": round(sum(row["wall_ms"] for row in query_results) / max(1, len(query_results)), 3),
            "avg_router_latency_ms": round(
                sum(float(row["summary"]["router_latency_ms"] or 0.0) for row in query_results) / max(1, len(query_results)),
                3,
            ),
        },
    }


def write_report(result: dict[str, Any], out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = out_dir / f"context_memory_plugin_benchmark_{stamp}.json"
    md_path = out_dir / f"context_memory_plugin_benchmark_{stamp}.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# IVY Context Memory Plugin Benchmark",
        "",
        f"- Created: `{result['created_at']}`",
        f"- Store: `{result['store']}`",
        f"- Source root: `{result['source_root']}`",
        f"- Passed expectations: `{result['summary']['passed_expectations']} / {result['summary']['query_count']}`",
        f"- Avg query wall: `{result['summary']['avg_query_wall_ms']} ms`",
        f"- Avg router latency: `{result['summary']['avg_router_latency_ms']} ms`",
        "",
        "| Query | Wall ms | Router ms | Mode | Selected | Pass |",
        "|---|---:|---:|---|---|---|",
    ]
    for row in result["queries"]:
        selected = ", ".join(row["summary"]["selected_ids"])
        lines.append(
            f"| {row['label']} | {row['wall_ms']} | {row['summary']['router_latency_ms']} | "
            f"{row['summary']['packet_mode']} | `{selected}` | {row['passed_expectation']} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark the IVY context memory plugin hot path.")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    result = run_benchmark(args.store.resolve(), source_root=args.source_root.resolve(), reset=args.reset)
    paths = write_report(result, args.out_dir.resolve())
    print(json.dumps({"ok": True, "summary": result["summary"], "paths": paths}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
