from __future__ import annotations

import argparse
import importlib.util
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
PLUGIN_SCRIPT = REPO_ROOT / "plugins" / "ivy-context-memory" / "scripts" / "ivy_context_memory.py"
DEFAULT_STORE = ROOT / "out" / "autoresearch_loop" / "memory_store"
DEFAULT_CASES = ROOT / "docs" / "AUTORESEARCH_MINED_EVAL_CASES.json"
DEFAULT_OUT = ROOT / "docs" / "AUTORESEARCH_MINED_POLICY_EVAL.md"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_plugin() -> Any:
    spec = importlib.util.spec_from_file_location("ivy_context_memory_mined_eval", PLUGIN_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load plugin: {PLUGIN_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


def evaluate(store: Path, cases: list[dict[str, Any]], *, max_prefilter_items: int) -> dict[str, Any]:
    plugin = load_plugin()
    rows = []
    for case in cases:
        started = time.perf_counter()
        result = plugin.query_store(store, query=case["query"], max_prefilter_items=max_prefilter_items)
        wall_ms = round((time.perf_counter() - started) * 1000, 3)
        selected_ids = list(result.get("selected_ids", []))
        required = set(case.get("required_source_ids", []))
        must_abstain = bool(case.get("must_abstain", False))
        packet_text = str(result.get("packet_text", "")).lower()
        expected_terms = [str(term).lower() for term in case.get("expected_terms", [])]
        term_match = bool(expected_terms) and all(term in packet_text for term in expected_terms)
        if must_abstain:
            passed = not selected_ids
        else:
            passed = required.issubset(set(selected_ids)) or term_match
        rows.append(
            {
                "case_id": case["id"],
                "query": case["query"],
                "passed": bool(passed),
                "required_source_ids": sorted(required),
                "selected_ids": selected_ids,
                "packet_mode": result.get("packet_mode"),
                "wall_ms": wall_ms,
                "router_latency_ms": result.get("latency_ms"),
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


def write_report(results: list[dict[str, Any]], out: Path) -> dict[str, Any]:
    ranked = sorted(results, key=lambda row: (row["passed"], -row["avg_router_latency_ms"], -row["avg_wall_ms"]), reverse=True)
    winner = ranked[0] if ranked else {}
    lines = [
        "# Autoresearch Mined Case Policy Eval",
        "",
        f"Created: `{utc_now()}`",
        "",
        "| max_prefilter_items | Passed | Avg wall ms | Avg router ms |",
        "|---:|---:|---:|---:|",
    ]
    for row in ranked:
        lines.append(f"| {row['max_prefilter_items']} | {row['passed']} / {row['total']} | {row['avg_wall_ms']} | {row['avg_router_latency_ms']} |")
    lines.extend(["", "## Winner", "", f"`max_prefilter_items = {winner.get('max_prefilter_items')}`", "", "## Rows", ""])
    for row in ranked:
        lines.append(f"### Policy {row['max_prefilter_items']}")
        lines.append("")
        lines.append("| Case | Pass | Mode | Required | Selected | Router ms |")
        lines.append("|---|---|---|---|---|---:|")
        for item in row["rows"]:
            lines.append(
                f"| {item['case_id']} | {item['passed']} | {item['packet_mode']} | "
                f"`{', '.join(item['required_source_ids']) or 'none'}` | `{', '.join(item['selected_ids']) or 'none'}` | {item['router_latency_ms']} |"
            )
        lines.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    return {"winner": winner, "report": str(out)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate prefilter policies against autoresearch-mined hard cases.")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--candidate", type=int, action="append", default=[16, 32, 64, 128])
    args = parser.parse_args()

    cases = load_cases(args.cases)
    results = [evaluate(args.store.resolve(), cases, max_prefilter_items=value) for value in args.candidate]
    report = write_report(results, args.out)
    print(json.dumps({"ok": True, "winner": report["winner"], "report": report["report"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
