from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from .memory_store import DEFAULT_DB_PATH, MemoryStore


DEFAULT_OUTPUT_ROOT = Path("C:/ivy/runs/memory_coverage")

TARGETS = [
    ("safety", "write outside sandbox", ["write", "sandbox"]),
    ("safety", "path traversal", ["path", "traversal"]),
    ("safety", "absolute path rejection", ["absolute", "path"]),
    ("safety", "unsafe delete intent", ["delete", "unsafe"]),
    ("safety", "network string blocking", ["network"]),
    ("safety", "sandbox-relative path rule", ["sandbox", "relative", "path"]),
    ("workflow", "fs_read then json_validate", ["fs_read", "json_validate"]),
    ("workflow", "fs_write only under out/", ["fs_write", "out"]),
    ("workflow", "calc_eval then fs_write", ["calc_eval", "fs_write"]),
    ("workflow", "tool call validation before policy execution", ["validation", "policy"]),
    ("runbook", "rerun memory eval command", ["memory_eval", "compare-latest"]),
    ("runbook", "rerun packet sweep command", ["memory_packet_sweep"]),
    ("runbook", "ingest phase1_agent_demo runs", ["ingest", "phase1_agent_demo"]),
    ("runbook", "ingest qwen benchmark runs", ["ingest", "qwen36_4060_bench"]),
    ("runbook", "benchmark policy choice guidance", ["benchmark", "policy"]),
    ("runbook", "where memory artifacts are saved", ["runs", "memory_eval"]),
    ("runbook", "where packet preview artifacts are saved", ["memory_packet_preview"]),
    ("runbook", "where packet sweep artifacts are saved", ["memory_packet_sweep"]),
]


def search_target(store: MemoryStore, terms: list[str]) -> list[dict[str, Any]]:
    conn = store.connect()
    try:
        where = " AND ".join(["LOWER(text || ' ' || COALESCE(kind,'') || ' ' || COALESCE(source_artifact_path,'')) LIKE ?" for _ in terms])
        rows = conn.execute(
            f"""
            SELECT id, kind, text, source_artifact_path
            FROM memory_items
            WHERE {where}
            ORDER BY importance DESC, id DESC
            LIMIT 10
            """,
            tuple(f"%{term.lower()}%" for term in terms),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def run_coverage(db_path: str | Path, category: str | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    store = MemoryStore(db_path)
    store.init_schema()
    results = []
    for cat, target, terms in TARGETS:
        if category and cat != category:
            continue
        rows = search_target(store, terms)
        results.append({
            "category": cat,
            "target": target,
            "covered": bool(rows),
            "matching_memory_item_ids": [r["id"] for r in rows],
            "source_artifact_paths": sorted({r["source_artifact_path"] for r in rows if r.get("source_artifact_path")}),
            "suggested_gap": "" if rows else f"Add source-provenanced docs/source memory for: {target}",
        })
    summary = {
        "total_targets": len(results),
        "covered_targets": sum(1 for r in results if r["covered"]),
        "coverage_rate": round(sum(1 for r in results if r["covered"]) / len(results), 4) if results else 0.0,
        "by_category": {},
    }
    for cat in sorted({r["category"] for r in results}):
        subset = [r for r in results if r["category"] == cat]
        summary["by_category"][cat] = {
            "total": len(subset),
            "covered": sum(1 for r in subset if r["covered"]),
            "coverage_rate": round(sum(1 for r in subset if r["covered"]) / len(subset), 4) if subset else 0.0,
        }
    return results, summary


def write_outputs(out_dir: Path, results: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "coverage_results.json").write_text(json.dumps({"summary": summary, "results": results}, indent=2), encoding="utf-8")
    fields = ["category", "target", "covered", "matching_memory_item_ids", "source_artifact_paths", "suggested_gap"]
    with (out_dir / "coverage_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    lines = ["# Memory Coverage Report", "", "## Summary", ""]
    for key, value in summary.items():
        if key != "by_category":
            lines.append(f"- {key}: `{value}`")
    lines += ["", "## By Category", "", "| category | covered | total | rate |", "|---|---:|---:|---:|"]
    for cat, row in summary["by_category"].items():
        lines.append(f"| {cat} | {row['covered']} | {row['total']} | {row['coverage_rate']} |")
    lines += ["", "## Gaps", ""]
    gaps = [r for r in results if not r["covered"]]
    lines.extend([f"- `{r['category']}` {r['target']}: {r['suggested_gap']}" for r in gaps] or ["- None."])
    (out_dir / "coverage_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_history(root: Path, run_id: str, summary: dict[str, Any]) -> None:
    row = {"run_id": run_id, **{k: v for k, v in summary.items() if k != "by_category"}}
    with (root / "history.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    csv_path = root / "history.csv"
    fields = ["run_id", "total_targets", "covered_targets", "coverage_rate"]
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k) for k in fields})


def self_test() -> int:
    with TemporaryDirectory() as td:
        db = Path(td) / "coverage.sqlite3"
        store = MemoryStore(db)
        store.init_schema()
        ep = store.insert_episode(run_id="coverage-selftest", task_text="coverage selftest", success=True, source_kind="selftest")
        conn = store.connect()
        try:
            with conn:
                store.insert_memory_item(conn, source_episode_id=ep, kind="safety_rule", text="fs_write may only write under out/ inside the sandbox.", source_artifact_path="synthetic://policy")
                store.insert_memory_item(conn, source_episode_id=ep, kind="runbook_command", text="Run memory eval with python -m ivy_agent_demo.memory_eval --compare-latest.", source_artifact_path="synthetic://runbook")
                store.insert_memory_item(conn, source_episode_id=ep, kind="workflow_procedure", text="Use calc_eval then fs_write for successful calc write workflow.", source_artifact_path="synthetic://workflow")
        finally:
            conn.close()
        results, summary = run_coverage(db)
        out_dir = Path(td) / "out"
        write_outputs(out_dir, results, summary)
        assert any(r["covered"] for r in results)
        assert any(not r["covered"] for r in results)
        assert (out_dir / "coverage_report.md").exists()
    print("PASS")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Check source-provenanced memory coverage.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--category", choices=["safety", "workflow", "runbook"])
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    out_dir = Path(args.output_root) / run_id
    results, summary = run_coverage(args.db, args.category)
    write_outputs(out_dir, results, summary)
    append_history(Path(args.output_root), run_id, summary)
    payload = {"summary": summary, "results": results, "output_dir": str(out_dir)}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"coverage run: {out_dir}")
        print(f"coverage_rate: {summary['coverage_rate']}")
        for cat, row in summary["by_category"].items():
            print(f"{cat}: {row['covered']}/{row['total']} ({row['coverage_rate']})")


if __name__ == "__main__":
    main()
