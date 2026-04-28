from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent.resolve()
OUTPUT_ROOT = REPO_ROOT / "runs" / "mome_stability_trial"
DEFAULT_CASES = REPO_ROOT / "ivy_agent_demo" / "memory_injection_cases.json"

TEST_MATRIX = {
    "benchmark_memory_question": {
        "policies": ["none", "benchmark", "mome_benchmark", "mome_auto"],
    },
    "runbook_memory_eval": {
        "policies": ["none", "hybrid_default", "mome_runbook", "mome_auto"],
    },
    "json_tool_debug_think_tags": {
        "policies": ["none", "failure_first", "mome_debug", "mome_auto"],
    },
    "calc_write_workflow": {
        "policies": ["none", "hybrid_default", "mome_auto"],
    },
    "safety_path_rule": {
        "policies": ["none", "safety_first", "mome_safety", "mome_auto"],
    },
}


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]


def load_cases(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("cases", [])


def run_single_case(case_id: str, policy: str, args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "python",
        "-m",
        "ivy_agent_demo.memory_injection_experiment",
        "--cases", str(DEFAULT_CASES),
        "--case-id", case_id,
        "--policies", policy,
        "--sandbox-root", args.sandbox_root,
        "--slot-id", str(args.slot_id),
        "--output-root", str(out_dir),
    ]
    if args.stop_server_after:
        command.append("--stop-server-after")
    
    start = datetime.now()
    try:
        proc = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=args.experiment_timeout_sec,
        )
        output = proc.stdout + proc.stderr
    except subprocess.TimeoutExpired:
        output = "timeout"
    except Exception as e:
        output = str(e)
    
    duration_sec = (datetime.now() - start).total_seconds()
    
    success = False
    success_rate = 0.0
    
    if output:
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("success_rate:"):
                try:
                    success_rate = float(line.split(":")[1].strip())
                    success = success_rate > 0
                    break
                except:
                    pass
    
    return {
        "case_id": case_id,
        "policy": policy,
        "success": success,
        "success_rate": success_rate,
        "output": output[:2000] if output else "",
        "duration_sec": round(duration_sec, 1),
    }


def aggregate_policy_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    if total == 0:
        return {"repeat_count": 0, "success_count": 0, "success_rate": 0.0}
    
    success_count = sum(1 for r in results if r.get("success"))
    avg_rate = sum(r.get("success_rate", 0) for r in results) / total
    
    return {
        "repeat_count": total,
        "success_count": success_count,
        "success_rate": round(avg_rate, 2),
    }


def run_trial(args: argparse.Namespace) -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    run_id = timestamp()
    out_dir = OUTPUT_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    
    config = {
        "run_id": run_id,
        "repeats": args.repeats,
        "test_matrix": TEST_MATRIX,
        "sandbox_root": args.sandbox_root,
        "slot_id": args.slot_id,
    }
    (out_dir / "stability_trial_config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )
    
    all_results: list[dict[str, Any]] = []
    case_results: dict[str, dict[str, list[dict[str, Any]]]] = {}
    
    cases = load_cases(DEFAULT_CASES)
    case_map = {c["id"]: c for c in cases}
    
    for case_id, config in TEST_MATRIX.items():
        if args.case_id and case_id != args.case_id:
            continue
        policies = config["policies"]
        if args.policies:
            policies = [p for p in policies if p in args.policies]
        
        case_results[case_id] = {}
        
        for policy in policies:
            policy_results = []
            for rep in range(args.repeats):
                rep_dir = out_dir / f"{case_id}__{policy}__rep{rep}"
                print(f"Running {case_id}/{policy} rep {rep+1}/{args.repeats}...")
                
                result = run_single_case(case_id, policy, args, rep_dir)
                policy_results.append(result)
                all_results.append({
                    "run_id": run_id,
                    "case_id": case_id,
                    "policy": policy,
                    "repeat": rep,
                    **result,
                })
            
            case_results[case_id][policy] = policy_results
    
    config["completed_at"] = datetime.now().isoformat()
    (out_dir / "stability_trial_config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )
    
    summary = build_summary(case_results, all_results, run_id)
    
    (out_dir / "stability_trial_results.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    
    write_csv_report(out_dir, summary)
    write_markdown_report(out_dir, summary)
    append_history(summary)
    
    print(f"\nTrial completed: {out_dir}")
    print(f"Overall mome_auto success rate: {summary['mome_auto_success_rate']}")
    print(f"Baseline none success rate: {summary['baseline_none_success_rate']}")
    
    return summary


def build_summary(case_results: dict, all_results: list, run_id: str) -> dict[str, Any]:
    summary = {
        "run_id": run_id,
        "case_results": {},
        "mome_auto_success_rate": 0.0,
        "baseline_none_success_rate": 0.0,
        "best_legacy_success_rate": 0.0,
    }
    
    mome_auto_rates = []
    none_rates = []
    legacy_rates = []
    
    for case_id, policy_results in case_results.items():
        case_summary = {
            "policies": {},
            "best_policy": None,
            "best_rate": 0.0,
        }
        
        for policy, results in policy_results.items():
            agg = aggregate_policy_results(results)
            case_summary["policies"][policy] = agg
            
            if policy == "mome_auto":
                mome_auto_rates.append(agg["success_rate"])
            elif policy == "none":
                none_rates.append(agg["success_rate"])
            elif policy.startswith("mome_"):
                pass
            else:
                legacy_rates.append(agg["success_rate"])
            
            if agg["success_rate"] > case_summary["best_rate"]:
                case_summary["best_rate"] = agg["success_rate"]
                case_summary["best_policy"] = policy
        
        summary["case_results"][case_id] = case_summary
    
    if mome_auto_rates:
        summary["mome_auto_success_rate"] = round(sum(mome_auto_rates) / len(mome_auto_rates), 2)
    if none_rates:
        summary["baseline_none_success_rate"] = round(sum(none_rates) / len(none_rates), 2)
    if legacy_rates:
        summary["best_legacy_success_rate"] = round(max(legacy_rates) if legacy_rates else 0.0, 2)
    
    return summary


def write_csv_report(out_dir: Path, summary: dict[str, Any]) -> None:
    rows = [["case_id", "policy", "repeat_count", "success_count", "success_rate"]]
    
    for case_id, case_summary in summary.get("case_results", {}).items():
        for policy, stats in case_summary.get("policies", {}).items():
            rows.append([
                case_id,
                policy,
                str(stats.get("repeat_count", 0)),
                str(stats.get("success_count", 0)),
                str(stats.get("success_rate", 0.0)),
            ])
    
    csv_text = "\n".join(",".join(row) for row in rows)
    (out_dir / "stability_trial_results.csv").write_text(csv_text, encoding="utf-8")


def write_markdown_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# MoME v0 Stability Trial Results",
        "",
        f"Run ID: {summary['run_id']}",
        "",
        "## Summary",
        "",
        f"- mome_auto success rate: {summary.get('mome_auto_success_rate', 'N/A')}",
        f"- baseline none success rate: {summary.get('baseline_none_success_rate', 'N/A')}",
        f"- best legacy success rate: {summary.get('best_legacy_success_rate', 'N/A')}",
        "",
        "## Results by Case",
        "",
    ]
    
    for case_id, case_summary in summary.get("case_results", {}).items():
        lines.append(f"### {case_id}")
        lines.append("")
        lines.append("| Policy | Repeats | Success Rate |")
        lines.append("|--------|--------|-------------|")
        
        for policy, stats in case_summary.get("policies", {}).items():
            lines.append(f"| {policy} | {stats.get('repeat_count', 0)} | {stats.get('success_rate', 0.0)} |")
        
        lines.append("")
        lines.append(f"**Best**: {case_summary.get('best_policy', 'N/A')} ({case_summary.get('best_rate', 0.0)})")
        lines.append("")
    
    (out_dir / "stability_trial_report.md").write_text("\n".join(lines), encoding="utf-8")


def append_history(summary: dict[str, Any]) -> None:
    history_path = OUTPUT_ROOT / "history.jsonl"
    row = {
        "run_id": summary["run_id"],
        "mome_auto_success_rate": summary.get("mome_auto_success_rate"),
        "baseline_none_success_rate": summary.get("baseline_none_success_rate"),
        "best_legacy_success_rate": summary.get("best_legacy_success_rate"),
    }
    
    if history_path.exists():
        existing = json.loads(history_path.read_text(encoding="utf-8"))
    else:
        existing = []
    
    existing.append(row)
    history_path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MoME v0 stability trial")
    parser.add_argument("--repeats", type=int, default=2, help="Number of repeats per case/policy")
    parser.add_argument("--case-id", type=str, default=None, help="Run only specific case")
    parser.add_argument("--policies", nargs="+", default=None, help="Filter policies")
    parser.add_argument("--sandbox-root", default=str(REPO_ROOT / "sandbox"))
    parser.add_argument("--slot-id", type=int, default=99)
    parser.add_argument("--experiment-timeout-sec", type=int, default=600)
    parser.add_argument("--stop-server-after", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("Dry run - would execute:")
        for case_id, config in TEST_MATRIX.items():
            if args.case_id and case_id != args.case_id:
                continue
            policies = config["policies"]
            if args.policies:
                policies = [p for p in policies if p in args.policies]
            print(f"  {case_id}: {policies} x {args.repeats} = {len(policies) * args.repeats} runs")
        return
    
    result = run_trial(args)
    
    mome_rate = result.get("mome_auto_success_rate", 0)
    none_rate = result.get("baseline_none_success_rate", 0)
    
    if mome_rate >= none_rate and mome_rate >= 0.5:
        classification = "ready_for_guarded_preview"
    elif mome_rate >= 0.3:
        classification = "needs_more_case_specific_work"
    else:
        classification = "not_ready"
    
    print(f"\nMoME v0 classification: {classification}")


if __name__ == "__main__":
    main()