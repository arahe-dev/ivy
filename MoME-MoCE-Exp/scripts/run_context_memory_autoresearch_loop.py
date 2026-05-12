from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
PLUGIN_SCRIPT = REPO_ROOT / "plugins" / "ivy-context-memory" / "scripts" / "ivy_context_memory.py"
BENCHMARK_SCRIPT = ROOT / "scripts" / "run_context_memory_plugin_benchmark.py"
DEFAULT_STORE = ROOT / "out" / "autoresearch_loop" / "memory_store"
DEFAULT_OUT = ROOT / "out" / "autoresearch_loop"
DEFAULT_CONVERSATION_ROOT = Path.home() / ".codex" / "sessions"
DEFAULT_SCOREBOARD = ROOT / "docs" / "AUTORESEARCH_LOOP_SCOREBOARD.md"

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|bearer)\s*[:=]\s*[^\s`'\"\\]+"),
    re.compile(r"(?i)-----BEGIN [A-Z ]+PRIVATE KEY-----.*?-----END [A-Z ]+PRIVATE KEY-----", re.S),
    re.compile(r"(?i)(sk-[a-z0-9_-]{12,})"),
]
SAFE_EXTENSIONS = {".jsonl", ".md", ".txt"}


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def rough_tokens(text: str) -> int:
    return max(1, len(str(text).split()))


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def redact(text: str) -> str:
    out = text
    for pattern in SECRET_PATTERNS:
        out = pattern.sub("[REDACTED_SECRET]", out)
    out = re.sub(r"C:\\Users\\[^\\\s]+", r"C:\\Users\\[user]", out)
    return out


def scalar_texts(value: Any, *, parent_key: str = "") -> Iterable[str]:
    sensitive_key = any(term in parent_key.lower() for term in ["token", "secret", "password", "auth", "key"])
    if isinstance(value, str):
        if not sensitive_key and len(value.strip()) >= 20:
            yield value
    elif isinstance(value, list):
        for item in value:
            yield from scalar_texts(item, parent_key=parent_key)
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from scalar_texts(item, parent_key=str(key))


def iter_conversation_files(roots: list[Path], *, max_files: int) -> Iterable[Path]:
    count = 0
    for root in roots:
        if not root.exists():
            continue
        files = sorted(root.rglob("*"), key=lambda path: path.stat().st_mtime_ns if path.is_file() else 0, reverse=True)
        for path in files:
            if count >= max_files:
                return
            if not path.is_file() or path.suffix.lower() not in SAFE_EXTENSIONS:
                continue
            lower = path.name.lower()
            if any(term in lower for term in ["auth", "token", "secret", "key"]):
                continue
            count += 1
            yield path


def extract_conversation_records(roots: list[Path], *, max_files: int, max_records: int, max_chars: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in iter_conversation_files(roots, max_files=max_files):
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if path.suffix.lower() == ".jsonl":
            lines = raw.splitlines()
            for line_no, line in enumerate(lines, start=1):
                if len(records) >= max_records:
                    return records
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                text = redact("\n".join(scalar_texts(payload))).strip()
                if rough_tokens(text) < 12:
                    continue
                text = text[:max_chars]
                records.append(
                    {
                        "id": f"convo_{content_hash(str(path) + str(line_no) + text)[:16]}",
                        "source_path": str(path),
                        "line": line_no,
                        "text": text,
                        "tokens": rough_tokens(text),
                    }
                )
        else:
            text = redact(raw).strip()
            if rough_tokens(text) >= 12:
                records.append(
                    {
                        "id": f"convo_{content_hash(str(path) + text)[:16]}",
                        "source_path": str(path),
                        "line": 1,
                        "text": text[:max_chars],
                        "tokens": rough_tokens(text[:max_chars]),
                    }
                )
        if len(records) >= max_records:
            return records
    return records


def write_conversation_stash(records: list[dict[str, Any]], stash_dir: Path) -> dict[str, Any]:
    if stash_dir.exists():
        shutil.rmtree(stash_dir)
    stash_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = stash_dir / "real_conversation_context.jsonl"
    md_path = stash_dir / "real_conversation_context.md"
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    lines = [
        "# Redacted Real Conversation Context Stash",
        "",
        f"Created: `{utc_now()}`",
        "",
        "This file is generated from local conversation logs with secret/path redaction. It lives under `out/` and should not be committed.",
        "",
    ]
    for idx, record in enumerate(records, start=1):
        lines.extend(
            [
                f"## Conversation Record {idx}: {record['id']}",
                "",
                f"- Source: `{record['source_path']}`",
                f"- Line: `{record['line']}`",
                f"- Tokens: `{record['tokens']}`",
                "",
                record["text"].replace("\r\n", "\n"),
                "",
            ]
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "stash_dir": str(stash_dir),
        "jsonl": str(jsonl_path),
        "markdown": str(md_path),
        "records": len(records),
        "tokens": sum(record["tokens"] for record in records),
    }


def benchmark_queries() -> list[dict[str, Any]]:
    return [
        {"query": "What did CP28 show about final answer packet formats?", "expect_any": ["cp28", "final-answer"], "should_select": True},
        {"query": "What MCP tools does ivy-context-memory expose?", "expect_any": ["cp33", "mcp"], "should_select": True},
        {"query": "What is the latest CP42 rebuild policy versus stale memory?", "expect_any": ["unchanged file chunks", "stale policy"], "should_select": True},
        {"query": "What is today's Bitcoin price?", "expect_any": [], "should_select": False},
        {"query": "What do real conversations ask us to build for IVY memory?", "expect_any": ["memory", "context", "plugin", "loop"], "should_select": True},
    ]


def evaluate_policy(plugin: Any, store: Path, *, max_prefilter_items: int) -> dict[str, Any]:
    rows = []
    for spec in benchmark_queries():
        started = time.perf_counter()
        result = plugin.query_store(store, query=spec["query"], max_prefilter_items=max_prefilter_items)
        wall_ms = round((time.perf_counter() - started) * 1000, 3)
        selected_ids = result.get("selected_ids", [])
        haystack = " ".join([" ".join(selected_ids), result.get("packet_text", "")]).lower()
        if spec["should_select"]:
            passed = bool(selected_ids) and any(term in haystack for term in spec["expect_any"])
        else:
            passed = not selected_ids
        rows.append(
            {
                "query": spec["query"],
                "passed": passed,
                "wall_ms": wall_ms,
                "router_latency_ms": result.get("latency_ms"),
                "packet_mode": result.get("packet_mode"),
                "selected_ids": selected_ids,
            }
        )
    return {
        "max_prefilter_items": max_prefilter_items,
        "passed": sum(1 for row in rows if row["passed"]),
        "total": len(rows),
        "avg_wall_ms": round(sum(row["wall_ms"] for row in rows) / max(1, len(rows)), 3),
        "avg_router_latency_ms": round(sum(float(row["router_latency_ms"] or 0.0) for row in rows) / max(1, len(rows)), 3),
        "rows": rows,
    }


def write_policy(store: Path, policy: dict[str, Any]) -> Path:
    path = store / "policy" / "autoresearch_policy.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def capacity_rating(*, actual_tokens: int, target_tokens: int, query_count: int, avg_router_latency_ms: float, passed: int, total: int) -> dict[str, Any]:
    shard_tokens = 4096
    projected_shards = math.ceil(target_tokens / shard_tokens)
    effective_pass = passed == total
    latency_pass = avg_router_latency_ms <= 25.0
    return {
        "target_tokens": target_tokens,
        "actual_stashed_tokens": actual_tokens,
        "rating_mode": "virtual_sharded_projection",
        "projected_shards_at_4096_tokens": projected_shards,
        "queries_tested": query_count,
        "passed_expectations": passed,
        "total_expectations": total,
        "avg_router_latency_ms": avg_router_latency_ms,
        "rated": bool(effective_pass and latency_pass),
        "caveat": (
            "This is a capacity rating for the sharded memory architecture, not a claim that a frontier model received "
            "10M tokens in one prompt. Raw conversation context stays outside the model and is compiled into small ACCA packets."
        ),
    }


def run_loop(args: argparse.Namespace) -> dict[str, Any]:
    plugin = load_module(PLUGIN_SCRIPT, "ivy_context_memory_autoresearch")
    benchmark = load_module(BENCHMARK_SCRIPT, "ivy_context_memory_plugin_benchmark")
    out_dir = args.out_dir.resolve()
    store = args.store.resolve()
    if args.reset and out_dir.exists():
        if ROOT not in out_dir.parents:
            raise RuntimeError(f"refusing to reset output outside MoME-MoCE-Exp: {out_dir}")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    roots = [path.resolve() for path in args.conversation_root]
    records = extract_conversation_records(roots, max_files=args.max_conversation_files, max_records=args.max_records, max_chars=args.max_record_chars)
    stash = write_conversation_stash(records, out_dir / "stash")

    plugin.init_store(store)
    if records:
        plugin.add_source(store, Path(stash["stash_dir"]), build=False)
    plugin.add_source(store, ROOT, build=False)
    plugin.remember(
        store,
        text="Autoresearch loop stashed redacted real conversation context and uses benchmark-driven policy tuning for IVY memory.",
        source_path="root/notes/autoresearch_loop.md",
        tags=["autoresearch", "loop", "real-convos"],
        authority="medium",
    )

    iteration_rows = []
    policy_candidates = [32, 64, 128, 192]
    best_policy = None
    for iteration in range(1, args.iterations + 1):
        candidates = [evaluate_policy(plugin, store, max_prefilter_items=value) for value in policy_candidates]
        candidates.sort(key=lambda row: (row["passed"] == row["total"], -row["avg_router_latency_ms"], -row["avg_wall_ms"]), reverse=True)
        best = candidates[0]
        best_policy = {
            "schema_version": "ivy_context_memory.autoresearch_policy.v0.1",
            "updated_at": utc_now(),
            "iteration": iteration,
            "max_prefilter_items": best["max_prefilter_items"],
            "objective": "minimum latency with all benchmark expectations passing",
            "metrics": {
                "passed": best["passed"],
                "total": best["total"],
                "avg_wall_ms": best["avg_wall_ms"],
                "avg_router_latency_ms": best["avg_router_latency_ms"],
            },
        }
        policy_path = write_policy(store, best_policy)
        iteration_rows.append({"iteration": iteration, "candidates": candidates, "selected_policy": best_policy, "policy_path": str(policy_path)})
        if best["passed"] == best["total"] and best["avg_router_latency_ms"] <= args.router_latency_gate_ms:
            break

    assert best_policy is not None
    bench_result = benchmark.run_benchmark(store, source_root=ROOT, reset=False)
    rating = capacity_rating(
        actual_tokens=stash["tokens"],
        target_tokens=args.target_token_rating,
        query_count=bench_result["summary"]["query_count"],
        avg_router_latency_ms=float(bench_result["summary"]["avg_router_latency_ms"]),
        passed=int(bench_result["summary"]["passed_expectations"]),
        total=int(bench_result["summary"]["query_count"]),
    )
    result = {
        "schema_version": "ivy_context_memory.autoresearch_loop.v0.1",
        "created_at": utc_now(),
        "store": str(store),
        "out_dir": str(out_dir),
        "conversation_roots": [str(path) for path in roots],
        "stash": stash,
        "iterations": iteration_rows,
        "selected_policy": best_policy,
        "plugin_benchmark_summary": bench_result["summary"],
        "capacity_rating": rating,
    }
    (out_dir / "autoresearch_loop_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown_report(result, out_dir / "autoresearch_loop_report.md")
    if args.scoreboard_path:
        write_scoreboard(result, args.scoreboard_path.resolve())
    return result


def write_markdown_report(result: dict[str, Any], path: Path) -> None:
    rating = result["capacity_rating"]
    policy = result["selected_policy"]
    lines = [
        "# IVY Context Memory Autoresearch Loop Report",
        "",
        f"- Created: `{result['created_at']}`",
        f"- Store: `{result['store']}`",
        f"- Stashed records: `{result['stash']['records']}`",
        f"- Stashed tokens: `{result['stash']['tokens']}`",
        f"- Selected max prefilter items: `{policy['max_prefilter_items']}`",
        f"- Policy avg router latency: `{policy['metrics']['avg_router_latency_ms']} ms`",
        f"- Plugin benchmark: `{result['plugin_benchmark_summary']['passed_expectations']} / {result['plugin_benchmark_summary']['query_count']}`",
        f"- Capacity target: `{rating['target_tokens']}` tokens",
        f"- Capacity rated: `{rating['rated']}`",
        "",
        "## Capacity Rating",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Target tokens | `{rating['target_tokens']}` |",
        f"| Actual stashed tokens | `{rating['actual_stashed_tokens']}` |",
        f"| Projected 4096-token shards | `{rating['projected_shards_at_4096_tokens']}` |",
        f"| Avg router latency | `{rating['avg_router_latency_ms']} ms` |",
        f"| Expectations | `{rating['passed_expectations']} / {rating['total_expectations']}` |",
        "",
        "## Caveat",
        "",
        rating["caveat"],
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_scoreboard(result: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rating = result["capacity_rating"]
    policy = result["selected_policy"]
    lines = [
        "# IVY Autoresearch Loop Scoreboard",
        "",
        f"Last updated: `{result['created_at']}`",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Stashed real-conversation records | `{result['stash']['records']}` |",
        f"| Stashed real-conversation tokens | `{result['stash']['tokens']}` |",
        f"| Selected max prefilter items | `{policy['max_prefilter_items']}` |",
        f"| Policy avg router latency | `{policy['metrics']['avg_router_latency_ms']} ms` |",
        f"| Plugin benchmark | `{result['plugin_benchmark_summary']['passed_expectations']} / {result['plugin_benchmark_summary']['query_count']}` |",
        f"| Capacity target | `{rating['target_tokens']}` |",
        f"| Capacity rated | `{rating['rated']}` |",
        "",
        "## Notes",
        "",
        "- Generated by `scripts/run_context_memory_autoresearch_loop.py`.",
        "- Raw/redacted conversation stash remains under `out/autoresearch_loop/` and is not committed.",
        "- The 10M-token rating is a sharded-memory capacity rating, not a single-prompt context-window claim.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a bounded Karpathy-style autoresearch loop for IVY context memory.")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--conversation-root", type=Path, action="append", default=None)
    parser.add_argument("--max-conversation-files", type=int, default=12)
    parser.add_argument("--max-records", type=int, default=80)
    parser.add_argument("--max-record-chars", type=int, default=2400)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--target-token-rating", type=int, default=10_000_000)
    parser.add_argument("--router-latency-gate-ms", type=float, default=25.0)
    parser.add_argument("--scoreboard-path", type=Path, default=DEFAULT_SCOREBOARD)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    if args.conversation_root is None:
        args.conversation_root = [DEFAULT_CONVERSATION_ROOT]

    result = run_loop(args)
    print(
        json.dumps(
            {
                "ok": True,
                "result": str(Path(result["out_dir"]) / "autoresearch_loop_result.json"),
                "report": str(Path(result["out_dir"]) / "autoresearch_loop_report.md"),
                "scoreboard": str(args.scoreboard_path),
                "selected_policy": result["selected_policy"],
                "capacity_rating": result["capacity_rating"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
