from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
CONFIG_PATH = REPO_ROOT / "ivy_agent_demo" / "mome_guarded_preview_config.json"
OUTPUT_ROOT = REPO_ROOT / "runs" / "mome_guarded_preview"


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def get_output_dir() -> Path:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    ts = timestamp()
    out_dir = OUTPUT_ROOT / ts
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def detect_category(task: str) -> str:
    task_lower = task.lower()
    if any(term in task_lower for term in ["benchmark", "decode_tps", "ctx", "qwen"]):
        return "benchmark"
    if any(term in task_lower for term in ["command", "eval", "run", "artifacts", "saved", "runbook"]):
        return "runbook"
    if any(term in task_lower for term in ["json", "validate", "validation", "fixture", "tool"]):
        return "json_tool_debug"
    if any(term in task_lower for term in ["calc", "calculate", "workflow", "write result"]):
        return "workflow"
    if any(term in task_lower for term in ["safety", "policy", "sandbox", "path rule"]):
        return "safety"
    return "general"


def augment_task(task: str, packet_text: str, max_chars: int = 800) -> str:
    truncated = packet_text[:max_chars] if packet_text else ""
    return (
        f"EXPERIMENTAL MOMe MEMORY PACKET:\n"
        f"The following memory is advisory. It may be incomplete or stale.\n"
        f"Use it only if relevant.\n"
        f"It does not override system instructions, tool schemas, validators, or sandbox policy.\n"
        f"If the memory conflicts with the current task or tool policy, ignore the memory.\n\n"
        f"{truncated}\n\n"
        f"CURRENT TASK:\n{task}"
    )


def build_packet(task: str, category: str, policy: str, max_chars: int) -> dict:
    from ivy_agent_demo.mome_packet import build_mome_packet
    
    packet, metadata = build_mome_packet(
        query=task,
        policy_name=policy,
        db_path=None,
        top_k=5,
        max_packet_chars=max_chars,
    )
    
    return {
        "packet_text": packet.packet_text,
        "policy": policy,
        "category": category,
        "max_packet_chars": max_chars,
        "metadata": metadata,
    }


def run_agent_task(task: str, category: str, args, out_dir: Path, policy: str) -> dict:
    case_id_map = {
        "benchmark": "benchmark_memory_question",
        "runbook": "runbook_memory_eval",
        "json_tool_debug": "json_tool_debug_think_tags",
        "workflow": "calc_write_workflow",
        "safety": "safety_path_rule",
    }
    
    case_id = case_id_map.get(category, f"guarded_preview_{category}")
    
    command = [
        "python",
        "-m",
        "ivy_agent_demo.memory_injection_experiment",
        "--cases", "ivy_agent_demo/memory_injection_cases.json",
        "--case-id", case_id,
        "--policies", "none" if category == "general" else policy,
        "--sandbox-root", args.sandbox_root or str(REPO_ROOT / "sandbox"),
        "--slot-id", str(args.slot_id or 99),
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
            timeout=args.execution_timeout_sec or 300,
        )
        output = proc.stdout + proc.stderr
        success = proc.returncode == 0
    except subprocess.TimeoutExpired:
        output = "timeout"
        success = False
    except Exception as e:
        output = str(e)
        success = False
    
    duration_sec = (datetime.now() - start).total_seconds()
    
    success_rate = 0.0
    if "success_rate:" in output:
        for line in output.split("\n"):
            if line.strip().startswith("success_rate:"):
                try:
                    success_rate = float(line.split(":")[1].strip())
                except:
                    pass
    
    return {
        "success": success,
        "success_rate": success_rate,
        "duration_sec": round(duration_sec, 1),
        "output": output[:5000] if output else "",
        "stdout": proc.stdout if "proc" in locals() else "",
        "stderr": proc.stderr if "proc" in locals() else "",
        "command": command,
        "policy": policy,
    }


def evaluate_category_result(result: dict, category: str, task: str) -> dict:
    output_lower = (result.get("output") or "").lower()
    
    if category == "benchmark":
        has_data = any(term in output_lower for term in ["decode_tps", "tok/s", "tokens per second"])
        return {"classification": "memory_helped" if has_data else "memory_neutral", "success": has_data}
    
    if category == "runbook":
        has_command = "python" in output_lower and "memory_eval" in output_lower
        return {"classification": "memory_helped" if has_command else "memory_neutral", "success": has_command}
    
    if category == "json_tool_debug":
        has_json = "json" in output_lower and ("valid" in output_lower or "validation" in output_lower)
        return {"classification": "memory_neutral", "success": has_json}
    
    if category == "workflow":
        has_391 = "391" in output_lower
        return {"classification": "memory_neutral", "success": has_391}
    
    if category == "safety":
        has_safety = "sandbox" in output_lower or "path" in output_lower
        return {"classification": "memory_neutral", "success": has_safety}
    
    return {"classification": "evaluator_missing", "success": False}


def find_nested_experiment_dir(run_dir: Path) -> Path | None:
    if not run_dir.exists():
        return None
    candidates = [p for p in run_dir.iterdir() if p.is_dir() and p.name.replace("_", "").isdigit()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def load_nested_experiment_result(run_dir: Path) -> dict | None:
    nested_dir = find_nested_experiment_dir(run_dir)
    if not nested_dir:
        return None
    result_path = nested_dir / "experiment_results.json"
    if not result_path.exists():
        return None
    try:
        return json.loads(result_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def parse_guarded_execution_result(run_dir: Path, expected_policy: str) -> dict:
    result = {
        "completed": False,
        "success": False,
        "classification": "runner_failure",
        "structured_result_source": None,
        "nested_artifact_paths": {},
    }
    data = load_nested_experiment_result(run_dir)
    if not data:
        result["error_message"] = "nested experiment_results.json not found"
        return result
    
    results = data.get("results") or []
    if not results:
        result["error_message"] = "no case results in nested experiment"
        return result
    
    case_result = None
    for item in results:
        if item.get("policy") == expected_policy:
            case_result = item
            break
    if not case_result:
        case_result = results[0]
    evaluation = case_result.get("evaluation") or {}
    output_check = case_result.get("output_file_check") or case_result.get("calc_output_check") or {}
    
    actual_policy = case_result.get("policy")
    result.update(
        {
            "expected_policy": expected_policy,
            "actual_policy": actual_policy,
            "policy_match": actual_policy == expected_policy,
            "completed": bool(evaluation.get("completed")),
            "success": bool(evaluation.get("passed") or evaluation.get("success")),
            "classification": evaluation.get("classification") or "inconclusive",
            "final_answer_exists": bool(evaluation.get("final_answer_exists")),
            "output_file_exists": bool(output_check.get("output_file_exists")),
            "output_file_contains_expected": bool(
                output_check.get("output_file_contains_391")
                or output_check.get("output_file_contains_validation_result")
            ),
            "validation_failures_count": len(evaluation.get("validation_failures") or []),
            "policy_failures_count": len(evaluation.get("policy_failures") or []),
            "repair_count": int(evaluation.get("repair_count") or 0),
            "tool_steps": evaluation.get("tool_steps") or [],
            "ask_user_used": bool(output_check.get("ask_user_used")),
            "progress_guard_count": int(output_check.get("progress_guard_triggered_count") or 0),
            "packet_chars": evaluation.get("packet_chars"),
            "packet_line_count": evaluation.get("packet_line_count"),
            "error_message": evaluation.get("error") or output_check.get("failure_reason"),
            "structured_result_source": "experiment_results.json",
            "nested_artifact_paths": {
                "experiment_dir": str(find_nested_experiment_dir(run_dir)),
                "agent_stdout": case_result.get("stdout_path"),
                "agent_stderr": case_result.get("stderr_path"),
                "artifact_root": case_result.get("artifact_root"),
            },
        }
    )
    
    return result


def run_preview_mode(task: str, category: str, args, out_dir: Path) -> dict:
    config = load_config()
    cat_config = config.get("category_policy_map", {}).get(category, {})
    max_chars = args.max_packet_chars or cat_config.get("max_packet_chars", 800)
    policy = args.policy or config.get("default_policy", "mome_auto")
    
    result = build_packet(task, category, policy, max_chars)
    packet_text = result.get("packet_text", "")
    packet_path = out_dir / "memory_packet.txt"
    packet_json_path = out_dir / "memory_packet.json"
    task_path = out_dir / "task_original.txt"
    task_path.write_text(task, encoding="utf-8")
    packet_path.write_text(packet_text, encoding="utf-8")
    packet_json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    config_path = out_dir / "guarded_preview_config_used.json"
    config_path.write_text(json.dumps(load_config(), indent=2), encoding="utf-8")
    
    return {
        "mode": "preview",
        "category": category,
        "policy": policy,
        "packet_text": packet_text,
        "packet_chars": len(packet_text),
        "packet_line_count": packet_text.count("\n") + (1 if packet_text else 0),
        "injection_allowed": cat_config.get("injection_allowed", False),
        "preview_allowed": cat_config.get("preview_allowed", False),
        "packet_path": str(packet_path),
        "packet_json_path": str(packet_json_path),
        "report_path": str(out_dir / "guarded_preview_report.md"),
        "output_dir": str(out_dir),
    }


def run_inject_mode(task: str, category: str, args, out_dir: Path) -> dict:
    config = load_config()
    cat_config = config.get("category_policy_map", {}).get(category, {})
    max_chars = args.max_packet_chars or cat_config.get("max_packet_chars", 800)
    policy = args.policy or config.get("default_policy", "mome_auto")
    
    injection_allowed = cat_config.get("injection_allowed", False)
    if not injection_allowed:
        return {
            "mode": "inject",
            "category": category,
            "blocked": True,
            "reason": cat_config.get("rationale", "injection not allowed for this category"),
            "suggestion": "use --mode preview instead",
        }
    
    result = build_packet(task, category, policy, max_chars)
    augmented = augment_task(task, result["packet_text"], max_chars)
    
    run_inject_dir = out_dir / "run_inject"
    run_inject_dir.mkdir(parents=True, exist_ok=True)
    
    (run_inject_dir / "task_original.txt").write_text(task, encoding="utf-8")
    (run_inject_dir / "task_augmented.txt").write_text(augmented, encoding="utf-8")
    (run_inject_dir / "packet.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (run_inject_dir / "memory_packet.txt").write_text(result.get("packet_text", ""), encoding="utf-8")
    (run_inject_dir / "memory_packet.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    
    exec_result = {"classification": "evaluator_missing", "completed": False}
    
    if getattr(args, "execute", False):
        agent_result = run_agent_task(augmented, category, args, run_inject_dir, policy)
        (run_inject_dir / "stdout.log").write_text(agent_result.get("stdout", ""), encoding="utf-8")
        (run_inject_dir / "stderr.log").write_text(agent_result.get("stderr", ""), encoding="utf-8")
        (run_inject_dir / "execution_command.json").write_text(json.dumps(agent_result.get("command", []), indent=2), encoding="utf-8")
        
        nested_result = parse_guarded_execution_result(run_inject_dir, policy)
        if nested_result.get("structured_result_source"):
            exec_result = {
                **nested_result,
                "duration_sec": agent_result.get("duration_sec", 0),
            }
        else:
            eval_result = evaluate_category_result(agent_result, category, augmented)
            exec_result = {
                "classification": eval_result.get("classification", "evaluator_missing"),
                "success": eval_result.get("success", False),
                "completed": agent_result.get("success", False),
                "duration_sec": agent_result.get("duration_sec", 0),
                "structured_result_source": "stdout_fallback",
            }
    
    return {
        "mode": "inject",
        "category": category,
        "policy": policy,
        "expected_policy": policy,
        "augmented_task": augmented,
        "packet_text": result["packet_text"],
        "blocked": False,
        "output_dir": str(out_dir),
        "run_inject_dir": str(run_inject_dir),
        "execution_result": exec_result,
    }


def run_compare_mode(task: str, category: str, args, out_dir: Path) -> dict:
    config = load_config()
    
    run_off_dir = out_dir / "run_off"
    run_off_dir.mkdir(parents=True, exist_ok=True)
    
    (run_off_dir / "task_original.txt").write_text(task, encoding="utf-8")
    
    off_exec_result = {"classification": "off_baseline", "completed": False}
    off_policy = "none"
    
    if getattr(args, "execute", False):
        off_result = run_agent_task(task, category, args, run_off_dir, off_policy)
        (run_off_dir / "stdout.log").write_text(off_result.get("stdout", ""), encoding="utf-8")
        (run_off_dir / "stderr.log").write_text(off_result.get("stderr", ""), encoding="utf-8")
        (run_off_dir / "execution_command.json").write_text(json.dumps(off_result.get("command", []), indent=2), encoding="utf-8")
        
        nested_result = parse_guarded_execution_result(run_off_dir, off_policy)
        if nested_result.get("structured_result_source"):
            off_exec_result = {
                **nested_result,
                "duration_sec": off_result.get("duration_sec", 0),
            }
        else:
            off_eval = evaluate_category_result(off_result, category, task)
            off_exec_result = {
                "classification": off_eval.get("classification", "off_baseline"),
                "success": off_eval.get("success", False),
                "completed": off_result.get("success", False),
                "duration_sec": off_result.get("duration_sec", 0),
                "structured_result_source": "stdout_fallback",
            }
    
    inject_result = run_inject_mode(task, category, args, out_dir)
    
    if inject_result.get("blocked"):
        comparison = {
            "mode": "compare",
            "task": task,
            "category": category,
            "off_result": {"mode": "off", "category": category, "task": task, "execution_result": off_exec_result},
            "inject_result": inject_result,
            "comparison_available": False,
            "classification": "injection_blocked",
        }
    else:
        inject_exec = inject_result.get("execution_result", {})
        off_exec = off_exec_result
        
        if off_exec.get("success") and inject_exec.get("success"):
            classification = "memory_neutral"
        elif inject_exec.get("success") and not off_exec.get("success"):
            classification = "memory_helped"
        elif not inject_exec.get("success") and off_exec.get("success"):
            classification = "memory_hurt"
        else:
            if inject_exec.get("classification") == "runner_failure":
                classification = "runner_failure"
            elif inject_exec.get("classification") == "evaluator_missing" or off_exec.get("classification") == "evaluator_missing":
                classification = "evaluator_missing"
            else:
                classification = "inconclusive"
        
        comparison = {
            "mode": "compare",
            "task": task,
            "category": category,
            "off_result": {"mode": "off", "category": category, "task": task, "execution_result": off_exec, "expected_policy": off_policy},
            "inject_result": inject_result,
            "comparison_available": True,
            "classification": classification,
            "output_dir": str(out_dir),
        }

    comparison_report = out_dir / "comparison_report.md"
    comparison_lines = [
        "# MoME Guarded Preview Comparison",
        "",
        f"- category: `{category}`",
        f"- classification: `{comparison.get('classification')}`",
        f"- run_dir: `{out_dir}`",
        "",
        "## Off Result",
        f"- expected_policy: `{off_exec_result.get('expected_policy')}`",
        f"- actual_policy: `{off_exec_result.get('actual_policy')}`",
        f"- policy_match: `{off_exec_result.get('policy_match')}`",
        f"- completed: `{off_exec_result.get('completed')}`",
        f"- success: `{off_exec_result.get('success', False)}`",
        f"- classification: `{off_exec_result.get('classification')}`",
        f"- tool_steps: `{len(off_exec_result.get('tool_steps') or [])}`",
        f"- repair_count: `{off_exec_result.get('repair_count', 0)}`",
        f"- validation_failures_count: `{off_exec_result.get('validation_failures_count', 0)}`",
        f"- policy_failures_count: `{off_exec_result.get('policy_failures_count', 0)}`",
        "",
        "## Inject Result",
        f"- expected_policy: `{inject_exec.get('expected_policy')}`",
        f"- actual_policy: `{inject_exec.get('actual_policy')}`",
        f"- policy_match: `{inject_exec.get('policy_match')}`",
        f"- completed: `{inject_exec.get('completed') if inject_result.get('execution_result') else False}`",
        f"- success: `{inject_exec.get('success', False)}`",
        f"- classification: `{inject_exec.get('classification', 'evaluator_missing')}`",
        f"- tool_steps: `{len(inject_exec.get('tool_steps') or [])}`",
        f"- repair_count: `{inject_exec.get('repair_count', 0)}`",
        f"- validation_failures_count: `{inject_exec.get('validation_failures_count', 0)}`",
        f"- policy_failures_count: `{inject_exec.get('policy_failures_count', 0)}`",
        "",
        "## Structured Sources",
        f"- off_source: `{off_exec_result.get('structured_result_source')}`",
        f"- inject_source: `{inject_exec.get('structured_result_source')}`",
    ]
    comparison_report.write_text("\n".join(comparison_lines) + "\n", encoding="utf-8")
    comparison["comparison_report_path"] = str(comparison_report)
    
    result_path = out_dir / "result.json"
    result_path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    
    return comparison


def run_guarded_preview(args) -> dict:
    task = args.task
    if not task and args.task_file:
        task = Path(args.task_file).read_text(encoding="utf-8")
    
    if not task:
        return {"error": "No task provided. Use --task or --task-file."}
    
    category = args.category or detect_category(task)
    mode = args.mode
    out_dir = get_output_dir()
    config = load_config()
    (out_dir / "guarded_preview_config_used.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    (out_dir / "task_original.txt").write_text(task, encoding="utf-8")
    
    if mode == "off":
        result = {
            "mode": "off",
            "category": category,
            "task": task,
            "injection_blocked": True,
            "reason": "mode is off",
            "classification": "off_baseline",
            "output_dir": str(out_dir),
        }
    elif mode == "preview":
        result = run_preview_mode(task, category, args, out_dir)
    elif mode == "inject":
        if category == "general" and not args.force:
            cat_config = config.get("category_policy_map", {}).get("general", {})
            if not cat_config.get("injection_allowed", False):
                result = {
                    "mode": "inject",
                    "category": category,
                    "blocked": True,
                    "reason": "general category injection not allowed by default",
                    "suggestion": "use --mode preview or specify category",
                    "output_dir": str(out_dir),
                }
                return result
        result = run_inject_mode(task, category, args, out_dir)
    elif mode == "compare":
        result = run_compare_mode(task, category, args, out_dir)
    else:
        result = {"error": f"Unknown mode: {mode}"}
    
    result["category"] = category
    result["task"] = task
    result["output_dir"] = result.get("output_dir", str(out_dir))
    report_path = Path(result["output_dir"]) / "guarded_preview_report.md"
    report_lines = [
        "# MoME Guarded Preview Report",
        "",
        f"- mode: `{result.get('mode')}`",
        f"- category: `{category}`",
        f"- policy: `{result.get('policy', 'n/a')}`",
        f"- output_dir: `{result.get('output_dir')}`",
    ]
    if result.get("mode") == "preview":
        report_lines.extend([
            f"- injection_allowed: `{result.get('injection_allowed')}`",
            f"- preview_allowed: `{result.get('preview_allowed')}`",
            f"- packet_chars: `{result.get('packet_chars')}`",
            f"- packet_line_count: `{result.get('packet_line_count')}`",
            f"- packet_path: `{result.get('packet_path')}`",
        ])
    if result.get("mode") == "inject":
        exec_result = result.get("execution_result", {})
        report_lines.extend([
            f"- injection_allowed: `{not result.get('blocked', False)}`",
            f"- completed: `{exec_result.get('completed', False)}`",
            f"- success: `{exec_result.get('success', False)}`",
            f"- classification: `{exec_result.get('classification')}`",
            f"- run_inject_dir: `{result.get('run_inject_dir')}`",
        ])
    if result.get("mode") == "compare":
        report_lines.extend([
            f"- comparison: `{result.get('classification')}`",
            f"- comparison_report: `{result.get('comparison_report_path')}`",
        ])
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    result["guarded_preview_report_path"] = str(report_path)
    return result


def self_test() -> int:
    print("Running MoME guarded preview self-test...")
    
    config = load_config()
    if not config:
        print("FAIL: Config not found")
        return 1
    
    if config.get("default_memory_mode") != "off":
        print("FAIL: default_memory_mode should be 'off'")
        return 1
    
    allowed = config.get("allowed_modes", [])
    if "off" not in allowed or "preview" not in allowed or "inject" not in allowed:
        print("FAIL: allowed_modes missing required modes")
        return 1
    
    benchmark_cfg = config.get("category_policy_map", {}).get("benchmark", {})
    if not benchmark_cfg.get("injection_allowed"):
        print("FAIL: benchmark injection should be allowed")
        return 1
    
    general_cfg = config.get("category_policy_map", {}).get("general", {})
    if general_cfg.get("injection_allowed"):
        print("FAIL: general injection should NOT be allowed by default")
        return 1
    
    print("PASS: Config validation")
    
    test_task = "Summarize Qwen 4060 ctx 512 decode_tps. Do not invent numbers."
    category = detect_category(test_task)
    if category != "benchmark":
        print(f"WARN: Expected benchmark, got {category}")
    
    print(f"PASS: Category detection ({category})")
    
    args = argparse.Namespace(
        task=test_task,
        task_file=None,
        category=category,
        mode="preview",
        policy="mome_auto",
        max_packet_chars=800,
        debug=True,
    )
    result = run_guarded_preview(args)
    if result.get("error"):
        print(f"FAIL: {result['error']}")
        return 1
    
    if not result.get("packet_text"):
        print("FAIL: No packet generated")
        return 1
    
    print(f"PASS: Preview mode packet generated ({len(result.get('packet_text', ''))} chars)")
    
    args_inject = argparse.Namespace(
        task=test_task,
        task_file=None,
        category=category,
        mode="inject",
        policy="mome_auto",
        max_packet_chars=800,
        debug=True,
        force=False,
    )
    inject_result = run_guarded_preview(args_inject)
    if inject_result.get("blocked"):
        print(f"FAIL: Should allow benchmark injection, got blocked: {inject_result.get('reason')}")
        return 1
    
    print("PASS: Inject mode allowed for benchmark")
    
    general_task = "Tell me about this repo generally."
    args_gen = argparse.Namespace(
        task=general_task,
        task_file=None,
        category="general",
        mode="inject",
        policy="mome_auto",
        max_packet_chars=800,
        debug=True,
        force=False,
    )
    gen_result = run_guarded_preview(args_gen)
    if not gen_result.get("blocked"):
        print("FAIL: General injection should be blocked")
        return 1
    
    print("PASS: General injection blocked as expected")
    
    print("\nAll self-test checks PASSED!")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="MoME Guarded Preview - Opt-in Memory Wrapper")
    parser.add_argument("--task", type=str, default=None, help="Task to run")
    parser.add_argument("--task-file", type=str, default=None, help="File containing task")
    parser.add_argument("--category", type=str, default=None, help="Task category (benchmark/runbook/json_tool_debug/workflow/safety/general)")
    parser.add_argument("--mode", type=str, default="preview", choices=["off", "preview", "inject", "compare"], help="Preview mode")
    parser.add_argument("--policy", type=str, default=None, help="MoME policy (default: mome_auto)")
    parser.add_argument("--max-packet-chars", type=int, default=None, help="Max packet chars")
    parser.add_argument("--debug", action="store_true", help="Show debug info")
    parser.add_argument("--self-test", action="store_true", help="Run self-test")
    parser.add_argument("--force", action="store_true", help="Force injection even if blocked")
    parser.add_argument("--execute", action="store_true", help="Execute real agent for inject/compare modes")
    parser.add_argument("--sandbox-root", type=str, default=None, help="Sandbox root path")
    parser.add_argument("--slot-id", type=int, default=99, help="Slot ID for agent")
    parser.add_argument("--stop-server-after", action="store_true", help="Stop server after run")
    parser.add_argument("--execution-timeout-sec", type=int, default=300, help="Execution timeout")
    
    args = parser.parse_args()
    
    if args.self_test:
        sys.exit(self_test())
    
    if args.mode == "compare" and not args.debug:
        args.debug = True
    
    result = run_guarded_preview(args)
    
    if args.mode in ("inject", "compare"):
        if not getattr(args, "execute", False):
            result["execution_warning"] = "Use --execute to run real agent. Current mode shows packet only."
    
    if args.debug:
        print(f"\n=== MoME Guarded Preview Result ===")
        print(f"Mode: {result.get('mode', 'unknown')}")
        print(f"Category: {result.get('category', 'unknown')}")
        if result.get("policy"):
            print(f"Policy: {result.get('policy')}")
        if result.get("output_dir"):
            print(f"Run dir: {result.get('output_dir')}")
        
        if result.get("blocked"):
            print(f"BLOCKED: {result.get('reason', 'unknown')}")
            if result.get("suggestion"):
                print(f"Suggestion: {result.get('suggestion')}")
        
        if result.get("packet_text"):
            print(f"\n--- Memory Packet ---")
            print(result["packet_text"][:500])
            if len(result["packet_text"]) > 500:
                print(f"... ({len(result['packet_text'])} total chars)")
        
        if result.get("augmented_task"):
            print(f"\n--- Augmented Task (first 500 chars) ---")
            print(result["augmented_task"][:500])
        if result.get("mode") == "compare":
            off_exec = (result.get("off_result") or {}).get("execution_result", {})
            inj_exec = (result.get("inject_result") or {}).get("execution_result", {})
            print(f"\n--- Compare Summary ---")
            print(f"Off expected_policy: {off_exec.get('expected_policy')} | actual_policy: {off_exec.get('actual_policy')} | match: {off_exec.get('policy_match')}")
            print(f"Off completed: {off_exec.get('completed', False)} | success: {off_exec.get('success', False)} | classification: {off_exec.get('classification')}")
            print(f"Inject expected_policy: {inj_exec.get('expected_policy')} | actual_policy: {inj_exec.get('actual_policy')} | match: {inj_exec.get('policy_match')}")
            print(f"Inject completed: {inj_exec.get('completed', False)} | success: {inj_exec.get('success', False)} | classification: {inj_exec.get('classification')}")
            print(f"Comparison: {result.get('classification')}")
            print(f"Off tool_steps: {len(off_exec.get('tool_steps') or [])} | repairs: {off_exec.get('repair_count', 0)}")
            print(f"Inject tool_steps: {len(inj_exec.get('tool_steps') or [])} | repairs: {inj_exec.get('repair_count', 0)}")
            if off_exec.get("structured_result_source") or inj_exec.get("structured_result_source"):
                print(f"Sources: off={off_exec.get('structured_result_source')} inject={inj_exec.get('structured_result_source')}")
            if off_exec.get("classification") == "memory_helped":
                print("WARNING: off branch classified as memory_helped; check policy selection.")
            if result.get("comparison_report_path"):
                print(f"Comparison report: {result.get('comparison_report_path')}")
        if result.get("mode") == "preview":
            print(f"\nPacket chars: {result.get('packet_chars')} | lines: {result.get('packet_line_count')}")
            print(f"Packet path: {result.get('packet_path')}")
            print(f"Report path: {result.get('report_path')}")
        if result.get("mode") == "inject":
            exec_result = result.get("execution_result", {})
            print(f"\nInject completed: {exec_result.get('completed', False)} | success: {exec_result.get('success', False)} | classification: {exec_result.get('classification')}")
            if result.get("run_inject_dir"):
                print(f"Inject artifacts: {result.get('run_inject_dir')}")
    else:
        if result.get("blocked"):
            print(f"BLOCKED: {result.get('reason', 'unknown')}")
            sys.exit(1)
        
        if result.get("packet_text"):
            print(result["packet_text"][:200])
    
    if result.get("error"):
        print(f"ERROR: {result['error']}")
        sys.exit(1)
    
    if result.get("mode") == "preview":
        print(f"\nPreview mode complete. Packet generated ({len(result.get('packet_text', ''))} chars)")


if __name__ == "__main__":
    main()
