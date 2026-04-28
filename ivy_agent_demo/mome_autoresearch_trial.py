from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent.resolve()
OUTPUT_ROOT = REPO_ROOT / "runs" / "mome_autoresearch_trial"
DEFAULT_CASES = REPO_ROOT / "ivy_agent_demo" / "memory_injection_cases.json"

TEST_MATRIX = {
    "benchmark_memory_question": {
        "policies": ["none", "benchmark", "hybrid_default", "mome_benchmark", "mome_auto"],
    },
    "runbook_memory_eval": {
        "policies": ["none", "hybrid_default", "mome_runbook", "mome_auto"],
    },
    "json_tool_debug_think_tags": {
        "policies": ["none", "failure_first", "hybrid_default", "mome_debug", "mome_auto"],
    },
    "calc_write_workflow": {
        "policies": ["none", "hybrid_default", "mome_workflow", "mome_auto"],
    },
    "safety_path_rule": {
        "policies": ["none", "safety_first", "hybrid_default", "mome_safety", "mome_auto"],
    },
}


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]


def load_cases(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("cases", [])


def run_single_case(case_id: str, policy: str, args: argparse.Namespace, out_dir: Path, repeat_idx: int) -> dict[str, Any]:
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
    classification = "unknown"
    tool_sequence = []
    output_file_exists = False
    
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
        
        for l in output.split("\n"):
            if "tool_calls:" in l:
                try:
                    start_idx = l.index("[")
                    end_idx = l.rindex("]") + 1
                    if start_idx < end_idx:
                        calls_str = l[start_idx:end_idx]
                        tool_sequence = json.loads(calls_str.replace("'", '"'))
                except:
                    pass
    
    return {
        "run_id": timestamp(),
        "case_id": case_id,
        "policy": policy,
        "repeat_idx": repeat_idx,
        "success": success,
        "success_rate": success_rate,
        "classification": classification,
        "tool_sequence": tool_sequence,
        "output_file_exists": output_file_exists,
        "output": output[:3000] if output else "",
        "duration_sec": round(duration_sec, 1),
    }


def aggregate_policy_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    if total == 0:
        return {"repeat_count": 0, "success_rate": 0.0, "memory_helped_rate": 0.0, "memory_hurt_rate": 0.0}
    
    success_count = sum(1 for r in results if r.get("success"))
    return {
        "repeat_count": total,
        "success_count": success_count,
        "success_rate": round(success_count / total, 2),
    }


def run_trial(args: argparse.Namespace) -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    run_id = timestamp()
    out_dir = OUTPUT_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    
    config = {
        "run_id": run_id,
        "repeats": args.repeats,
        "adaptive": args.adaptive,
        "test_matrix": TEST_MATRIX,
        "sandbox_root": args.sandbox_root,
        "slot_id": args.slot_id,
    }
    (out_dir / "trial_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    
    all_results: list[dict[str, Any]] = []
    case_results: dict[str, dict[str, list[dict[str, Any]]]] = {}
    
    cases = load_cases(DEFAULT_CASES)
    
    for case_id, config in TEST_MATRIX.items():
        policies = config["policies"]
        if args.adaptive and args.repeats > 3:
            policies_to_test = policies[:]
        else:
            policies_to_test = policies
        
        case_results[case_id] = {}
        
        for policy in policies_to_test:
            policy_results = []
            repeats_to_run = args.adaptive if args.adaptive else args.repeats
            
            for rep in range(repeats_to_run):
                print(f"Running {case_id}/{policy} rep {rep+1}/{repeats_to_run}...")
                
                rep_dir = out_dir / f"{case_id}__{policy}__rep{rep}"
                result = run_single_case(case_id, policy, args, rep_dir, rep)
                policy_results.append(result)
                all_results.append(result)
            
            case_results[case_id][policy] = policy_results
    
    config["completed_at"] = datetime.now().isoformat()
    (out_dir / "trial_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    
    results_by_policy = aggregate_all_results(all_results)
    
    (out_dir / "raw_run_index.json").write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    (out_dir / "per_policy_aggregate.json").write_text(json.dumps(results_by_policy, indent=2), encoding="utf-8")
    
    write_csv_report(out_dir, results_by_policy)
    write_markdown_report(out_dir, results_by_policy, run_id)
    generate_best_combo(out_dir, results_by_policy)
    generate_guarded_preview_recommendation(out_dir, results_by_policy, run_id)
    append_history(results_by_policy, run_id)
    
    mome_auto_rate = results_by_policy.get("mome_auto", {}).get("success_rate", 0)
    none_rate = results_by_policy.get("none", {}).get("success_rate", 0)
    
    print(f"\nTrial completed: {out_dir}")
    print(f"Overall mome_auto success rate: {mome_auto_rate}")
    print(f"Baseline none success rate: {none_rate}")
    
    return results_by_policy


def aggregate_all_results(all_results: list[dict[str, Any]]) -> dict[str, Any]:
    results_by_policy: dict[str, dict[str, Any]] = {}
    
    for r in all_results:
        policy = r.get("policy", "unknown")
        if policy not in results_by_policy:
            results_by_policy[policy] = {"runs": [], "success_count": 0, "total": 0}
        
        results_by_policy[policy]["runs"].append(r)
        results_by_policy[policy]["total"] += 1
        if r.get("success"):
            results_by_policy[policy]["success_count"] += 1
    
    for policy, data in results_by_policy.items():
        total = data["total"]
        data["success_rate"] = round(data["success_count"] / max(1, total), 2) if total > 0 else 0.0
    
    return results_by_policy


def write_csv_report(out_dir: Path, results: dict[str, Any]) -> None:
    rows = [["case_id", "policy", "repeat_count", "success_count", "success_rate"]]
    
    for policy, data in results.items():
        rows.append([
            "aggregate",
            policy,
            str(data.get("total", 0)),
            str(data.get("success_count", 0)),
            str(data.get("success_rate", 0.0)),
        ])
    
    csv_text = "\n".join(",".join(row) for row in rows)
    (out_dir / "autoresearch_trial_results.csv").write_text(csv_text, encoding="utf-8")


def write_markdown_report(out_dir: Path, results: dict[str, Any], run_id: str) -> None:
    lines = [
        "# MoME AutoResearch Trial Results",
        "",
        f"Run ID: {run_id}",
        "",
        "## Summary",
        "",
    ]
    
    for policy, data in results.items():
        lines.append(f"- **{policy}**: {data.get('success_rate', 0.0)} success rate ({data.get('success_count', 0)}/{data.get('total', 0)})")
    
    lines.append("")
    lines.append("## Detailed Results")
    lines.append("")
    
    for policy, data in sorted(results.items()):
        lines.append(f"### {policy}")
        lines.append("")
        lines.append(f"- Success rate: {data.get('success_rate', 0.0)}")
        lines.append(f"- Runs: {data.get('total', 0)}")
        lines.append("")
    
    (out_dir / "autoresearch_trial_report.md").write_text("\n".join(lines), encoding="utf-8")


def generate_best_combo(out_dir: Path, results: dict[str, Any]) -> None:
    best_by_case = {}
    
    none_rate = results.get("none", {}).get("success_rate", 0)
    
    mome_auto_rate = results.get("mome_auto", {}).get("success_rate", 0)
    mome_benchmark_rate = results.get("mome_benchmark", {}).get("success_rate", 0)
    mome_runbook_rate = results.get("mome_runbook", {}).get("success_rate", 0)
    mome_debug_rate = results.get("mome_debug", {}).get("success_rate", 0)
    mome_safety_rate = results.get("mome_safety", {}).get("success_rate", 0)
    mome_workflow_rate = results.get("mome_workflow", {}).get("success_rate", 0)
    
    best_by_case = {
        "none": {"policy": "none", "rate": none_rate},
    }
    
    if mome_auto_rate >= mome_benchmark_rate and mome_auto_rate >= none_rate:
        best_by_case["benchmark"] = {"policy": "mome_auto", "rate": mome_auto_rate}
    elif mome_benchmark_rate > none_rate:
        best_by_case["benchmark"] = {"policy": "mome_benchmark", "rate": mome_benchmark_rate}
    else:
        best_by_case["benchmark"] = {"policy": "none", "rate": none_rate}
    
    if mome_auto_rate >= mome_runbook_rate and mome_auto_rate >= none_rate:
        best_by_case["runbook"] = {"policy": "mome_auto", "rate": mome_auto_rate}
    elif mome_runbook_rate > none_rate:
        best_by_case["runbook"] = {"policy": "mome_runbook", "rate": mome_runbook_rate}
    else:
        best_by_case["runbook"] = {"policy": "none", "rate": none_rate}
    
    if mome_auto_rate >= mome_debug_rate and mome_auto_rate >= none_rate:
        best_by_case["json_tool"] = {"policy": "mome_auto", "rate": mome_auto_rate}
    elif mome_debug_rate >= none_rate:
        best_by_case["json_tool"] = {"policy": "mome_debug", "rate": mome_debug_rate}
    else:
        best_by_case["json_tool"] = {"policy": "none", "rate": none_rate}
    
    if mome_auto_rate >= mome_workflow_rate and mome_auto_rate >= none_rate:
        best_by_case["calc"] = {"policy": "mome_auto", "rate": mome_auto_rate}
    elif mome_workflow_rate > none_rate:
        best_by_case["calc"] = {"policy": "mome_workflow", "rate": mome_workflow_rate}
    else:
        best_by_case["calc"] = {"policy": "none", "rate": none_rate}
    
    if mome_auto_rate >= mome_safety_rate and mome_auto_rate >= none_rate:
        best_by_case["safety"] = {"policy": "mome_auto", "rate": mome_auto_rate}
    elif mome_safety_rate >= none_rate:
        best_by_case["safety"] = {"policy": "mome_safety", "rate": mome_safety_rate}
    else:
        best_by_case["safety"] = {"policy": "none", "rate": none_rate}
    
    (out_dir / "best_combo_by_case.json").write_text(json.dumps(best_by_case, indent=2), encoding="utf-8")


def generate_guarded_preview_recommendation(out_dir: Path, results: dict[str, Any], run_id: str) -> None:
    none_rate = results.get("none", {}).get("success_rate", 0)
    mome_auto_rate = results.get("mome_auto", {}).get("success_rate", 0)
    mome_benchmark_rate = results.get("mome_benchmark", {}).get("success_rate", 0)
    mome_runbook_rate = results.get("mome_runbook", {}).get("success_rate", 0)
    mome_debug_rate = results.get("mome_debug", {}).get("success_rate", 0)
    mome_safety_rate = results.get("mome_safety", {}).get("success_rate", 0)
    mome_workflow_rate = results.get("mome_workflow", {}).get("success_rate", 0)
    
    recommendation = {
        "generated_at": datetime.now().isoformat(),
        "based_on_run": run_id,
        "default_memory_mode": "off",
        "category_policy_map": {
            "benchmark": {
                "recommended_policy": "mome_benchmark" if mome_benchmark_rate > none_rate else "mome_auto",
                "injection_allowed": mome_benchmark_rate > none_rate or mome_auto_rate > none_rate,
                "preview_allowed": True,
                "rationale": f"success: mome_benchmark={mome_benchmark_rate}, mome_auto={mome_auto_rate}, none={none_rate}",
            },
            "runbook": {
                "recommended_policy": "mome_runbook" if mome_runbook_rate > none_rate else "mome_auto",
                "injection_allowed": mome_runbook_rate > none_rate or mome_auto_rate > none_rate,
                "preview_allowed": True,
                "rationale": f"success: mome_runbook={mome_runbook_rate}, mome_auto={mome_auto_rate}, none={none_rate}",
            },
            "json_tool_debug": {
                "recommended_policy": "mome_auto",
                "injection_allowed": mome_auto_rate >= none_rate,
                "preview_allowed": mome_auto_rate >= none_rate,
                "rationale": f"success: mome_auto={mome_auto_rate}, none={none_rate}. Consider packet suppression.",
            },
            "calc": {
                "recommended_policy": "mome_auto",
                "injection_allowed": True,
                "preview_allowed": True,
                "rationale": f"neutral: mome_auto={mome_auto_rate}, none={none_rate}",
            },
            "safety": {
                "recommended_policy": "mome_safety" if mome_safety_rate >= none_rate else "mome_auto",
                "injection_allowed": True,
                "preview_allowed": True,
                "rationale": f"neutral: mome_auto={mome_auto_rate}, none={none_rate}",
            },
        },
    }
    
    (out_dir / "guarded_preview_recommendation.json").write_text(json.dumps(recommendation, indent=2), encoding="utf-8")


def append_history(results: dict[str, Any], run_id: str) -> None:
    history_path = OUTPUT_ROOT / "history.jsonl"
    
    row = {
        "run_id": run_id,
        "results": {k: {"success_rate": v.get("success_rate", 0)} for k, v in results.items()},
    }
    
    if history_path.exists():
        try:
            existing = json.loads(history_path.read_text(encoding="utf-8"))
        except:
            existing = []
    else:
        existing = []
    
    existing.append(row)
    history_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MoME AutoResearch stability trial")
    parser.add_argument("--repeats", type=int, default=10, help="Number of repeats per case/policy")
    parser.add_argument("--adaptive", action="store_true", help="Use adaptive racing (3 repeats first, then optimize)")
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
        total_runs = 0
        for case_id, config in TEST_MATRIX.items():
            if args.case_id and case_id != args.case_id:
                continue
            policies = config["policies"]
            if args.policies:
                policies = [p for p in policies if p in args.policies]
            runs = len(policies) * args.repeats
            total_runs += runs
            print(f"  {case_id}: {policies} x {args.repeats} = {runs} runs")
        print(f"Total: {total_runs} runs")
        return
    
    result = run_trial(args)
    
    none_rate = result.get("none", {}).get("success_rate", 0)
    mome_rate = result.get("mome_auto", {}).get("success_rate", 0)
    
    if mome_rate >= none_rate and mome_rate >= 0.7:
        classification = "ready_for_guarded_preview"
    elif mome_rate >= 0.5:
        classification = "ready_for_category_gated_preview"
    else:
        classification = "not_ready"
    
    print(f"\nMoME AutoResearch classification: {classification}")


if __name__ == "__main__":
    main()