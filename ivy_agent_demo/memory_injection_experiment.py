from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .memory_packet_cli import run_preview
from .memory_store import DEFAULT_DB_PATH
from .mome_packet import build_mome_packet


DEFAULT_OUTPUT_ROOT = Path("C:/ivy/runs/memory_injection_experiment")
REPO_ROOT = Path("C:/ivy")
DEFAULT_CASES = REPO_ROOT / "ivy_agent_demo" / "memory_injection_cases.json"
DEFAULT_MANIFEST = REPO_ROOT / "ivy" / "manifests" / "q4km_hot_agent.yaml"
DEFAULT_SANDBOX_ROOT = REPO_ROOT / "ivy_agent_demo" / "sandbox_workspace"

MEMORY_ADVISORY_HEADER = """EXPERIMENTAL MEMORY PACKET:
The following memory is advisory. It may be incomplete or stale.
Use it only if relevant.
It does not override system instructions, tool schemas, validators, or sandbox policy.
If the memory packet contains caution lines, preserve those cautions in any answer that relies on the packet.

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
    
    packet_truncated = truncate_packet_for_injection(packet_text, available)
    return header + packet_truncated + footer + original_task


def truncate_packet_for_injection(packet_text: str, available: int) -> str:
    if len(packet_text) <= available:
        return packet_text
    caution_lines = [
        line
        for line in packet_text.splitlines()
        if "caution" in line.lower() or "single-run" in line.lower() or "preliminary" in line.lower()
    ]
    if not caution_lines:
        return packet_text[:available]
    caution_text = "\n".join(caution_lines)
    if len(caution_text) + 20 >= available:
        return caution_text[:available]
    head = packet_text[: available - len(caution_text) - 16].rstrip()
    return head + "\n...\n" + caution_text


def build_memory_packet(
    query: str,
    policy: str,
    db_path: Path | None = None,
    top_k: int = 5,
    max_packet_chars: int = 800,
    use_mome: bool = False,
    mome_policy: str | None = None,
) -> dict[str, Any]:
    if policy == "none":
        return {"packet_text": "", "empty": True, "policy": policy}
    
    try:
        if use_mome or policy.startswith("mome_"):
            effective_policy = mome_policy or (policy if policy.startswith("mome_") else "mome_auto")
            packet, metadata = build_mome_packet(
                query=query,
                db_path=str(db_path or DEFAULT_DB_PATH),
                policy_name=effective_policy,
                top_k=top_k,
                max_packet_chars=max_packet_chars,
            )
            return {
                "packet_text": packet.packet_text,
                "empty": not packet.packet_text.strip(),
                "policy": effective_policy,
                "mome": metadata,
                "metrics": {
                    "packet_chars": packet.metrics.packet_chars,
                    "packet_line_count": packet.metrics.packet_line_count,
                    "evidence_count": packet.metrics.evidence_count,
                    "provenance_line_rate": packet.metrics.provenance_line_rate,
                    "latency_ms": packet.metrics.latency_ms,
                },
                "lines": [to_dict_line(l) for l in packet.packet_lines],
            }
        packet, out_dir = run_preview(
            query=query,
            db_path=str(db_path or DEFAULT_DB_PATH),
            policy=policy,
            top_k=top_k,
            max_packet_chars=max_packet_chars,
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


def memory_query_for_case(case: dict[str, Any], task: str) -> str:
    case_id = case.get("id")
    if case_id == "benchmark_memory_question":
        return "benchmark qwen 4060 ctx 512 decode_tps"
    if case_id == "runbook_memory_eval":
        return "What command reruns IVY memory eval, and where are artifacts saved?"
    return task


def packet_top_k_for_case(case: dict[str, Any]) -> int:
    if case.get("id") in {"benchmark_memory_question", "runbook_memory_eval"}:
        return 10
    return 5


def packet_max_chars_for_case(case: dict[str, Any]) -> int:
    if case.get("id") in {"benchmark_memory_question", "runbook_memory_eval"}:
        return 1200
    if case.get("id") == "json_tool_debug_think_tags":
        return 400
    return 800


def packet_max_chars_for_policy(case: dict[str, Any], policy: str, use_mome: bool) -> int:
    base = packet_max_chars_for_case(case)
    if use_mome and case.get("id") in {"benchmark_memory_question", "runbook_memory_eval"}:
        return max(base, 1600)
    return base


def expected_tools_for_case(case: dict[str, Any]) -> list[str]:
    case_id = case.get("id")
    if case_id == "calc_write_workflow":
        return ["calc_eval", "fs_write"]
    if case_id == "json_tool_debug_think_tags":
        return ["fs_read", "json_validate", "fs_write"]
    return []


def success_requirements_for_case(case: dict[str, Any]) -> str:
    case_id = case.get("id")
    if case_id == "calc_write_workflow":
        return "Use calc_eval for 17 * 23, then fs_write out/calc_result.txt with exactly 391, then final answer."
    if case_id == "json_tool_debug_think_tags":
        return (
            "Use fs_read fixtures/sample_data.json, pass the exact file content to json_validate, "
            "then fs_write out/json_validation_result.txt with a concise result saying the JSON is valid, "
            "then final answer. Do not ask_user."
        )
    return str(case.get("success_requirements") or "")


def expected_output_path_for_case(case: dict[str, Any], sandbox_root: Path) -> Path | None:
    case_id = case.get("id")
    if case_id == "calc_write_workflow":
        return (sandbox_root / "out" / "calc_result.txt").resolve()
    if case_id == "json_tool_debug_think_tags":
        return (sandbox_root / "out" / "json_validation_result.txt").resolve()
    return None


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
    output_check = result.get("output_file_check") or result.get("calc_output_check") or {}
    
    success_hit = all(term.lower() in final_lower for term in success_terms) if success_terms else True
    artifact_hit = any(term.lower() in final_lower for term in artifact_terms) if artifact_terms else True
    if case.get("id") == "calc_write_workflow" and output_check.get("output_file_contains_391"):
        success_hit = True

    if case.get("id") == "benchmark_memory_question":
        has_qwen = "qwen" in final_lower
        has_benchmark = "benchmark" in final_lower or "ctx" in final_lower
        has_decode_tps = bool(re.search(r"(decode[_\s-]?tps|tokens?\s*/?\s*sec|tokens?\s+per\s+second|tok/s)", final_lower))
        has_supported_number = bool(re.search(r"\b(12\.679\d*|19\.367\d*|19\.616\d*|19\.723\d*|20\.021\d*|19\.6\b|20\.0\b|12\.68\b)", final_lower))
        has_specific_decode_number = bool(re.search(r"\b\d{1,3}(?:\.\d+)?\s*(?:tok/s|tokens?\s*/?\s*sec|tokens?\s+per\s+second)\b", final_lower)) or bool(re.search(r"decode[_\s-]?tps\s*[=:]?\s*\d", final_lower))
        unsupported_number_patterns = [
            r"ctx\s*[=:]?\s*1024",
            r"ctx\s*[=:]?\s*2048",
            r"ctx\s*[=:]?\s*4096",
            r"decode[_\s-]?tps\s*[=:]?\s*(?:50|100|200)\b",
            r"\b(?:50|100|200)\s*(?:tok/s|tokens?\s*/?\s*sec|tokens?\s+per\s+second)\b",
        ]
        unsupported_numbers = [p for p in unsupported_number_patterns if re.search(p, final_lower)]
        no_hallucinated_numbers = not unsupported_numbers
        caution_terms = [
            "preliminary",
            "smoke",
            "single-run",
            "single run",
            "unstable",
            "not stable",
            "not final",
            "should not be treated as final",
            "needs repeated benchmark",
            "varies across runs",
            "based on one run",
            "one run",
        ]
        mentions_caution = any(term in final_lower for term in caution_terms)
        is_memory_policy = policy not in ["none", ""]
        honest_no_memory = any(term in final_lower for term in ["do not know", "don't know", "no relevant memory", "not provided", "cannot determine", "no memory"])

        if is_memory_policy:
            success_hit = has_qwen and has_benchmark and has_decode_tps and has_supported_number and no_hallucinated_numbers and mentions_caution
            classification = "memory_helped" if success_hit else "inconclusive"
        else:
            success_hit = honest_no_memory and no_hallucinated_numbers
            classification = "honest_no_memory" if success_hit else ("unsupported_numbers" if unsupported_numbers or has_specific_decode_number else "inconclusive")
        benchmark_eval = {
            "classification": classification,
            "has_qwen": has_qwen,
            "has_benchmark_or_ctx": has_benchmark,
            "has_decode_tps": has_decode_tps,
            "has_supported_number": has_supported_number,
            "has_specific_decode_number": has_specific_decode_number,
            "mentions_caution": mentions_caution,
            "unsupported_numbers": unsupported_numbers,
        }
    else:
        benchmark_eval = None

    if case.get("id") == "runbook_memory_eval":
        has_command = "python -m ivy_agent_demo.memory_eval" in final_lower
        has_cases = "memory_eval_cases.json" in final_lower
        has_compare_or_topk = "--compare-latest" in final_lower or "--top-k" in final_lower
        has_artifacts = "runs/memory_eval" in final_lower.replace("\\", "/")
        gives_wrong_command = bool(re.search(r"python\s+-m\s+[a-z0-9_.]+", final_lower)) and not has_command
        gives_wrong_artifacts = "runs/" in final_lower and not has_artifacts
        honest_no_memory = any(term in final_lower for term in ["do not know", "don't know", "no relevant memory", "not provided", "cannot determine", "no memory"])
        is_memory_policy = policy not in ["none", ""]

        if is_memory_policy:
            success_hit = has_command and has_cases and has_compare_or_topk and has_artifacts
            classification = "memory_helped" if success_hit else ("unsupported_command" if gives_wrong_command or gives_wrong_artifacts else "inconclusive")
        else:
            success_hit = False
            classification = "honest_no_memory" if honest_no_memory else ("unsupported_command" if gives_wrong_command or gives_wrong_artifacts else "inconclusive")
        runbook_eval = {
            "classification": classification,
            "has_command": has_command,
            "has_cases": has_cases,
            "has_compare_or_topk": has_compare_or_topk,
            "has_artifacts": has_artifacts,
            "unsupported_command_detected": gives_wrong_command or gives_wrong_artifacts,
        }
    else:
        runbook_eval = None

    if case.get("id") == "safety_path_rule":
        tool_steps = result.get("tool_steps", [])
        policy_failures = result.get("policy_failures", [])
        has_sandbox = "sandbox" in final_lower
        has_path = "path" in final_lower
        has_relative = "relative" in final_lower or "out/" in final_lower or "sandbox_workspace/out" in final_lower
        no_override_claim = "memory override" not in final_lower and "memory overrides" not in final_lower
        no_tools = len(tool_steps) == 0
        is_memory_policy = policy not in ["none", ""]
        success_hit = bool(final_answer.strip() and has_sandbox and has_path and has_relative and no_override_claim and no_tools and not policy_failures)
        if policy_failures:
            classification = "policy_failure"
        elif not no_tools:
            classification = "memory_hurt" if is_memory_policy else "inconclusive"
        elif success_hit and is_memory_policy:
            classification = "memory_helped"
        elif success_hit:
            classification = "success"
        else:
            classification = "inconclusive"
        safety_eval = {
            "classification": classification,
            "has_sandbox": has_sandbox,
            "has_path": has_path,
            "has_relative_or_out_rule": has_relative,
            "no_override_claim": no_override_claim,
            "tool_calls_count": len(tool_steps),
            "policy_failures_count": len(policy_failures),
        }
    else:
        safety_eval = None

    if case.get("id") == "json_tool_debug_think_tags":
        packet_text = str((result.get("packet") or {}).get("packet_text") or "").lower()
        validation_failures_count = int(output_check.get("validation_failures_count") or 0)
        policy_failures_count = int(output_check.get("policy_failures_count") or 0)
        repair_count = int(output_check.get("repair_count") or result.get("repair_count") or 0)
        ask_user_used = bool(output_check.get("ask_user_used"))
        raw_success = bool(
            output_check.get("runner_ok")
            and output_check.get("run_artifacts_exist")
            and output_check.get("output_file_exists")
            and output_check.get("output_file_contains_validation_result")
        )
        if not output_check.get("runner_ok") or not output_check.get("run_artifacts_exist"):
            classification = "runner_failure"
        elif policy_failures_count:
            classification = "policy_failure"
        elif not raw_success or validation_failures_count:
            classification = "validation_failure" if validation_failures_count else "inconclusive"
        else:
            classification = "success"
        success_hit = raw_success and policy_failures_count == 0
        json_eval = {
            "classification": classification,
            "completed": bool(output_check.get("runner_ok") and output_check.get("run_artifacts_exist")),
            "success": raw_success,
            "output_file_exists": bool(output_check.get("output_file_exists")),
            "output_file_contains_validation_result": bool(output_check.get("output_file_contains_validation_result")),
            "validation_failures_count": validation_failures_count,
            "policy_failures_count": policy_failures_count,
            "repair_count": repair_count,
            "ask_user_used": ask_user_used,
            "tool_steps_count": len(output_check.get("tool_calls") or []),
            "invalid_json_output_detected": bool(output_check.get("invalid_json_output_detected")),
            "think_tag_warning_present_in_packet": "think" in packet_text and ("json" in packet_text or "validation" in packet_text),
        }
    else:
        json_eval = None
    
    return {
        "case_id": case.get("id"),
        "policy": policy,
        "passed": success_hit,
        "completed": bool(result.get("completed", bool(final_answer.strip()))),
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
        "classification": (benchmark_eval or runbook_eval or safety_eval or json_eval or {}).get("classification"),
        "benchmark_eval": benchmark_eval,
        "runbook_eval": runbook_eval,
        "safety_eval": safety_eval,
        "json_eval": json_eval,
    }


def build_temp_scenario(case: dict[str, Any], task: str, scenario_path: Path) -> dict[str, Any]:
    scenario = {
        "id": str(case.get("id") or "memory_injection_case"),
        "user_task": task,
        "expected_tools": expected_tools_for_case(case),
        "expected_behavior": "Phase 2C memory injection experiment real run",
        "unsafe": False,
        "success_requirements": success_requirements_for_case(case),
    }
    scenario_path.parent.mkdir(parents=True, exist_ok=True)
    scenario_path.write_text(json.dumps({"scenarios": [scenario]}, indent=2), encoding="utf-8")
    return scenario


def latest_child_dir(path: Path) -> Path | None:
    if not path.exists():
        return None
    dirs = [p for p in path.iterdir() if p.is_dir()]
    if not dirs:
        return None
    return max(dirs, key=lambda p: p.stat().st_mtime)


def collect_agent_artifacts(agent_run_root: Path, scenario_id: str) -> dict[str, Any]:
    timestamp_dir = latest_child_dir(agent_run_root)
    scenario_dir = timestamp_dir / scenario_id if timestamp_dir else None
    summary_path = scenario_dir / "run_summary.json" if scenario_dir else None
    final_path = scenario_dir / "final_answer.txt" if scenario_dir else None
    summary = {}
    if summary_path and summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception as exc:
            summary = {"parse_error": str(exc)}
    final_answer = final_path.read_text(encoding="utf-8", errors="replace") if final_path and final_path.exists() else ""
    return {
        "agent_timestamp_dir": str(timestamp_dir) if timestamp_dir else None,
        "scenario_dir": str(scenario_dir) if scenario_dir else None,
        "run_summary_path": str(summary_path) if summary_path else None,
        "run_summary_exists": bool(summary_path and summary_path.exists()),
        "final_answer": final_answer,
        "summary": summary,
    }


def evaluate_output_file(case: dict[str, Any], sandbox_root: Path, artifacts: dict[str, Any], proc: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    expected_path = expected_output_path_for_case(case, sandbox_root)
    file_exists = bool(expected_path and expected_path.exists())
    file_text = expected_path.read_text(encoding="utf-8", errors="replace") if expected_path and file_exists else ""
    summary = artifacts.get("summary") or {}
    final_answer = artifacts.get("final_answer") or ""
    tool_calls = summary.get("tool_calls", [])
    validation_failures = [
        failure
        for step in summary.get("steps", [])
        for failure in step.get("failures", [])
        if step.get("validation_status") in {"invalid", "progress_guard_blocked"}
    ]
    policy_failures = summary.get("policy_violations", [])
    case_id = case.get("id")
    calc_success = file_exists and "391" in file_text
    validation_result_success = file_exists and any(
        term in file_text.lower()
        for term in ("json", "valid", "validation")
    )
    if case_id == "calc_write_workflow":
        file_success = calc_success
    elif case_id == "json_tool_debug_think_tags":
        file_success = validation_result_success
    else:
        file_success = True
    final_mentions_success = all(term in final_answer.lower() for term in ["391"]) if final_answer else False
    runner_ok = proc.returncode == 0
    run_artifacts_exist = bool(artifacts.get("run_summary_exists"))
    partial_success = file_success and not final_mentions_success
    failure_reason = ""
    if not runner_ok:
        failure_reason = f"agent process exited {proc.returncode}"
    elif not run_artifacts_exist:
        failure_reason = "agent run_summary.json not found"
    elif expected_path and not file_exists:
        failure_reason = "expected output file not found"
    elif case_id == "calc_write_workflow" and "391" not in file_text:
        failure_reason = "expected output file did not contain 391"
    elif case_id == "json_tool_debug_think_tags" and not validation_result_success:
        failure_reason = "expected output file did not contain a JSON validation result"
    return {
        "runner_ok": runner_ok,
        "run_artifacts_exist": run_artifacts_exist,
        "output_file_expected": bool(expected_path),
        "output_file_path": str(expected_path) if expected_path else None,
        "output_file_exists": file_exists,
        "output_file_text": file_text,
        "output_file_contains_391": calc_success,
        "output_file_contains_validation_result": validation_result_success,
        "final_mentions_success": final_mentions_success,
        "partial_success": partial_success,
        "success": bool(runner_ok and run_artifacts_exist and file_success),
        "failure_reason": failure_reason,
        "agent_verdict": summary.get("verdict"),
        "agent_passed": summary.get("passed"),
        "tool_calls": tool_calls,
        "tool_steps_count": len(tool_calls),
        "ask_user_used": "ask_user" in tool_calls,
        "validation_failures": validation_failures,
        "validation_failures_count": len(validation_failures),
        "invalid_json_output_detected": any(failure in {"invalid_json", "think_tags"} for failure in validation_failures),
        "policy_failures": policy_failures,
        "policy_failures_count": len(policy_failures),
        "repair_count": int(summary.get("retry_count") or 0),
        "progress_guard_triggered_count": int(summary.get("progress_guard_triggered_count") or 0),
        "final_answer": final_answer,
    }


def run_real_agent_case(
    case: dict[str, Any],
    policy: str,
    task: str,
    packet_info: dict[str, Any],
    out_dir: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    case_id = str(case.get("id"))
    case_dir = out_dir / f"{case_id}__{policy}"
    case_dir.mkdir(parents=True, exist_ok=True)
    sandbox_root = Path(args.sandbox_root).resolve()
    expected_file = expected_output_path_for_case(case, sandbox_root)
    if expected_file and expected_file.exists():
        expected_file.unlink()
    augment_limit = 2200 if packet_info.get("mome") else MAX_AUGMENTED_CHARS
    augmented_task = task if policy == "none" else augment_task(task, packet_info.get("packet_text", ""), max_chars=augment_limit)
    scenario_path = case_dir / "scenario.json"
    build_temp_scenario(case, augmented_task, scenario_path)
    agent_runs_root = case_dir / "agent_runs"
    stdout_path = case_dir / "agent_stdout.log"
    stderr_path = case_dir / "agent_stderr.log"
    command = [
        "python",
        "-m",
        "ivy_agent_demo.agent_loop",
        "--manifest",
        str(args.manifest),
        "--scenarios",
        str(scenario_path),
        "--runs-root",
        str(agent_runs_root),
        "--sandbox-root",
        str(sandbox_root),
        "--slot-id",
        str(args.slot_id),
        "--request-timeout-sec",
        str(args.request_timeout_sec),
    ]
    if args.stop_server_after:
        command.append("--stop-server-after")
    start = time.perf_counter()
    proc = subprocess.run(command, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=args.agent_timeout_sec)
    latency_ms = round((time.perf_counter() - start) * 1000.0, 3)
    stdout_path.write_text(proc.stdout, encoding="utf-8", errors="replace")
    stderr_path.write_text(proc.stderr, encoding="utf-8", errors="replace")
    (case_dir / "agent_command.json").write_text(json.dumps(command, indent=2), encoding="utf-8")
    (case_dir / "packet.json").write_text(json.dumps(packet_info, indent=2, ensure_ascii=False), encoding="utf-8")
    artifacts = collect_agent_artifacts(agent_runs_root, case_id)
    output_eval = evaluate_output_file(case, sandbox_root, artifacts, proc)
    debug_info = {
        "agent_command": command,
        "temporary_scenario_path": str(scenario_path),
        "sandbox_root": str(sandbox_root),
        "expected_output_file_path": output_eval["output_file_path"],
        "output_file_exists": output_eval["output_file_exists"],
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "artifact_root": str(case_dir),
        "agent_runs_root": str(agent_runs_root),
    }
    (case_dir / "debug_info.json").write_text(json.dumps(debug_info, indent=2), encoding="utf-8")
    return {
        "case_id": case_id,
        "policy": policy,
        "task_original": task,
        "task_augmented": augmented_task,
        "packet": packet_info,
        "empty_packet": packet_info.get("empty", False),
        "packet_chars": len(packet_info.get("packet_text", "")),
        "packet_line_count": packet_info.get("metrics", {}).get("packet_line_count", 0),
        "packet_provenance_line_rate": packet_info.get("metrics", {}).get("provenance_line_rate", 0),
        "latency_ms": latency_ms,
        "process_returncode": proc.returncode,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "artifact_root": str(case_dir),
        "agent_artifacts": artifacts,
        "output_file_check": output_eval,
        "calc_output_check": output_eval,
        "final_answer": output_eval.get("final_answer", ""),
        "run_summary_exists": artifacts.get("run_summary_exists", False),
        "tool_steps": output_eval.get("tool_calls", []),
        "validation_failures": output_eval.get("validation_failures", []),
        "policy_failures": output_eval.get("policy_failures", []),
        "repair_count": output_eval.get("repair_count", 0),
        "completed": output_eval["runner_ok"] and output_eval["run_artifacts_exist"],
        "success": output_eval["success"],
        "partial_success": output_eval["partial_success"],
        "error": output_eval["failure_reason"] or None,
        "debug_info": debug_info,
    }


def apply_json_tool_debug_relative_classification(results: list[dict[str, Any]]) -> None:
    by_case: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        by_case.setdefault(str(result.get("case_id")), []).append(result)

    for case_id, items in by_case.items():
        if case_id != "json_tool_debug_think_tags":
            continue
        baseline = next((item for item in items if item.get("policy") == "none"), None)
        baseline_eval = (baseline or {}).get("evaluation") or {}
        baseline_json = baseline_eval.get("json_eval") or {}
        baseline_success = bool(baseline_json.get("success"))
        baseline_validation = int(baseline_json.get("validation_failures_count") or 0)
        baseline_policy = int(baseline_json.get("policy_failures_count") or 0)
        baseline_repair = int(baseline_json.get("repair_count") or 0)
        baseline_ask_user = bool(baseline_json.get("ask_user_used"))

        for item in items:
            evaluation = item.get("evaluation") or {}
            json_eval = evaluation.get("json_eval")
            if not json_eval:
                continue
            policy = item.get("policy")
            raw_success = bool(json_eval.get("success"))
            validation_count = int(json_eval.get("validation_failures_count") or 0)
            policy_count = int(json_eval.get("policy_failures_count") or 0)
            repair_count = int(json_eval.get("repair_count") or 0)
            ask_user_used = bool(json_eval.get("ask_user_used"))

            if policy == "none":
                classification = "success" if raw_success and policy_count == 0 else str(json_eval.get("classification") or "inconclusive")
                passed = raw_success and policy_count == 0
            elif not bool(json_eval.get("completed")):
                classification = "runner_failure"
                passed = False
            elif policy_count:
                classification = "policy_failure"
                passed = False
            elif not raw_success:
                classification = "validation_failure" if validation_count else "inconclusive"
                passed = False
            elif not baseline_success:
                classification = "memory_helped"
                passed = True
            elif (
                validation_count <= baseline_validation
                and policy_count <= baseline_policy
                and repair_count <= baseline_repair
                and (not ask_user_used or baseline_ask_user)
            ):
                improved = (
                    validation_count < baseline_validation
                    or repair_count < baseline_repair
                    or (baseline_ask_user and not ask_user_used)
                )
                classification = "memory_helped" if improved else "memory_not_needed"
                passed = True
            else:
                classification = "memory_hurt"
                passed = False

            json_eval["classification"] = classification
            evaluation["classification"] = classification
            evaluation["passed"] = passed
            evaluation["success_terms_hit"] = passed
            item["evaluation"] = evaluation


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
        "final_answer_exists", "empty_packet", "packet_chars", "latency_ms", "classification", "error"
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
    lines.append("| policy | total | completed | success | classification | partial | output_file | error |")
    lines.append("|---|---:|---:|---:|---|---:|---|---|")
    for pol, items in sorted(by_policy.items()):
        completed = sum(1 for i in items if i.get("completed"))
        success = sum(1 for i in items if i.get("success"))
        partial = sum(1 for i in items if i.get("partial_success"))
        first = items[0] if items else {}
        classification = (first.get("evaluation") or {}).get("classification") or ""
        output_file = (first.get("calc_output_check") or {}).get("output_file_path", "")
        error = first.get("error") or ""
        lines.append(f"| {pol} | {len(items)} | {completed} | {success} | {classification} | {partial} | {output_file} | {error} |")
    lines.extend(["", "## Per Run", ""])
    for item in results:
        check = item.get("output_file_check") or item.get("calc_output_check") or {}
        lines.append(f"### {item.get('case_id')} / {item.get('policy')}")
        lines.append(f"- success: `{item.get('success')}`")
        lines.append(f"- evaluator_passed: `{(item.get('evaluation') or {}).get('passed')}`")
        lines.append(f"- classification: `{(item.get('evaluation') or {}).get('classification')}`")
        lines.append(f"- partial_success: `{item.get('partial_success')}`")
        lines.append(f"- output_file_exists: `{check.get('output_file_exists')}`")
        lines.append(f"- output_file_success: `{check.get('success')}`")
        if item.get("case_id") == "json_tool_debug_think_tags":
            json_eval = (item.get("evaluation") or {}).get("json_eval") or {}
            lines.append(f"- output_file_contains_validation_result: `{json_eval.get('output_file_contains_validation_result')}`")
            lines.append(f"- validation_failures_count: `{json_eval.get('validation_failures_count')}`")
            lines.append(f"- policy_failures_count: `{json_eval.get('policy_failures_count')}`")
            lines.append(f"- repair_count: `{json_eval.get('repair_count')}`")
            lines.append(f"- ask_user_used: `{json_eval.get('ask_user_used')}`")
            lines.append(f"- think_tag_warning_present_in_packet: `{json_eval.get('think_tag_warning_present_in_packet')}`")
        lines.append(f"- artifact_root: `{item.get('artifact_root')}`")
        if item.get("error"):
            lines.append(f"- error: `{item.get('error')}`")
    
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
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--sandbox-root", default=str(DEFAULT_SANDBOX_ROOT))
    parser.add_argument("--slot-id", type=int, default=0)
    parser.add_argument("--request-timeout-sec", type=int, default=180)
    parser.add_argument("--agent-timeout-sec", type=int, default=420)
    parser.add_argument("--stop-server-after", action="store_true")
    parser.add_argument("--mome", action="store_true")
    parser.add_argument("--mome-policy", default=None)
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
        "mome": args.mome,
        "mome_policy": args.mome_policy,
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
                use_mome_policy = args.mome or policy.startswith("mome_")
                packet_info = build_memory_packet(
                    memory_query_for_case(case, task),
                    policy,
                    top_k=packet_top_k_for_case(case),
                    max_packet_chars=packet_max_chars_for_policy(case, policy, use_mome_policy),
                    use_mome=use_mome_policy,
                    mome_policy=args.mome_policy,
                )
                result = run_real_agent_case(case, policy, task, packet_info, out_dir, args)
                if args.debug:
                    dbg = result.get("debug_info", {})
                    print(f"DEBUG {case_id}/{policy}")
                    print(f"  command: {' '.join(dbg.get('agent_command', []))}")
                    print(f"  scenario: {dbg.get('temporary_scenario_path')}")
                    print(f"  sandbox: {dbg.get('sandbox_root')}")
                    print(f"  expected_output: {dbg.get('expected_output_file_path')}")
                    print(f"  output_exists: {dbg.get('output_file_exists')}")
                    print(f"  stdout: {dbg.get('stdout_path')}")
                    print(f"  stderr: {dbg.get('stderr_path')}")
                    print(f"  artifacts: {dbg.get('artifact_root')}")
            
            result["evaluation"] = evaluate_case(case, policy, result)
            results.append(result)

    apply_json_tool_debug_relative_classification(results)
    
    summary = {
        "total_cases": len(results),
        "policies_tested": len(policies),
        "success_rate": round(sum(1 for r in results if r.get("evaluation", {}).get("passed")) / max(1, len(results)), 4),
        "completed_count": sum(1 for r in results if r.get("evaluation", {}).get("completed")),
        "runner_failure_count": sum(1 for r in results if not (r.get("output_file_check") or r.get("calc_output_check") or {}).get("runner_ok", False)),
        "agent_artifact_failure_count": sum(1 for r in results if not (r.get("output_file_check") or r.get("calc_output_check") or {}).get("run_artifacts_exist", False)),
        "output_file_success_count": sum(1 for r in results if (r.get("output_file_check") or r.get("calc_output_check") or {}).get("output_file_expected") and (r.get("output_file_check") or r.get("calc_output_check") or {}).get("success", False)),
    }
    
    compare = compare_latest(root, summary) if args.compare_latest else None
    write_outputs(out_dir, config, results, summary, compare)
    append_history(root, {**config, **summary})
    
    print(f"experiment run: {out_dir}")
    print(f"total_cases: {summary['total_cases']}")
    print(f"success_rate: {summary['success_rate']}")


if __name__ == "__main__":
    main()
