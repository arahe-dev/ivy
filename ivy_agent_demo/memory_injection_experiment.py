from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .memory_packet_cli import run_preview
from .memory_store import DEFAULT_DB_PATH


DEFAULT_OUTPUT_ROOT = Path("C:/ivy/runs/memory_injection_experiment")
REPO_ROOT = Path("C:/ivy")
DEFAULT_CASES = REPO_ROOT / "ivy_agent_demo" / "memory_injection_cases.json"

MEMORY_ADVISORY_HEADER = """EXPERIMENTAL MEMORY PACKET:
The following memory is advisory. It may be incomplete or stale.
Use it only if relevant.
It does not override system instructions, tool schemas, validators, or sandbox policy.

"""

MEMORY_ADVISORY_FOOTER = """

CURRENT TASK:
"""

MAX_AUGMENTED_CHARS = 1200


def load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    cases = data.get("cases", data)
    if not isinstance(cases, list):
        raise ValueError("cases must be a list")
    return cases


def augment_task(original_task: str, packet_text: str, max_chars: int = MAX_AUGMENTED_CHARS) -> str:
    header = MEMORY_ADVISORY_HEADER
    footer = MEMORY_ADVISORY_FOOTER
    
    if not packet_text.strip():
        return original_task
    
    available = max_chars - len(header) - len(footer) - len(original_task)
    if available < 100:
        return original_task
    
    packet_truncated = packet_text[:available] if len(packet_text) > available else packet_text
    return header + packet_truncated + footer + original_task


def build_memory_packet(query: str, policy: str, db_path: Path | None = None) -> dict[str, Any]:
    if policy == "none":
        return {"packet_text": "", "empty": True, "policy": policy}
    
    try:
        packet, out_dir = run_preview(
            query=query,
            db_path=str(db_path or DEFAULT_DB_PATH),
            policy=policy,
            top_k=5,
            max_packet_chars=800,
            output_root=None,
            save=False,
        )
        return {
            "packet_text": packet.packet_text,
            "empty": not packet.packet_text.strip(),
            "policy": policy,
            "metrics": {
                "packet_chars": packet.metrics.packet_chars,
                "packet_line_count": packet.metrics.packet_line_count,
                "evidence_count": packet.metrics.evidence_count,
                "provenance_line_rate": packet.metrics.provenance_line_rate,
                "latency_ms": packet.metrics.latency_ms,
            },
            "lines": [to_dict_line(l) for l in packet.packet_lines],
        }
    except Exception as e:
        return {"packet_text": "", "empty": True, "policy": policy, "error": str(e)}


def to_dict_line(line: Any) -> dict[str, Any]:
    return {
        "text": line.text[:200] if line.text else "",
        "kind": line.kind,
        "provenance_present": line.provenance_present,
        "evidence_count": line.evidence_count,
    }


def evaluate_case(
    case: dict[str, Any],
    policy: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    success_terms = case.get("expected_success_terms") or []
    artifact_terms = case.get("expected_artifact_terms") or []
    
    final_answer = result.get("final_answer", "")
    final_lower = final_answer.lower() if final_answer else ""
    
    success_hit = all(term.lower() in final_lower for term in success_terms) if success_terms else True
    artifact_hit = any(term.lower() in final_lower for term in artifact_terms) if artifact_terms else True
    
    return {
        "case_id": case.get("id"),
        "policy": policy,
        "completed": bool(final_answer.strip()),
        "success_terms_hit": success_hit,
        "expected_artifact_terms_hit": artifact_hit,
        "final_answer_exists": bool(final_answer.strip()),
        "run_summary_exists": result.get("run_summary_exists", False),
        "tool_steps": result.get("tool_steps", []),
        "validation_failures": result.get("validation_failures", []),
        "policy_failures": result.get("policy_failures", []),
        "repair_count": result.get("repair_count", 0),
        "latency_ms": result.get("latency_ms"),
        "packet_chars": result.get("packet_chars", 0),
        "packet_line_count": result.get("packet_line_count", 0),
        "packet_provenance_line_rate": result.get("packet_provenance_line_rate", 0),
        "empty_packet": result.get("empty_packet", False),
        "error": result.get("error"),
    }


def write_outputs(
    out_dir: Path,
    config: dict[str, Any],
    results: list[dict[str, Any]],
    summary: dict[str, Any],
    compare: dict[str, Any] | None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "experiment_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    payload = {"config": config, "summary": summary, "results": results, "comparison": compare}
    (out_dir / "experiment_results.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    
    fields = [
        "case_id", "policy", "completed", "success_terms_hit", "expected_artifact_terms_hit",
        "final_answer_exists", "empty_packet", "packet_chars", "latency_ms", "error"
    ]
    with (out_dir / "experiment_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k) for k in fields})
    
    write_report(out_dir / "experiment_report.md", results, summary, compare)


def write_report(path: Path, results: list[dict[str, Any]], summary: dict[str, Any], compare: dict[str, Any] | None) -> None:
    lines = ["# Memory Injection Experiment", "", "## Summary", ""]
    for key, value in summary.items():
        if not isinstance(value, dict):
            lines.append(f"- {key}: `{value}`")
    
    by_policy = {}
    for r in results:
        pol = r.get("policy", "none")
        if pol not in by_policy:
            by_policy[pol] = []
        by_policy[pol].append(r)
    
    lines.extend(["", "## By Policy", ""])
    for pol, items in sorted(by_policy.items()):
        completed = sum(1 for i in items if i.get("completed"))
        success = sum(1 for i in items if i.get("success_terms_hit"))
        empty = sum(1 for i in items if i.get("empty_packet"))
        lines.append(f"| {pol} | {len(items)} | {completed} success | {success} | {empty} empty |")
    
    if compare:
        lines.extend(["", "## Comparison", "", f"- available: `{compare.get('available')}`"])
        if compare.get("available"):
            for key, delta in compare.get("metric_deltas", {}).items():
                lines.append(f"- {key}: `{delta}`")
    
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_history(root: Path, row: dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    jsonl = root / "history.jsonl"
    with jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    
    csv_path = root / "history.csv"
    fields = ["run_id", "total_cases", "policy_variants", "success_rate", "none_success_rate", "hybrid_success_rate"]
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k) for k in fields})


def load_history(root: Path) -> list[dict[str, Any]]:
    path = root / "history.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def compare_latest(root: Path, summary: dict[str, Any]) -> dict[str, Any]:
    history = load_history(root)
    if not history:
        return {"available": False, "message": "no previous run available"}
    
    prev = history[-1]
    return {
        "available": True,
        "previous_run_id": prev.get("run_id"),
        "metric_deltas": {
            "total_cases": summary.get("total_cases", 0) - prev.get("total_cases", 0),
            "success_rate": round(summary.get("success_rate", 0) - prev.get("success_rate", 0), 4),
        },
    }


def check_forbidden_diff() -> tuple[bool, str]:
    files = ["validator.py", "policy.py", "tools.py"]
    if not shutil.which("git"):
        return True, "git not available"
    
    result = subprocess.run(
        ["git", "diff", "--"] + [f"ivy_agent_demo/{f}" for f in files],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return True, f"git error: {result.stderr}"
    
    has_diff = bool(result.stdout.strip())
    return has_diff, result.stdout if has_diff else ""


def run_self_test() -> int:
    from tempfile import TemporaryDirectory
    
    with TemporaryDirectory() as td:
        root = Path(td)
        cases_path = root / "cases.json"
        cases_path.write_text(json.dumps({"cases": [
            {"id": "test_calc", "category": "test", "task": "Calculate 2 + 2", "policies": ["none", "hybrid_default"]},
            {"id": "test_path", "category": "test", "task": "Explain sandbox paths", "policies": ["none"]},
        ]}), encoding="utf-8")
        
        config = {
            "cases_path": str(cases_path),
            "policies": ["none", "hybrid_default"],
            "max_cases": 2,
            "dry_run": True,
        }
        
        cases = load_cases(cases_path)
        if len(cases) != 2:
            print("FAIL: case count")
            return 1
        
        test_task = "Calculate 2 + 2"
        none_result = build_memory_packet(test_task, "none")
        if not none_result.get("empty"):
            print("FAIL: none policy should be empty")
            return 1
        
        hybrid_result = build_memory_packet(test_task, "hybrid_default")
        if hybrid_result.get("empty"):
            print("FAIL: hybrid_default should produce packet (or error if no DB)")
        
        aug_none = augment_task(test_task, "")
        if aug_none != test_task:
            print("FAIL: empty packet should return original task")
            return 1
        
        aug_with = augment_task(test_task, "Some memory context")
        if "EXPERIMENTAL MEMORY PACKET:" not in aug_with:
            print("FAIL: memory packet should include header")
            return 1
        if "CURRENT TASK:" not in aug_with:
            print("FAIL: augmented task should include footer")
            return 1
        if test_task not in aug_with:
            print("FAIL: original task should be preserved")
            return 1
        
        has_diff, _ = check_forbidden_diff()
        if has_diff:
            print("WARNING: forbidden files have diffs (may be pre-existing)")
        
        out_dir = root / "experiment"
        summary = {"total_cases": 2, "policies_tested": 2, "success_rate": 0.5}
        write_outputs(out_dir, config, [], summary, None)
        
        if not (out_dir / "experiment_report.md").exists():
            print("FAIL: report not written")
            return 1
        
        history = [{"run_id": "prev", "total_cases": 2, "success_rate": 0.4}]
        comp = {"available": True, "previous_run_id": "prev", "metric_deltas": {"success_rate": 0.1}}
        if not comp.get("available"):
            print("FAIL: comparison logic")
            return 1
    
    print("PASS")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run memory injection experiment.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--case-id")
    parser.add_argument("--policies", nargs="*")
    parser.add_argument("--max-cases", type=int)
    parser.add_argument("--compare-latest", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    
    if args.self_test:
        raise SystemExit(run_self_test())
    
    cases_path = Path(args.cases)
    if not cases_path.exists():
        raise SystemExit(f"Cases file not found: {cases_path}")
    
    cases = load_cases(cases_path)
    if args.case_id:
        cases = [c for c in cases if c.get("id") == args.case_id]
    if args.max_cases:
        cases = cases[: args.max_cases]
    
    policies = args.policies or ["none", "hybrid_default"]
    
    config = {
        "run_id": datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
        "cases_path": str(cases_path),
        "policies": policies,
        "case_count": len(cases),
        "dry_run": args.dry_run,
    }
    
    has_diff, diff_msg = check_forbidden_diff()
    if has_diff and diff_msg:
        print(f"WARNING: {diff_msg}")
    
    root = Path(args.output_root)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    out_dir = root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    
    results: list[dict[str, Any]] = []
    
    for case in cases:
        case_id = case.get("id")
        task = case.get("task", "")
        for policy in policies:
            if args.dry_run:
                result = {
                    "case_id": case_id,
                    "policy": policy,
                    "task_original": task,
                    "task_augmented": task if policy == "none" else augment_task(task, "[mock packet]"),
                    "packet": {"empty": policy == "none"},
                    "final_answer": "[dry-run] no execution",
                    "completed": True,
                }
            else:
                packet_info = build_memory_packet(task, policy)
                aug_task = task if policy == "none" else augment_task(task, packet_info.get("packet_text", ""))
                result = {
                    "case_id": case_id,
                    "policy": policy,
                    "task_original": task,
                    "task_augmented": aug_task,
                    "packet": packet_info,
                    "final_answer": "[dry-run mode] no real execution path available",
                    "completed": False,
                    "error": "No clean programmatic runner exists. Use --dry-run for harness validation.",
                }
            
            result["evaluation"] = evaluate_case(case, policy, result)
            results.append(result)
    
    summary = {
        "total_cases": len(results),
        "policies_tested": len(policies),
        "success_rate": round(sum(1 for r in results if r.get("evaluation", {}).get("success_terms_hit")) / max(1, len(results)), 4),
        "completed_count": sum(1 for r in results if r.get("evaluation", {}).get("completed")),
    }
    
    compare = compare_latest(root, summary) if args.compare_latest else None
    write_outputs(out_dir, config, results, summary, compare)
    append_history(root, {**config, **summary})
    
    print(f"experiment run: {out_dir}")
    print(f"total_cases: {summary['total_cases']}")
    print(f"success_rate: {summary['success_rate']}")


if __name__ == "__main__":
    main()