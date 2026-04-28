from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from .memory_search import hybrid_search, keyword_search, vector_search, vectorize_memory_items
from .memory_store import DEFAULT_DB_PATH, MemoryStore


DEFAULT_OUTPUT_ROOT = Path("C:/ivy/runs/memory_eval")
VALID_MODES = {"keyword", "vector", "hybrid"}


@dataclass
class EvalCase:
    id: str
    query: str
    search_mode: str
    expected_terms: list[str]
    expected_kind: str | None = None
    expected_source_hint: str | None = None
    must_have_provenance: bool = True
    require_all_terms: bool = False
    notes: str = ""


def normalize(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def load_cases(path: str | Path) -> list[EvalCase]:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    raw_cases = data.get("cases") if isinstance(data, dict) else data
    if not isinstance(raw_cases, list):
        raise ValueError("Case file must contain a list or an object with a 'cases' list.")
    cases: list[EvalCase] = []
    for i, raw in enumerate(raw_cases):
        if not isinstance(raw, dict):
            raise ValueError(f"Case {i} is not an object.")
        missing = [k for k in ("id", "query", "search_mode", "expected_terms") if k not in raw]
        if missing:
            raise ValueError(f"Case {raw.get('id', i)} missing required fields: {missing}")
        if raw["search_mode"] not in VALID_MODES:
            raise ValueError(f"Case {raw['id']} has invalid search_mode: {raw['search_mode']}")
        if not isinstance(raw["expected_terms"], list) or not raw["expected_terms"]:
            raise ValueError(f"Case {raw['id']} expected_terms must be a non-empty list.")
        cases.append(
            EvalCase(
                id=str(raw["id"]),
                query=str(raw["query"]),
                search_mode=str(raw["search_mode"]),
                expected_terms=[str(x) for x in raw["expected_terms"]],
                expected_kind=raw.get("expected_kind"),
                expected_source_hint=raw.get("expected_source_hint"),
                must_have_provenance=bool(raw.get("must_have_provenance", True)),
                require_all_terms=bool(raw.get("require_all_terms", False)),
                notes=str(raw.get("notes", "")),
            )
        )
    return cases


def result_blob(result: dict[str, Any]) -> str:
    fields = [
        result.get("text"),
        result.get("kind"),
        result.get("source_artifact_path"),
        result.get("run_id"),
        result.get("source_episode_id"),
        result.get("artifact_path"),
    ]
    return normalize(" ".join(str(x or "") for x in fields))


def has_provenance(result: dict[str, Any]) -> bool:
    return bool(
        result.get("source_artifact_path")
        or result.get("source_episode_id")
        or result.get("run_id")
        or result.get("artifact_path")
    )


def required_term_count(case: EvalCase) -> int:
    n = len(case.expected_terms)
    if case.require_all_terms or n <= 2:
        return n
    return 2


def is_hit(case: EvalCase, result: dict[str, Any]) -> bool:
    blob = result_blob(result)
    matched = sum(1 for term in case.expected_terms if normalize(term) in blob)
    if matched < required_term_count(case):
        return False
    if case.expected_kind and normalize(case.expected_kind) not in normalize(result.get("kind")):
        return False
    if case.expected_source_hint and normalize(case.expected_source_hint) not in blob:
        return False
    if case.must_have_provenance and not has_provenance(result):
        return False
    return True


def run_search(case: EvalCase, db_path: Path, top_k: int) -> list[dict[str, Any]]:
    if case.search_mode == "keyword":
        rows, _ = keyword_search(case.query, db_path, top_k)
        return rows
    if case.search_mode == "vector":
        return vector_search(case.query, db_path, top_k)
    return hybrid_search(case.query, db_path, top_k)


def evaluate_cases(cases: list[EvalCase], db_path: Path, top_k: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    per_case: list[dict[str, Any]] = []
    latencies: list[float] = []
    for case in cases:
        start = time.perf_counter()
        skip_reason = ""
        try:
            results = run_search(case, db_path, top_k)
        except sqlite3.Error as exc:
            results = []
            skip_reason = f"sqlite error: {exc}"
        latency_ms = round((time.perf_counter() - start) * 1000.0, 3)
        latencies.append(latency_ms)
        hit_positions = [idx + 1 for idx, row in enumerate(results) if is_hit(case, row)]
        provenance_ok = (not case.must_have_provenance) or any(has_provenance(r) for r in results)
        skipped = bool(skip_reason)
        per_case.append(
            {
                "case_id": case.id,
                "query": case.query,
                "search_mode": case.search_mode,
                "expected_terms": case.expected_terms,
                "expected_kind": case.expected_kind,
                "expected_source_hint": case.expected_source_hint,
                "must_have_provenance": case.must_have_provenance,
                "require_all_terms": case.require_all_terms,
                "top_1_hit": bool(hit_positions and hit_positions[0] <= 1),
                "top_3_hit": bool(hit_positions and hit_positions[0] <= 3),
                "top_k_hit": bool(hit_positions),
                "best_hit_rank": hit_positions[0] if hit_positions else None,
                "provenance_ok": provenance_ok,
                "latency_ms": latency_ms,
                "skipped": skipped,
                "skip_reason": skip_reason,
                "top_results": results,
                "top_result_text_short": short_text(results[0].get("text") if results else "", 180),
                "top_result_source": results[0].get("source_artifact_path") if results else "",
                "notes": case.notes,
            }
        )
    evaluated = [r for r in per_case if not r["skipped"]]
    total = len(per_case)
    evaluated_count = len(evaluated)
    summary = {
        "total_cases": total,
        "evaluated_cases": evaluated_count,
        "skipped_cases": total - evaluated_count,
        "top_1_hit_rate": rate(evaluated, "top_1_hit"),
        "top_3_hit_rate": rate(evaluated, "top_3_hit"),
        "top_k_hit_rate": rate(evaluated, "top_k_hit"),
        "provenance_present_rate": rate(evaluated, "provenance_ok"),
        "average_latency_ms": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
        "per_case_latency_ms": {r["case_id"]: r["latency_ms"] for r in per_case},
    }
    return per_case, summary


def rate(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return round(sum(1 for r in rows if r.get(key)) / len(rows), 4)


def short_text(text: Any, limit: int = 120) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text[: limit - 3] + "..." if len(text) > limit else text


def build_synthetic_db(db_path: Path) -> None:
    store = MemoryStore(db_path)
    store.init_schema()
    ep = store.insert_episode(
        run_id="synthetic-memory-eval",
        task_text="synthetic memory retrieval evaluation fixture",
        outcome="fixture",
        success=True,
        artifact_path=str(db_path),
        source_kind="synthetic_eval",
    )
    conn = store.connect()
    try:
        with conn:
            items = [
                ("json_contamination_warning", "JSON validation failed because the model emitted think reasoning tags before a tool call JSON object.", "synthetic://json_think_tags"),
                ("benchmark_result", "Qwen 4060 benchmark result ctx=512 cache_k=f16 cache_v=f16 decode_tps=19.6 from qwen36_4060_bench.", "synthetic://qwen36_4060_bench"),
                ("policy_warning", "Policy blocked an absolute path violation because tool arguments used a Windows drive path.", "synthetic://absolute_path_policy"),
                ("successful_pattern", "Successful calc write workflow: calc_eval computed the value and fs_write saved the result successfully.", "synthetic://calc_write_success"),
            ]
            for kind, text, source in items:
                store.insert_memory_item(
                    conn,
                    source_episode_id=ep,
                    kind=kind,
                    text=text,
                    importance=0.8,
                    confidence=0.95,
                    status="active",
                    source_artifact_path=source,
                )
        vectorize_memory_items(db_path)
    finally:
        conn.close()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "case_id",
        "query",
        "search_mode",
        "top_1_hit",
        "top_3_hit",
        "top_k_hit",
        "provenance_ok",
        "latency_ms",
        "skipped",
        "skip_reason",
        "top_result_text_short",
        "top_result_source",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fields})


def history_paths(root: Path) -> tuple[Path, Path]:
    return root / "history.jsonl", root / "history.csv"


def load_history(root: Path) -> list[dict[str, Any]]:
    path, _ = history_paths(root)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def append_history(root: Path, row: dict[str, Any]) -> None:
    jsonl, csv_path = history_paths(root)
    with jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    fields = [
        "eval_run_id",
        "timestamp",
        "db_path",
        "cases_path",
        "top_k",
        "synthetic_db",
        "total_cases",
        "evaluated_cases",
        "skipped_cases",
        "top_1_hit_rate",
        "top_3_hit_rate",
        "top_k_hit_rate",
        "provenance_present_rate",
        "average_latency_ms",
        "notes",
    ]
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k) for k in fields})


def compare_previous(current: dict[str, Any], current_cases: list[dict[str, Any]], history: list[dict[str, Any]]) -> dict[str, Any]:
    if not history:
        return {"available": False, "notes": "no previous run available"}
    previous = history[-1]
    prev_path = Path(previous.get("output_dir", "")) / "memory_eval_results.json"
    previous_cases: list[dict[str, Any]] = []
    if prev_path.exists():
        try:
            previous_cases = json.loads(prev_path.read_text(encoding="utf-8")).get("per_case_results", [])
        except Exception:
            previous_cases = []
    prev_by_id = {r.get("case_id"): r for r in previous_cases}
    cur_by_id = {r.get("case_id"): r for r in current_cases}
    improved, regressed, newly_failing, newly_passing = [], [], [], []
    for case_id in sorted(set(prev_by_id) & set(cur_by_id)):
        prev_hit = bool(prev_by_id[case_id].get("top_k_hit"))
        cur_hit = bool(cur_by_id[case_id].get("top_k_hit"))
        prev_rank = prev_by_id[case_id].get("best_hit_rank") or 9999
        cur_rank = cur_by_id[case_id].get("best_hit_rank") or 9999
        if not prev_hit and cur_hit:
            newly_passing.append(case_id)
        elif prev_hit and not cur_hit:
            newly_failing.append(case_id)
        elif cur_rank < prev_rank:
            improved.append(case_id)
        elif cur_rank > prev_rank:
            regressed.append(case_id)
    metrics = ["top_1_hit_rate", "top_3_hit_rate", "top_k_hit_rate", "provenance_present_rate", "average_latency_ms"]
    deltas = {m: round(float(current.get(m, 0.0)) - float(previous.get(m, 0.0)), 4) for m in metrics}
    return {
        "available": True,
        "previous_eval_run_id": previous.get("eval_run_id"),
        "previous_output_dir": previous.get("output_dir"),
        "metric_deltas": deltas,
        "improved_cases": improved,
        "regressed_cases": regressed,
        "newly_failing_cases": newly_failing,
        "newly_passing_cases": newly_passing,
        "added_cases": sorted(set(cur_by_id) - set(prev_by_id)),
        "removed_cases": sorted(set(prev_by_id) - set(cur_by_id)),
    }


def write_report(path: Path, config: dict[str, Any], summary: dict[str, Any], rows: list[dict[str, Any]], comparison: dict[str, Any] | None) -> None:
    lines = [
        "# IVY Memory Retrieval Eval",
        "",
        f"- Output: `{path.parent}`",
        f"- DB: `{config['db_path']}`",
        f"- Cases: `{config['cases_path']}`",
        f"- Top K: `{config['top_k']}`",
        f"- Synthetic DB: `{config['synthetic_db']}`",
        "",
        "## Summary",
        "",
    ]
    for key in ("total_cases", "evaluated_cases", "skipped_cases", "top_1_hit_rate", "top_3_hit_rate", "top_k_hit_rate", "provenance_present_rate", "average_latency_ms"):
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.extend([
        "",
        "## Per Case",
        "",
        "| case | mode | top1 | top3 | topk | provenance | latency_ms | top result |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ])
    for row in rows:
        lines.append(
            f"| {row['case_id']} | {row['search_mode']} | {row['top_1_hit']} | {row['top_3_hit']} | "
            f"{row['top_k_hit']} | {row['provenance_ok']} | {row['latency_ms']} | {short_text(row['top_result_text_short'], 80)} |"
        )
    misses = [r for r in rows if not r["top_k_hit"]]
    lines.extend(["", "## Top Misses", ""])
    if misses:
        for row in misses[:10]:
            lines.append(f"- `{row['case_id']}`: {row['query']}")
    else:
        lines.append("- None.")
    if comparison:
        lines.extend(["", "## Comparison", ""])
        if not comparison.get("available"):
            lines.append("- no previous run available")
        else:
            lines.append(f"- Previous run: `{comparison.get('previous_eval_run_id')}`")
            lines.append(f"- Previous output: `{comparison.get('previous_output_dir')}`")
            lines.append(f"- Metric deltas: `{comparison.get('metric_deltas')}`")
            lines.append(f"- Improvements: `{comparison.get('improved_cases')}`")
            lines.append(f"- Regressions: `{comparison.get('regressed_cases')}`")
            lines.append(f"- Newly passing: `{comparison.get('newly_passing_cases')}`")
            lines.append(f"- Newly failing: `{comparison.get('newly_failing_cases')}`")
    if summary.get("top_k_hit_rate", 0.0) < 1.0:
        lines.extend(["", "## Sparse DB Note", "", "- Some expected memories were not retrieved. This can be normal before relevant artifacts are ingested."])
    lines.extend(["", "## Next Recommended Action", ""])
    if config["synthetic_db"]:
        lines.append("- Run the same eval against the real memory DB after ingesting recent runs.")
    else:
        lines.append("- Ingest relevant run artifacts, rerun with `--compare-latest`, and inspect misses before any prompt injection experiment.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate passive IVY memory retrieval quality.")
    parser.add_argument("--cases", required=True)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--build-synthetic-db", action="store_true")
    parser.add_argument("--compare-latest", action="store_true")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    args = parser.parse_args()

    cases = load_cases(args.cases)
    if args.dry_run:
        payload = {"cases_path": args.cases, "case_count": len(cases), "case_ids": [c.id for c in cases], "schema_ok": True}
        print(json.dumps(payload, indent=2) if args.json else f"Loaded {len(cases)} cases; schema validation passed.")
        return

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_dir = output_root / run_id
    output_dir.mkdir(parents=True, exist_ok=False)

    db_path = output_dir / "synthetic_memory.sqlite3" if args.build_synthetic_db else Path(args.db)
    if args.build_synthetic_db:
        build_synthetic_db(db_path)
    else:
        MemoryStore(db_path).init_schema()

    config = {
        "eval_run_id": run_id,
        "timestamp": run_id,
        "db_path": str(db_path),
        "cases_path": str(Path(args.cases)),
        "top_k": args.top_k,
        "synthetic_db": bool(args.build_synthetic_db),
        "output_dir": str(output_dir),
    }

    previous_history = load_history(output_root) if args.compare_latest else []
    rows, summary = evaluate_cases(cases, db_path, args.top_k)
    history_row = {**config, **summary, "notes": "synthetic" if args.build_synthetic_db else ""}
    comparison = compare_previous(history_row, rows, previous_history) if args.compare_latest else None

    (output_dir / "memory_eval_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    write_csv(output_dir / "memory_eval_results.csv", rows)
    payload = {"config": config, "summary": summary, "per_case_results": rows, "comparison_vs_previous": comparison}
    (output_dir / "memory_eval_results.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(output_dir / "memory_eval_report.md", config, summary, rows, comparison)
    append_history(output_root, history_row)

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"memory eval run: {output_dir}")
        print(f"top_1_hit_rate: {summary['top_1_hit_rate']}")
        print(f"top_3_hit_rate: {summary['top_3_hit_rate']}")
        print(f"top_k_hit_rate: {summary['top_k_hit_rate']}")
        print(f"provenance_present_rate: {summary['provenance_present_rate']}")
        if comparison:
            print(comparison.get("notes") or f"compared with {comparison.get('previous_eval_run_id')}")


if __name__ == "__main__":
    main()
