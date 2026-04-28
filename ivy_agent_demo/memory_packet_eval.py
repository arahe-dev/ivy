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


def canonical_kind(kind: str | None) -> str:
    mapping = {
        "json_contamination_warning": "json_contamination_warning",
        "benchmark_result": "benchmark_result",
        "policy_warning": "policy_warning",
        "validation_warning": "validation_failure",
        "failure_warning": "validation_failure",
        "successful_pattern": "workflow_success",
    }
    return mapping.get(kind or "unknown", kind or "unknown")


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
        metrics = to_dict(packet.metrics)
        kind_counts: dict[str, int] = {}
        for line in packet.packet_lines:
            kind = canonical_kind(line.kind)
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
        grouping_ok = True
        for kind, max_lines in (case.get("expected_max_lines_for_kind") or {}).items():
            grouping_ok = grouping_ok and kind_counts.get(kind, 0) <= int(max_lines)
        if "expected_min_evidence_count" in case:
            grouping_ok = grouping_ok and metrics["evidence_count"] >= int(case["expected_min_evidence_count"])
        if "expected_duplicate_group_count_at_least" in case:
            grouping_ok = grouping_ok and metrics["duplicate_group_count"] >= int(case["expected_duplicate_group_count_at_least"])
        if "expected_max_packet_lines" in case:
            grouping_ok = grouping_ok and metrics["packet_line_count"] <= int(case["expected_max_packet_lines"])
        diversity_ok = True
        if "expected_min_unique_kind_count" in case:
            diversity_ok = diversity_ok and metrics["unique_kind_count"] >= int(case["expected_min_unique_kind_count"])
        if "expected_max_packet_chars" in case:
            diversity_ok = diversity_ok and metrics["packet_chars"] <= int(case["expected_max_packet_chars"])
        for term in case.get("expected_warning_terms") or []:
            diversity_ok = diversity_ok and norm(term) in blob
        forbidden_ok = not any(norm(term) in blob for term in case.get("forbidden_packet_terms") or [])
        rows.append(
            {
                "case_id": case["id"],
                "query": case["query"],
                "policy": policy,
                "packet_term_hit": term_hit,
                "provenance_ok": provenance_ok,
                "expected_expert_hit": expert_hit,
                "expected_composer_hit": composer_hit,
                "grouping_quality_ok": grouping_ok,
                "diversity_quality_ok": diversity_ok and forbidden_ok,
                "latency_ms": packet.metrics.latency_ms,
                "packet_chars": packet.metrics.packet_chars,
                "evidence_count": packet.metrics.evidence_count,
                "unique_kind_count": packet.metrics.unique_kind_count,
                "duplicate_group_count": packet.metrics.duplicate_group_count,
                "compression_ratio": packet.metrics.compression_ratio,
                "chars_per_evidence": packet.metrics.chars_per_evidence,
                "too_large_packet": bool(case.get("max_packet_chars") and packet.metrics.packet_chars > int(case["max_packet_chars"])),
                "repetitive_packet": packet.metrics.raw_candidate_count > 1 and packet.metrics.duplicate_group_count == 0 and packet.metrics.packet_line_count >= packet.metrics.raw_candidate_count,
                "overclaim_warning": not forbidden_ok,
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
        "grouping_quality_rate": rate(rows, "grouping_quality_ok"),
        "diversity_quality_rate": rate(rows, "diversity_quality_ok"),
        "average_latency_ms": round(sum(float(r["latency_ms"]) for r in rows) / len(rows), 3) if rows else 0.0,
        "average_packet_chars": round(sum(int(r["packet_chars"]) for r in rows) / len(rows), 3) if rows else 0.0,
        "average_chars_per_evidence": round(sum(float(r["chars_per_evidence"]) for r in rows) / len(rows), 3) if rows else 0.0,
        "average_compression_ratio": round(sum(float(r["compression_ratio"]) for r in rows) / len(rows), 4) if rows else 0.0,
        "too_large_packet_count": sum(1 for r in rows if r["too_large_packet"]),
        "repetitive_packet_count": sum(1 for r in rows if r["repetitive_packet"]),
        "overclaim_warning_count": sum(1 for r in rows if r["overclaim_warning"]),
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
    fields = ["eval_run_id", "db_path", "cases_path", "packet_term_hit_rate", "provenance_line_rate", "expected_expert_hit_rate", "expected_composer_hit_rate", "grouping_quality_rate", "diversity_quality_rate", "average_latency_ms", "average_packet_chars", "average_chars_per_evidence", "average_compression_ratio"]
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
    metrics = ["packet_term_hit_rate", "provenance_line_rate", "expected_expert_hit_rate", "expected_composer_hit_rate", "grouping_quality_rate", "diversity_quality_rate", "average_latency_ms", "average_chars_per_evidence", "average_compression_ratio"]
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
    fields = ["case_id", "query", "policy", "packet_term_hit", "provenance_ok", "expected_expert_hit", "expected_composer_hit", "grouping_quality_ok", "diversity_quality_ok", "latency_ms", "packet_chars", "evidence_count", "unique_kind_count", "duplicate_group_count", "compression_ratio", "chars_per_evidence", "too_large_packet", "repetitive_packet", "overclaim_warning", "packet_text_short"]
    with (out_dir / "packet_eval_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fields})
    lines = ["# Memory Packet Eval", "", "## Summary", ""]
    for key, value in summary.items():
        lines.append(f"- {key}: `{value}`")
    lines += ["", "## Cases", "", "| case | policy | terms | provenance | grouping | diversity | evidence | compression | chars |", "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in rows:
        lines.append(f"| {row['case_id']} | {row['policy']} | {row['packet_term_hit']} | {row['provenance_ok']} | {row['grouping_quality_ok']} | {row['diversity_quality_ok']} | {row['evidence_count']} | {row['compression_ratio']} | {row['packet_chars']} |")
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
