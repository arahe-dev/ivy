from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .memory_packet import to_dict
from .memory_packet_cli import build_synthetic_memory, packet_quality_score, run_preview
from .memory_store import DEFAULT_DB_PATH


DEFAULT_OUTPUT_ROOT = Path("C:/ivy/runs/memory_packet_sweep")
DEFAULT_POLICIES = ["none", "keyword_only", "vector_only", "hybrid_default", "failure_first", "benchmark", "safety_first", "recent_buffer"]
OVERCLAIM_BASE_TERMS = ["confirmed", "guaranteed", "definitely", "always", "must"]


def norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def load_cases(path: str | Path, category: str | None = None) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    cases = data.get("cases") if isinstance(data, dict) else data
    if not isinstance(cases, list):
        raise ValueError("sweep cases must be a list or object with cases")
    out = []
    for case in cases:
        for key in ("id", "category", "query", "expected_packet_terms"):
            if key not in case:
                raise ValueError(f"case missing {key}: {case}")
        if category and case["category"] != category:
            continue
        out.append(case)
    return out


def term_hit(packet_text: str, terms: list[str]) -> bool:
    blob = norm(packet_text)
    return all(norm(term) in blob for term in terms)


def warning_terms_present(packet_text: str, terms: list[str]) -> bool:
    if not terms:
        return True
    blob = norm(packet_text)
    return all(norm(term) in blob for term in terms)


def audit_overclaim(packet: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    text = norm(packet.get("packet_text"))
    terms = list(case.get("overclaim_risk_terms") or []) + OVERCLAIM_BASE_TERMS
    hits = [term for term in terms if norm(term) and norm(term) in text]
    metrics = packet.get("metrics", {})
    weak_evidence = metrics.get("evidence_count", 0) < 2 or metrics.get("provenance_line_rate", 0.0) < 1.0
    return {
        "risk": bool(hits and weak_evidence),
        "terms": hits,
        "weak_evidence": weak_evidence,
    }


def audit_evidence(packet: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for line in packet.get("packet_lines") or []:
        evidence_count = int(line.get("evidence_count") or 0)
        text = norm(line.get("text"))
        generic = any(term in text for term in ("safety memory", "relevant memory", "workflow memory")) and evidence_count <= 1
        caution = any(term in text for term in ("caution", "risk", "treat as", "may", "smoke"))
        rows.append({
            "memory_item_id": line.get("memory_item_id"),
            "kind": line.get("kind"),
            "provenance_present": bool(line.get("provenance_present")),
            "source_artifact_present": bool(line.get("source_artifact_path") or line.get("example_artifacts")),
            "evidence_count": evidence_count,
            "exact_or_generic": "generic" if generic else "specific",
            "caution_present": caution,
        })
    return rows


def audit_overcompression(packet: dict[str, Any]) -> dict[str, Any]:
    metrics = packet.get("metrics", {})
    groups = packet.get("candidate_groups") or []
    risks = []
    if metrics.get("raw_candidate_count", 0) >= 5 and metrics.get("grouped_candidate_count") == 1:
        kinds = {g.get("kind") for g in groups}
        experts = set()
        for g in groups:
            experts.update(g.get("source_experts") or [])
        if len(kinds) > 1:
            risks.append("mixed kinds collapsed into one group")
        if len(experts) > 3:
            risks.append("many source experts collapsed into one group")
        for g in groups:
            text = norm(g.get("summary"))
            if g.get("kind") == "benchmark_result" and "different" not in text and g.get("evidence_count", 0) > 1:
                risks.append("benchmark group may hide materially different configs")
            if g.get("kind") in {"policy_warning", "safety_warning"} and g.get("evidence_count", 0) > 3 and "generic" not in text:
                risks.append("safety group may hide distinct safety warning types")
    return {"risk": bool(risks), "reasons": risks}


def evaluate_packet(case: dict[str, Any], policy: str, packet_obj: Any) -> dict[str, Any]:
    packet = to_dict(packet_obj)
    text = packet["packet_text"]
    metrics = packet["metrics"]
    forbidden_hits = [term for term in case.get("forbidden_packet_terms") or [] if norm(term) in norm(text)]
    overclaim = audit_overclaim(packet, case)
    overcompression = audit_overcompression(packet)
    expected_warnings = warning_terms_present(text, case.get("expected_warning_terms") or [])
    quality_metrics = dict(metrics)
    quality_metrics["packet_quality_score"] = packet_quality_score(quality_metrics)
    result = {
        "case_id": case["id"],
        "category": case["category"],
        "query": case["query"],
        "policy": policy,
        "packet_term_hit": term_hit(text, case.get("expected_packet_terms") or []),
        "forbidden_term_violation": bool(forbidden_hits),
        "forbidden_terms": forbidden_hits,
        "warning_terms_present": expected_warnings,
        "overclaim_risk_detected": overclaim["risk"],
        "overclaim_terms": overclaim["terms"],
        "overcompression_risk_detected": overcompression["risk"],
        "overcompression_reasons": overcompression["reasons"],
        "empty_packet": metrics.get("packet_line_count", 0) == 0,
        "truncated": bool(metrics.get("truncated")),
        "evidence_audit": audit_evidence(packet),
        "packet_text": text,
        "packet": packet,
        **quality_metrics,
    }
    result["packet_quality_score"] = quality_metrics["packet_quality_score"]
    return result


def run_sweep(cases: list[dict[str, Any]], db: str, policies: list[str] | None, top_k: int | None, max_packet_chars: int | None, out_dir: Path) -> list[dict[str, Any]]:
    packets_dir = out_dir / "packets"
    packets_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for case in cases:
        selected = policies or case.get("policies_to_test") or DEFAULT_POLICIES
        for policy in selected:
            packet, _ = run_preview(case["query"], db, policy, top_k, max_packet_chars, save=False)
            safe_name = f"{case['id']}__{policy}"
            (packets_dir / f"{safe_name}.txt").write_text(packet.packet_text, encoding="utf-8")
            (packets_dir / f"{safe_name}.json").write_text(json.dumps(to_dict(packet), indent=2, ensure_ascii=False), encoding="utf-8")
            rows.append(evaluate_packet(case, policy, packet))
    return rows


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_case = defaultdict(list)
    by_cat = defaultdict(list)
    by_policy = defaultdict(list)
    for row in rows:
        by_case[row["case_id"]].append(row)
        by_cat[row["category"]].append(row)
        by_policy[row["policy"]].append(row)
    best_by_case = {case: max(items, key=lambda r: r["packet_quality_score"])["policy"] for case, items in by_case.items()}
    best_by_category = {}
    for cat, items in by_cat.items():
        scores = defaultdict(list)
        for row in items:
            scores[row["policy"]].append(row["packet_quality_score"])
        best_by_category[cat] = max(scores.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))[0]
    def policy_avg(policy: str, key: str) -> float:
        items = by_policy.get(policy, [])
        return sum(float(r.get(key, 0)) for r in items) / len(items) if items else 0.0
    policies = list(by_policy)
    summary = {
        "total_packets": len(rows),
        "total_cases": len(by_case),
        "packet_term_hit_rate": avg_bool(rows, "packet_term_hit"),
        "overclaim_risk_count": sum(1 for r in rows if r["overclaim_risk_detected"]),
        "overcompression_risk_count": sum(1 for r in rows if r["overcompression_risk_detected"]),
        "empty_packet_count": sum(1 for r in rows if r["empty_packet"]),
        "average_packet_chars": round(avg(rows, "packet_chars"), 3),
        "average_latency_ms": round(avg(rows, "latency_ms"), 3),
        "best_policy_by_case": best_by_case,
        "best_policy_by_category": best_by_category,
        "most_compact_policy": min(policies, key=lambda p: policy_avg(p, "packet_chars")) if policies else None,
        "most_evidence_dense_policy": min(policies, key=lambda p: policy_avg(p, "chars_per_evidence")) if policies else None,
        "most_overclaim_prone_policy": max(policies, key=lambda p: sum(1 for r in by_policy[p] if r["overclaim_risk_detected"])) if policies else None,
        "most_empty_policy": max(policies, key=lambda p: sum(1 for r in by_policy[p] if r["empty_packet"])) if policies else None,
        "highest_provenance_policy": max(policies, key=lambda p: policy_avg(p, "provenance_line_rate")) if policies else None,
        "lowest_latency_policy": min(policies, key=lambda p: policy_avg(p, "latency_ms")) if policies else None,
    }
    return summary


def avg(rows: list[dict[str, Any]], key: str) -> float:
    return sum(float(r.get(key, 0)) for r in rows) / len(rows) if rows else 0.0


def avg_bool(rows: list[dict[str, Any]], key: str) -> float:
    return round(sum(1 for r in rows if r.get(key)) / len(rows), 4) if rows else 0.0


def load_history(root: Path) -> list[dict[str, Any]]:
    path = root / "history.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_history(root: Path, row: dict[str, Any]) -> None:
    with (root / "history.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    fields = ["run_id", "cases_path", "db_path", "total_packets", "total_cases", "packet_term_hit_rate", "overclaim_risk_count", "overcompression_risk_count", "empty_packet_count", "average_packet_chars", "average_latency_ms"]
    csv_path = root / "history.csv"
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k) for k in fields})


def write_outputs(out_dir: Path, config: dict[str, Any], rows: list[dict[str, Any]], summary: dict[str, Any], compare: dict[str, Any] | None, inspect_failures: bool) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    comp_dir = out_dir / "comparisons"
    comp_dir.mkdir(exist_ok=True)
    (out_dir / "sweep_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    (out_dir / "sweep_results.json").write_text(json.dumps({"config": config, "summary": summary, "results": rows, "comparison": compare}, indent=2, ensure_ascii=False), encoding="utf-8")
    fields = ["case_id", "category", "policy", "packet_term_hit", "packet_quality_score", "packet_chars", "evidence_count", "unique_kind_count", "duplicate_group_count", "compression_ratio", "chars_per_evidence", "provenance_line_rate", "latency_ms", "warning_terms_present", "overclaim_risk_detected", "overcompression_risk_detected", "empty_packet", "truncated"]
    with (out_dir / "sweep_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fields})
    write_report(out_dir / "sweep_report.md", rows, summary, compare)
    write_policy_comparison(comp_dir / "policy_comparison.md", rows, summary)
    write_category_summary(comp_dir / "category_summary.md", rows, summary)
    if inspect_failures:
        write_failure_inspection(comp_dir / "failure_inspection.md", rows)


def write_report(path: Path, rows: list[dict[str, Any]], summary: dict[str, Any], compare: dict[str, Any] | None) -> None:
    lines = ["# Memory Packet Sweep", "", "## Overall Summary", ""]
    for key, value in summary.items():
        if not isinstance(value, dict):
            lines.append(f"- {key}: `{value}`")
    lines += ["", "## Failed Cases", ""]
    failed = [r for r in rows if not r["packet_term_hit"]]
    lines.extend([f"- `{r['case_id']}` / `{r['policy']}`" for r in failed[:30]] or ["- None."])
    lines += ["", "## Overclaim Risks", ""]
    over = [r for r in rows if r["overclaim_risk_detected"]]
    lines.extend([f"- `{r['case_id']}` / `{r['policy']}` terms={r['overclaim_terms']}" for r in over[:30]] or ["- None."])
    lines += ["", "## Overcompression Risks", ""]
    comp = [r for r in rows if r["overcompression_risk_detected"]]
    lines.extend([f"- `{r['case_id']}` / `{r['policy']}` reasons={r['overcompression_reasons']}" for r in comp[:30]] or ["- None."])
    lines += ["", "## Recommended Policies For Phase 2C", ""]
    for cat, policy in summary.get("best_policy_by_category", {}).items():
        lines.append(f"- `{cat}`: `{policy}`")
    if compare:
        lines += ["", "## Comparison", "", f"- {compare}"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_policy_comparison(path: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    by_policy = defaultdict(list)
    for row in rows:
        by_policy[row["policy"]].append(row)
    lines = ["# Policy Comparison", "", "| policy | packets | hit_rate | avg_quality | avg_chars | avg_latency | empty | overclaim | overcompression |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for policy, items in sorted(by_policy.items()):
        lines.append(f"| {policy} | {len(items)} | {avg_bool(items, 'packet_term_hit')} | {round(avg(items, 'packet_quality_score'), 4)} | {round(avg(items, 'packet_chars'), 1)} | {round(avg(items, 'latency_ms'), 1)} | {sum(1 for r in items if r['empty_packet'])} | {sum(1 for r in items if r['overclaim_risk_detected'])} | {sum(1 for r in items if r['overcompression_risk_detected'])} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_category_summary(path: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    by_cat = defaultdict(list)
    for row in rows:
        by_cat[row["category"]].append(row)
    lines = ["# Category Summary", "", "| category | packets | hit_rate | best_policy | avg_chars | overclaim | overcompression |", "|---|---:|---:|---|---:|---:|---:|"]
    for cat, items in sorted(by_cat.items()):
        lines.append(f"| {cat} | {len(items)} | {avg_bool(items, 'packet_term_hit')} | {summary['best_policy_by_category'].get(cat)} | {round(avg(items, 'packet_chars'), 1)} | {sum(1 for r in items if r['overclaim_risk_detected'])} | {sum(1 for r in items if r['overcompression_risk_detected'])} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_failure_inspection(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = ["# Failure Inspection", ""]
    for row in rows:
        if row["packet_term_hit"] and not row["overclaim_risk_detected"] and not row["overcompression_risk_detected"] and not row["empty_packet"]:
            continue
        lines.append(f"## {row['case_id']} / {row['policy']}")
        lines.append(f"- hit: `{row['packet_term_hit']}`")
        lines.append(f"- empty: `{row['empty_packet']}`")
        lines.append(f"- overclaim: `{row['overclaim_risk_detected']}` {row['overclaim_terms']}")
        lines.append(f"- overcompression: `{row['overcompression_risk_detected']}` {row['overcompression_reasons']}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def compare_latest(summary: dict[str, Any], prior: list[dict[str, Any]]) -> dict[str, Any]:
    if not prior:
        return {"available": False, "notes": "no previous run available"}
    prev = prior[-1]
    keys = ["packet_term_hit_rate", "overclaim_risk_count", "overcompression_risk_count", "empty_packet_count", "average_packet_chars", "average_latency_ms"]
    return {"available": True, "previous_run_id": prev.get("run_id"), "metric_deltas": {k: round(float(summary.get(k, 0)) - float(prev.get(k, 0)), 4) for k in keys}}


def self_test() -> int:
    from tempfile import TemporaryDirectory
    from .memory_packet_cli import build_synthetic_memory
    with TemporaryDirectory() as td:
        root = Path(td)
        db = root / "synthetic.sqlite3"
        build_synthetic_memory(db)
        cases_path = root / "cases.json"
        cases_path.write_text(json.dumps({"cases": [
            {"id": "json", "category": "json_tool_debug", "query": "json qwen think validation", "expected_packet_terms": ["json", "think"], "policies_to_test": ["failure_first"], "must_have_provenance": True},
            {"id": "bench", "category": "benchmark", "query": "qwen ctx=512 decode_tps", "expected_packet_terms": ["qwen", "decode_tps"], "policies_to_test": ["benchmark"], "must_have_provenance": True},
            {"id": "safety", "category": "safety", "query": "absolute path policy sandbox guaranteed", "expected_packet_terms": ["path", "policy"], "policies_to_test": ["safety_first"], "overclaim_risk_terms": ["guaranteed"], "must_have_provenance": False},
            {"id": "workflow", "category": "workflow", "query": "calc write workflow", "expected_packet_terms": ["calc", "write"], "policies_to_test": ["hybrid_default"], "must_have_provenance": True}
        ]}), encoding="utf-8")
        out = root / "out"
        cases = load_cases(cases_path)
        rows = run_sweep(cases, str(db), None, 5, 1200, out)
        summary = aggregate(rows)
        write_outputs(out, {"run_id": "selftest", "cases_path": str(cases_path), "db_path": str(db)}, rows, summary, None, True)
        fake_packet = {"packet_text": "This is guaranteed true.", "metrics": {"evidence_count": 0, "provenance_line_rate": 0.0}, "packet_lines": []}
        if not audit_overclaim(fake_packet, {"overclaim_risk_terms": ["guaranteed"]})["risk"]:
            print("FAIL overclaim audit")
            return 1
        fake_comp = {"metrics": {"raw_candidate_count": 5, "grouped_candidate_count": 1}, "candidate_groups": [{"kind": "benchmark_result", "summary": "benchmark summary", "source_experts": ["a", "b", "c", "d"], "evidence_count": 5}]}
        if not audit_overcompression(fake_comp)["risk"]:
            print("FAIL overcompression audit")
            return 1
        required = [out / "sweep_report.md", out / "comparisons" / "policy_comparison.md", out / "comparisons" / "category_summary.md", out / "comparisons" / "failure_inspection.md"]
        if not all(p.exists() for p in required):
            print("FAIL missing outputs")
            return 1
    print("PASS")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run broad real memory packet sweep.")
    parser.add_argument("--cases")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--policies", nargs="*")
    parser.add_argument("--compare-latest", action="store_true")
    parser.add_argument("--category")
    parser.add_argument("--inspect-failures", action="store_true")
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--max-packet-chars", type=int)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if not args.cases:
        raise SystemExit("--cases is required unless --self-test is used")
    root = Path(args.output_root)
    root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    out_dir = root / run_id
    cases = load_cases(args.cases, args.category)
    prior = load_history(root) if args.compare_latest else []
    rows = run_sweep(cases, args.db, args.policies, args.top_k, args.max_packet_chars, out_dir)
    summary = aggregate(rows)
    config = {"run_id": run_id, "cases_path": args.cases, "db_path": args.db, "policies": args.policies, "category": args.category, "top_k": args.top_k, "max_packet_chars": args.max_packet_chars, "output_dir": str(out_dir)}
    comparison = compare_latest(summary, prior) if args.compare_latest else None
    write_outputs(out_dir, config, rows, summary, comparison, args.inspect_failures)
    write_history(root, {**config, **summary})
    print(f"packet sweep run: {out_dir}")
    print(f"packet_term_hit_rate: {summary['packet_term_hit_rate']}")
    print(f"overclaim_risk_count: {summary['overclaim_risk_count']}")
    print(f"overcompression_risk_count: {summary['overcompression_risk_count']}")


if __name__ == "__main__":
    main()
