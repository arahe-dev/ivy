from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from .memory_packet import to_dict
from .memory_router import classify_source_family, route_memory
from .memory_search import vectorize_memory_items
from .memory_store import DEFAULT_DB_PATH, MemoryStore


DEFAULT_CASES = Path(__file__).resolve().parent / "memory_packet_ranking_cases.json"
DEFAULT_OUTPUT_ROOT = Path("C:/ivy/runs/memory_ranking_eval")


def load_cases(path: str | Path, category: str | None = None) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = payload.get("cases", payload if isinstance(payload, list) else [])
    if category:
        cases = [case for case in cases if case.get("category") == category]
    return cases


def term_hit(candidate_blob: str, terms: list[str]) -> bool:
    blob = candidate_blob.lower()
    hits = 0
    for term in terms:
        t = term.lower()
        aliases = [t]
        if t == "ctx=512":
            aliases.append("ctx 512")
        if t == "json_validate":
            aliases.append("validate")
        if any(alias in blob for alias in aliases):
            hits += 1
    if not terms:
        return True
    return hits >= len(terms) if len(terms) <= 2 else hits >= 2


def evaluate_case(case: dict[str, Any], db_path: str | Path, top_k: int) -> dict[str, Any]:
    start = time.perf_counter()
    decision, candidates, _policy = route_memory(case["query"], db_path, case.get("policy"), top_k)
    latency_ms = round((time.perf_counter() - start) * 1000.0, 3)
    expected_family = case.get("expected_preferred_source_family")
    expected_terms = case.get("expected_terms") or []
    top = candidates[:top_k]
    top1 = top[0] if top else None
    blobs = [f"{c.text} {c.kind or ''} {c.source_artifact_path or ''} {' '.join((c.ranking or {}).get('matched_terms', []))}" for c in top]
    top1_family_hit = bool(top1 and top1.source_family == expected_family)
    top3_family_hit = any(c.source_family == expected_family for c in top[:3])
    terms_hit = any(term_hit(blob, expected_terms) for blob in blobs)
    provenance = bool(top1 and top1.provenance_present)
    return {
        "case_id": case.get("id"),
        "category": case.get("category"),
        "query": case.get("query"),
        "policy": decision.selected_policy,
        "expected_source_family": expected_family,
        "top1_source_family": top1.source_family if top1 else None,
        "top1_source_family_hit": top1_family_hit,
        "top3_source_family_hit": top3_family_hit,
        "term_hit": terms_hit,
        "provenance": provenance,
        "latency_ms": latency_ms,
        "top_candidates": [to_dict(c) for c in top],
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    return {
        "total_cases": total,
        "top_1_source_family_hit_rate": round(sum(1 for r in results if r["top1_source_family_hit"]) / total, 4) if total else 0.0,
        "top_3_source_family_hit_rate": round(sum(1 for r in results if r["top3_source_family_hit"]) / total, 4) if total else 0.0,
        "term_hit_rate": round(sum(1 for r in results if r["term_hit"]) / total, 4) if total else 0.0,
        "provenance_rate": round(sum(1 for r in results if r["provenance"]) / total, 4) if total else 0.0,
        "avg_latency_ms": round(sum(float(r["latency_ms"]) for r in results) / total, 3) if total else 0.0,
        "known_miss_recovery_rate": round(sum(1 for r in results if r["top3_source_family_hit"] and r["term_hit"]) / total, 4) if total else 0.0,
    }


def read_history(root: Path) -> list[dict[str, Any]]:
    path = root / "history.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def compare_latest(root: Path, summary: dict[str, Any]) -> dict[str, Any]:
    history = read_history(root)
    if not history:
        return {"available": False, "message": "no previous run available"}
    prev = history[-1]
    keys = ["top_1_source_family_hit_rate", "top_3_source_family_hit_rate", "term_hit_rate", "provenance_rate", "avg_latency_ms", "known_miss_recovery_rate"]
    return {
        "available": True,
        "previous_run_id": prev.get("run_id"),
        "metric_deltas": {key: round(float(summary.get(key, 0)) - float(prev.get(key, 0)), 4) for key in keys},
    }


def write_outputs(out_dir: Path, config: dict[str, Any], results: list[dict[str, Any]], summary: dict[str, Any], comparison: dict[str, Any] | None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"config": config, "summary": summary, "results": results, "comparison": comparison}
    (out_dir / "ranking_eval_results.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "ranking_eval_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    fields = ["case_id", "category", "query", "policy", "expected_source_family", "top1_source_family", "top1_source_family_hit", "top3_source_family_hit", "term_hit", "provenance", "latency_ms"]
    with (out_dir / "ranking_eval_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k) for k in fields})
    lines = ["# Memory Ranking Eval", "", "## Summary", ""]
    for key, value in summary.items():
        lines.append(f"- {key}: `{value}`")
    if comparison:
        lines += ["", "## Comparison", "", f"- available: `{comparison.get('available')}`"]
        if comparison.get("available"):
            lines.append(f"- previous_run_id: `{comparison.get('previous_run_id')}`")
            for key, value in comparison.get("metric_deltas", {}).items():
                lines.append(f"- {key}: `{value}`")
    lines += ["", "## Cases", "", "| case | expected | top1 | top1_hit | top3_hit | term_hit |", "|---|---|---|---:|---:|---:|"]
    for row in results:
        lines.append(f"| {row['case_id']} | {row['expected_source_family']} | {row['top1_source_family']} | {row['top1_source_family_hit']} | {row['top3_source_family_hit']} | {row['term_hit']} |")
    (out_dir / "ranking_eval_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_history(root: Path, run_id: str, summary: dict[str, Any], config: dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    row = {"run_id": run_id, "db_path": config.get("db_path"), "cases_path": config.get("cases_path"), **summary}
    with (root / "history.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    csv_path = root / "history.csv"
    fields = ["run_id", "total_cases", "top_1_source_family_hit_rate", "top_3_source_family_hit_rate", "term_hit_rate", "provenance_rate", "avg_latency_ms", "known_miss_recovery_rate"]
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k) for k in fields})


def insert_fixture(db: Path, kind: str, text: str, source: str, run_id: str = "ranking-selftest") -> None:
    store = MemoryStore(db)
    store.init_schema()
    ep = store.insert_episode(run_id=run_id, task_text="ranking selftest", success=True, artifact_path=source, source_kind="selftest")
    conn = store.connect()
    try:
        with conn:
            store.insert_memory_item(conn, source_episode_id=ep, kind=kind, text=text, importance=0.7, confidence=0.9, status="active", source_artifact_path=source)
    finally:
        conn.close()


def self_test() -> int:
    with TemporaryDirectory() as td:
        root = Path(td)
        db = root / "ranking.sqlite3"
        fixtures = [
            ("benchmark_result", "Qwen 4060 benchmark ctx=512 decode_tps=19.6 n_gpu_layers=20", "C:/ivy/runs/qwen36_4060_bench/run/result.json"),
            ("doc_reference", "Generic benchmark policy docs mention qwen but no ctx field", "C:/ivy/ivy/docs/IVY_MEMORY_RANKING.md"),
            ("safety_rule", "Policy rejects write outside sandbox and blocks delete/network intent.", "C:/ivy/ivy_agent_demo/policy.py"),
            ("doc_reference", "Generic safety documentation overview.", "C:/ivy/ivy/docs/SAFETY.md"),
            ("workflow_procedure", "Workflow trace used fs_read then json_validate successfully.", "C:/ivy/runs/phase1_agent_demo/run/run_summary.json"),
            ("runbook_command", "Rerun memory eval command: python -m ivy_agent_demo.memory_eval --compare-latest", "C:/ivy/ivy/docs/IVY_BUILD_AND_RUNBOOK.md"),
        ]
        for fixture in fixtures:
            insert_fixture(db, *fixture)
        vectorize_memory_items(db)
        bench_decision, bench_candidates, _ = route_memory("qwen 4060 ctx 512 decode_tps", db, "benchmark", 5)
        safety_decision, safety_candidates, _ = route_memory("write outside sandbox policy", db, "safety_first", 5)
        workflow_decision, workflow_candidates, _ = route_memory("fs_read then json_validate workflow", db, "hybrid_default", 5)
        assert classify_source_family(bench_candidates[0]) == "benchmark_artifact"
        assert bench_candidates[0].source_family == "benchmark_artifact", bench_candidates[0]
        assert safety_candidates[0].source_family == "safety_policy", safety_candidates[0]
        assert workflow_candidates[0].source_family == "workflow_trace", workflow_candidates[0]
        cases = [
            {"id": "bench", "category": "benchmark", "query": "qwen 4060 ctx 512 decode_tps", "policy": "benchmark", "expected_preferred_source_family": "benchmark_artifact", "expected_terms": ["ctx=512", "decode_tps"]},
            {"id": "safety", "category": "safety", "query": "write outside sandbox policy", "policy": "safety_first", "expected_preferred_source_family": "safety_policy", "expected_terms": ["write", "sandbox"]},
            {"id": "workflow", "category": "workflow", "query": "fs_read then json_validate workflow", "policy": "hybrid_default", "expected_preferred_source_family": "workflow_trace", "expected_terms": ["fs_read", "json_validate"]},
        ]
        results = [evaluate_case(case, db, 5) for case in cases]
        summary = summarize(results)
        out_dir = root / "out"
        write_outputs(out_dir, {"db_path": str(db), "cases_path": "selftest"}, results, summary, None)
        assert summary["top_1_source_family_hit_rate"] == 1.0
        assert (out_dir / "ranking_eval_report.md").exists()
    print("PASS")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate IVY memory ranking precision.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--category")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--compare-latest", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    root = Path(args.output_root)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    out_dir = root / run_id
    cases = load_cases(args.cases, args.category)
    results = [evaluate_case(case, args.db, args.top_k) for case in cases]
    summary = summarize(results)
    config = {"run_id": run_id, "cases_path": args.cases, "db_path": args.db, "category": args.category, "top_k": args.top_k, "output_dir": str(out_dir)}
    comparison = compare_latest(root, summary) if args.compare_latest else None
    write_outputs(out_dir, config, results, summary, comparison)
    append_history(root, run_id, summary, config)
    print(f"ranking eval run: {out_dir}")
    print(f"top_1_source_family_hit_rate: {summary['top_1_source_family_hit_rate']}")
    print(f"top_3_source_family_hit_rate: {summary['top_3_source_family_hit_rate']}")
    print(f"term_hit_rate: {summary['term_hit_rate']}")
    print(f"known_miss_recovery_rate: {summary['known_miss_recovery_rate']}")


if __name__ == "__main__":
    main()
