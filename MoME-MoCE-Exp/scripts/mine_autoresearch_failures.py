from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULT = ROOT / "out" / "autoresearch_loop" / "autoresearch_loop_result.json"
DEFAULT_OUT = ROOT / "docs" / "AUTORESEARCH_MINED_EVAL_CASES.json"
DEFAULT_REPORT = ROOT / "docs" / "AUTORESEARCH_MINED_FAILURES.md"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_ids(ids: list[str]) -> tuple[str, ...]:
    return tuple(str(item) for item in ids)


def mine_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    mined: list[dict[str, Any]] = []
    iterations = result.get("iterations", [])
    for iteration in iterations:
        candidates = iteration.get("candidates", [])
        if not candidates:
            continue
        by_query: dict[str, list[dict[str, Any]]] = {}
        for candidate in candidates:
            for row in candidate.get("rows", []):
                enriched = dict(row)
                enriched["max_prefilter_items"] = candidate.get("max_prefilter_items")
                by_query.setdefault(str(row.get("query", "")), []).append(enriched)
        for query, rows in by_query.items():
            failed = [row for row in rows if not row.get("passed", False)]
            selected_sets = {normalize_ids(row.get("selected_ids", [])) for row in rows}
            latencies = [float(row.get("router_latency_ms") or 0.0) for row in rows]
            latency_spread = max(latencies) - min(latencies) if latencies else 0.0
            modes = {str(row.get("packet_mode")) for row in rows}
            reason = None
            severity = "info"
            if failed:
                reason = "failed_expectation"
                severity = "high"
            elif len(selected_sets) > 1:
                reason = "selection_changes_with_prefilter_depth"
                severity = "medium"
            elif latency_spread >= 5.0:
                reason = "latency_sensitive_to_prefilter_depth"
                severity = "medium"
            elif len(modes) > 1:
                reason = "packet_mode_changes_with_prefilter_depth"
                severity = "medium"
            if reason is None:
                continue
            fastest = sorted(rows, key=lambda row: float(row.get("router_latency_ms") or 0.0))[0]
            deepest = sorted(rows, key=lambda row: int(row.get("max_prefilter_items") or 0))[-1]
            mined.append(
                {
                    "query": query,
                    "reason": reason,
                    "severity": severity,
                    "fastest_policy": {
                        "max_prefilter_items": fastest.get("max_prefilter_items"),
                        "router_latency_ms": fastest.get("router_latency_ms"),
                        "selected_ids": fastest.get("selected_ids", []),
                        "packet_mode": fastest.get("packet_mode"),
                    },
                    "deepest_policy": {
                        "max_prefilter_items": deepest.get("max_prefilter_items"),
                        "router_latency_ms": deepest.get("router_latency_ms"),
                        "selected_ids": deepest.get("selected_ids", []),
                        "packet_mode": deepest.get("packet_mode"),
                    },
                    "latency_spread_ms": round(latency_spread, 3),
                    "selected_set_count": len(selected_sets),
                }
            )
    return mined


def to_eval_cases(mined: list[dict[str, Any]]) -> dict[str, Any]:
    cases = []
    for idx, row in enumerate(mined, start=1):
        fastest_ids = list(row["fastest_policy"].get("selected_ids", []))
        expected_terms = []
        q = row["query"].lower()
        if "cp28" in q:
            expected_terms = ["cp28", "final-answer"]
        elif "mcp tools" in q:
            expected_terms = ["mcp", "ivy_memory_query"]
        elif "cp42" in q:
            expected_terms = ["cp42", "stale"]
        elif "real conversations" in q:
            expected_terms = ["memory", "context"]
        cases.append(
            {
                "id": f"autoresearch_mined_{idx:03d}",
                "category": "autoresearch_failure_mining",
                "query": row["query"],
                "should_retrieve": bool(fastest_ids),
                "retrieval_ratio_target": [0.0, 0.05],
                "required_source_ids": fastest_ids[:2],
                "forbidden_source_ids": [],
                "expected_terms": expected_terms,
                "forbidden_terms": [],
                "must_abstain": not bool(fastest_ids),
                "requires_conflict_resolution": row["fastest_policy"].get("packet_mode") == "contradiction_aware",
                "requires_safety_priority": False,
                "provenance_required": bool(fastest_ids),
                "max_evidence_items": max(0, len(fastest_ids[:2])),
                "answer_contract": "abstain" if not fastest_ids else "answer",
                "notes": (
                    f"Mined from autoresearch loop because {row['reason']}; severity={row['severity']}; "
                    f"latency_spread_ms={row['latency_spread_ms']}."
                ),
            }
        )
    return {
        "schema_version": "context_stress_eval_cases.v0.1",
        "created_at": utc_now(),
        "generator": "scripts/mine_autoresearch_failures.py",
        "cases": cases,
    }


def write_report(mined: list[dict[str, Any]], path: Path) -> None:
    lines = [
        "# Autoresearch Mined Failures And Hard Cases",
        "",
        f"Created: `{utc_now()}`",
        "",
        f"Mined cases: `{len(mined)}`",
        "",
        "| Query | Reason | Severity | Fastest policy | Deepest policy | Latency spread ms |",
        "|---|---|---|---|---|---:|",
    ]
    for row in mined:
        lines.append(
            f"| {row['query']} | {row['reason']} | {row['severity']} | "
            f"`{row['fastest_policy']['max_prefilter_items']}` -> `{', '.join(row['fastest_policy']['selected_ids']) or 'none'}` | "
            f"`{row['deepest_policy']['max_prefilter_items']}` -> `{', '.join(row['deepest_policy']['selected_ids']) or 'none'}` | "
            f"{row['latency_spread_ms']} |"
        )
    lines.extend(
        [
            "",
            "## Use",
            "",
            "These are not all failures. They are failure-like or hard cases mined from policy sensitivity, selection drift, packet-mode drift, or outright expectation misses.",
            "Future reranker and router changes should preserve or improve these cases.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Mine autoresearch loop failures and hard cases into eval cases.")
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    result = json.loads(args.result.read_text(encoding="utf-8"))
    mined = mine_rows(result)
    payload = to_eval_cases(mined)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(mined, args.report)
    print(json.dumps({"ok": True, "mined": len(mined), "out": str(args.out), "report": str(args.report)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
