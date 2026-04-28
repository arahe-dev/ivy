from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .memory_packet import to_dict
from .memory_store import DEFAULT_DB_PATH
from .mome_packet import build_mome_packet


DEFAULT_OUTPUT_ROOT = Path("C:/ivy/runs/mome_eval")


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    cases = data.get("cases") if isinstance(data, dict) else data
    if not isinstance(cases, list):
        raise ValueError("MoME eval cases must be a list or object with cases")
    for case in cases:
        for key in ("id", "query", "expected_packet_terms"):
            if key not in case:
                raise ValueError(f"case missing {key}: {case}")
    return cases


def norm(value: Any) -> str:
    return str(value or "").lower()


def rate(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return round(sum(1 for row in rows if row.get(key)) / len(rows), 4)


def detect_overclaim(packet_text: str, forbidden_terms: list[str]) -> bool:
    blob = norm(packet_text)
    strong = ["guaranteed", "definitely", "always", "must override", "confirmed absolute-path failure"]
    return any(norm(term) in blob for term in forbidden_terms) or any(term in blob for term in strong)


def detect_overcompression(packet: Any) -> bool:
    metrics = packet.metrics
    mixed_families = len({candidate.source_family for candidate in packet.candidates_considered}) > 2
    return bool(metrics.raw_candidate_count >= 5 and metrics.packet_line_count <= 1 and mixed_families)


def evaluate(cases: list[dict[str, Any]], args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = []
    for case in cases:
        policies = args.policies or case.get("policies_to_test") or ["mome_auto"]
        for policy in policies:
            packet, metadata = build_mome_packet(
                query=case["query"],
                db_path=args.db,
                policy_name=policy,
                top_k=args.top_k,
                max_packet_chars=args.max_packet_chars or case.get("max_packet_chars"),
            )
            blob = norm(packet.packet_text)
            expected_terms = case.get("expected_packet_terms") or []
            expected_experts = case.get("expected_experts") or []
            expected_families = case.get("expected_source_families") or []
            caution_terms = case.get("expected_caution_terms") or []
            packet_term_hit = all(norm(term) in blob for term in expected_terms)
            expert_selection_hit = all(expert in metadata.get("experts_used", []) for expert in expected_experts)
            families_present = set(metadata.get("source_family_counts", {}).keys())
            source_family_hit = any(family in families_present for family in expected_families) if expected_families else True
            provenance_ok = (not case.get("must_have_provenance", True)) or packet.metrics.provenance_line_rate > 0
            caution_hit = all(norm(term) in blob for term in caution_terms) if caution_terms else True
            overclaim = detect_overclaim(packet.packet_text, case.get("forbidden_packet_terms") or [])
            overcompression = detect_overcompression(packet)
            rows.append({
                "case_id": case["id"],
                "category": case.get("category", ""),
                "query": case["query"],
                "policy": policy,
                "packet_term_hit": packet_term_hit,
                "expert_selection_hit": expert_selection_hit,
                "source_family_hit": source_family_hit,
                "provenance_ok": provenance_ok,
                "caution_hit": caution_hit,
                "empty_packet": packet.metrics.packet_line_count == 0,
                "overclaim_risk": overclaim,
                "overcompression_risk": overcompression,
                "latency_ms": packet.metrics.latency_ms,
                "packet_chars": packet.metrics.packet_chars,
                "packet_line_count": packet.metrics.packet_line_count,
                "provenance_rate": packet.metrics.provenance_line_rate,
                "expert_contribution_counts": metadata.get("expert_contribution_counts", {}),
                "source_family_counts": metadata.get("source_family_counts", {}),
                "packet_text_short": packet.packet_text[:260].replace("\n", " "),
                "packet": to_dict(packet),
                "metadata": metadata,
                "notes": case.get("notes", ""),
            })
    summary = {
        "total_results": len(rows),
        "packet_term_hit_rate": rate(rows, "packet_term_hit"),
        "expert_selection_hit_rate": rate(rows, "expert_selection_hit"),
        "source_family_hit_rate": rate(rows, "source_family_hit"),
        "provenance_ok_rate": rate(rows, "provenance_ok"),
        "caution_hit_rate": rate(rows, "caution_hit"),
        "empty_packet_count": sum(1 for row in rows if row["empty_packet"]),
        "overclaim_risk_count": sum(1 for row in rows if row["overclaim_risk"]),
        "overcompression_risk_count": sum(1 for row in rows if row["overcompression_risk"]),
        "average_latency_ms": round(sum(float(row["latency_ms"]) for row in rows) / len(rows), 3) if rows else 0.0,
        "average_packet_chars": round(sum(int(row["packet_chars"]) for row in rows) / len(rows), 3) if rows else 0.0,
    }
    return rows, summary


def load_history(root: Path) -> list[dict[str, Any]]:
    path = root / "history.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_history(root: Path, row: dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    with (root / "history.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    fields = ["eval_run_id", "cases_path", "db_path", "packet_term_hit_rate", "expert_selection_hit_rate", "source_family_hit_rate", "provenance_ok_rate", "caution_hit_rate", "empty_packet_count", "overclaim_risk_count", "overcompression_risk_count", "average_latency_ms", "average_packet_chars", "output_dir"]
    csv_path = root / "history.csv"
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow({key: row.get(key) for key in fields})


def compare_latest(summary: dict[str, Any], previous: list[dict[str, Any]]) -> dict[str, Any]:
    if not previous:
        return {"available": False, "notes": "no previous MoME eval run available"}
    prev = previous[-1]
    keys = ["packet_term_hit_rate", "expert_selection_hit_rate", "source_family_hit_rate", "provenance_ok_rate", "caution_hit_rate", "empty_packet_count", "overclaim_risk_count", "overcompression_risk_count", "average_latency_ms", "average_packet_chars"]
    return {
        "available": True,
        "previous_eval_run_id": prev.get("eval_run_id"),
        "metric_deltas": {key: round(float(summary.get(key, 0)) - float(prev.get(key, 0)), 4) for key in keys},
    }


def write_outputs(out_dir: Path, config: dict[str, Any], rows: list[dict[str, Any]], summary: dict[str, Any], comparison: dict[str, Any] | None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "mome_eval_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    payload = {"config": config, "summary": summary, "per_case_results": rows, "comparison_vs_previous": comparison}
    (out_dir / "mome_eval_results.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    fields = ["case_id", "category", "policy", "packet_term_hit", "expert_selection_hit", "source_family_hit", "provenance_ok", "caution_hit", "empty_packet", "overclaim_risk", "overcompression_risk", "latency_ms", "packet_chars", "packet_line_count", "provenance_rate", "packet_text_short"]
    with (out_dir / "mome_eval_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fields})
    lines = ["# IVY MoME Eval", "", "## Summary", ""]
    for key, value in summary.items():
        lines.append(f"- {key}: `{value}`")
    lines += ["", "## Cases", "", "| case | policy | terms | experts | source_family | provenance | caution | empty | chars |", "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in rows:
        lines.append(f"| {row['case_id']} | {row['policy']} | {row['packet_term_hit']} | {row['expert_selection_hit']} | {row['source_family_hit']} | {row['provenance_ok']} | {row['caution_hit']} | {row['empty_packet']} | {row['packet_chars']} |")
    if comparison:
        lines += ["", "## Comparison", "", f"- {comparison}"]
    (out_dir / "mome_eval_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate IVY MoME packet quality.")
    parser.add_argument("--cases", required=True)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--policies", nargs="*")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-packet-chars", type=int)
    parser.add_argument("--compare-latest", action="store_true")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    args = parser.parse_args()

    cases = load_cases(args.cases)
    root = Path(args.output_root)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    out_dir = root / run_id
    prior = load_history(root) if args.compare_latest else []
    rows, summary = evaluate(cases, args)
    comparison = compare_latest(summary, prior) if args.compare_latest else None
    config = {"eval_run_id": run_id, "cases_path": args.cases, "db_path": args.db, "policies": args.policies, "top_k": args.top_k, "max_packet_chars": args.max_packet_chars, "output_dir": str(out_dir)}
    write_outputs(out_dir, config, rows, summary, comparison)
    append_history(root, {**config, **summary})
    print(f"MoME eval run: {out_dir}")
    print(f"packet_term_hit_rate: {summary['packet_term_hit_rate']}")
    print(f"expert_selection_hit_rate: {summary['expert_selection_hit_rate']}")
    if comparison:
        print(comparison.get("notes") or f"compared with {comparison.get('previous_eval_run_id')}")


if __name__ == "__main__":
    main()
