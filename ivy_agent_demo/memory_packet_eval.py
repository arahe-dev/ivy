from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .memory_packet import to_dict
from .memory_packet_cli import run_preview
from .memory_store import DEFAULT_DB_PATH


DEFAULT_OUTPUT_ROOT = Path("C:/ivy/runs/memory_packet_eval")


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    cases = data.get("cases") if isinstance(data, dict) else data
    if not isinstance(cases, list):
        raise ValueError("packet eval cases must be a list or object with cases")
    for case in cases:
        for key in ("id", "query", "policy", "expected_packet_terms"):
            if key not in case:
                raise ValueError(f"case missing {key}: {case}")
    return cases


def norm(text: Any) -> str:
    return str(text or "").lower()


def rate(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return round(sum(1 for r in rows if r.get(key)) / len(rows), 4)


def evaluate(cases: list[dict[str, Any]], db: str, top_k: int | None, max_packet_chars: int | None, policies: list[str] | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = []
    for case in cases:
        policy = (policies[0] if policies else None) or case.get("policy")
        if policies and case.get("policy") not in policies:
            policy = case.get("policy")
        packet, _ = run_preview(case["query"], db, policy, top_k, max_packet_chars or case.get("max_packet_chars"), save=False)
        blob = norm(packet.packet_text)
        terms = case.get("expected_packet_terms") or []
        term_hit = all(norm(term) in blob for term in terms)
        experts = case.get("expected_experts") or []
        composers = case.get("expected_composers") or []
        expert_hit = all(expert in packet.routing_decision.selected_experts for expert in experts)
        composer_hit = all(composer in packet.routing_decision.selected_composers for composer in composers)
        provenance_ok = (not case.get("must_have_provenance", True)) or packet.metrics.provenance_line_rate > 0
        rows.append(
            {
                "case_id": case["id"],
                "query": case["query"],
                "policy": policy,
                "packet_term_hit": term_hit,
                "provenance_ok": provenance_ok,
                "expected_expert_hit": expert_hit,
                "expected_composer_hit": composer_hit,
                "latency_ms": packet.metrics.latency_ms,
                "packet_chars": packet.metrics.packet_chars,
                "too_large_packet": bool(case.get("max_packet_chars") and packet.metrics.packet_chars > int(case["max_packet_chars"])),
                "packet_text_short": packet.packet_text[:240].replace("\n", " "),
                "packet": to_dict(packet),
                "notes": case.get("notes", ""),
            }
        )
    summary = {
        "total_cases": len(rows),
        "evaluated_cases": len(rows),
        "packet_term_hit_rate": rate(rows, "packet_term_hit"),
        "provenance_line_rate": round(sum(r["packet"]["metrics"]["provenance_line_rate"] for r in rows) / len(rows), 4) if rows else 0.0,
        "expected_expert_hit_rate": rate(rows, "expected_expert_hit"),
        "expected_composer_hit_rate": rate(rows, "expected_composer_hit"),
        "average_latency_ms": round(sum(float(r["latency_ms"]) for r in rows) / len(rows), 3) if rows else 0.0,
        "average_packet_chars": round(sum(int(r["packet_chars"]) for r in rows) / len(rows), 3) if rows else 0.0,
        "too_large_packet_count": sum(1 for r in rows if r["too_large_packet"]),
    }
    return rows, summary


def history(root: Path) -> list[dict[str, Any]]:
    path = root / "history.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def append_history(root: Path, row: dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    with (root / "history.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    fields = ["eval_run_id", "db_path", "cases_path", "packet_term_hit_rate", "provenance_line_rate", "expected_expert_hit_rate", "expected_composer_hit_rate", "average_latency_ms", "average_packet_chars"]
    csv_path = root / "history.csv"
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k) for k in fields})


def compare(summary: dict[str, Any], rows: list[dict[str, Any]], previous: list[dict[str, Any]]) -> dict[str, Any]:
    if not previous:
        return {"available": False, "notes": "no previous run available"}
    prev = previous[-1]
    prev_path = Path(prev.get("output_dir", "")) / "packet_eval_results.json"
    prev_rows = []
    if prev_path.exists():
        prev_rows = json.loads(prev_path.read_text(encoding="utf-8")).get("per_case_results", [])
    prev_by_id = {r["case_id"]: r for r in prev_rows}
    cur_by_id = {r["case_id"]: r for r in rows}
    improved, regressed = [], []
    for case_id in set(prev_by_id) & set(cur_by_id):
        old = bool(prev_by_id[case_id].get("packet_term_hit"))
        new = bool(cur_by_id[case_id].get("packet_term_hit"))
        if new and not old:
            improved.append(case_id)
        if old and not new:
            regressed.append(case_id)
    metrics = ["packet_term_hit_rate", "provenance_line_rate", "expected_expert_hit_rate", "expected_composer_hit_rate", "average_latency_ms"]
    return {
        "available": True,
        "previous_eval_run_id": prev.get("eval_run_id"),
        "metric_deltas": {m: round(float(summary.get(m, 0)) - float(prev.get(m, 0)), 4) for m in metrics},
        "improved_cases": sorted(improved),
        "regressed_cases": sorted(regressed),
    }


def write_outputs(out_dir: Path, config: dict[str, Any], rows: list[dict[str, Any]], summary: dict[str, Any], comparison: dict[str, Any] | None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "packet_eval_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    payload = {"config": config, "summary": summary, "per_case_results": rows, "comparison_vs_previous": comparison}
    (out_dir / "packet_eval_results.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    fields = ["case_id", "query", "policy", "packet_term_hit", "provenance_ok", "expected_expert_hit", "expected_composer_hit", "latency_ms", "packet_chars", "too_large_packet", "packet_text_short"]
    with (out_dir / "packet_eval_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fields})
    lines = ["# Memory Packet Eval", "", "## Summary", ""]
    for key, value in summary.items():
        lines.append(f"- {key}: `{value}`")
    lines += ["", "## Cases", "", "| case | policy | terms | provenance | experts | composers | chars |", "|---|---|---:|---:|---:|---:|---:|"]
    for row in rows:
        lines.append(f"| {row['case_id']} | {row['policy']} | {row['packet_term_hit']} | {row['provenance_ok']} | {row['expected_expert_hit']} | {row['expected_composer_hit']} | {row['packet_chars']} |")
    if comparison:
        lines += ["", "## Comparison", "", f"- {comparison}"]
    (out_dir / "packet_eval_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate IVY read-only memory packet previews.")
    parser.add_argument("--cases", required=True)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--policies", nargs="*")
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--max-packet-chars", type=int)
    parser.add_argument("--compare-latest", action="store_true")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    args = parser.parse_args()
    cases = load_cases(args.cases)
    root = Path(args.output_root)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    out_dir = root / run_id
    prior = history(root) if args.compare_latest else []
    rows, summary = evaluate(cases, args.db, args.top_k, args.max_packet_chars, args.policies)
    config = {"eval_run_id": run_id, "db_path": args.db, "cases_path": args.cases, "policies": args.policies, "top_k": args.top_k, "max_packet_chars": args.max_packet_chars, "output_dir": str(out_dir)}
    comparison = compare(summary, rows, prior) if args.compare_latest else None
    write_outputs(out_dir, config, rows, summary, comparison)
    append_history(root, {**config, **summary})
    print(f"packet eval run: {out_dir}")
    print(f"packet_term_hit_rate: {summary['packet_term_hit_rate']}")
    print(f"provenance_line_rate: {summary['provenance_line_rate']}")
    if comparison:
        print(comparison.get("notes") or f"compared with {comparison.get('previous_eval_run_id')}")


if __name__ == "__main__":
    main()
