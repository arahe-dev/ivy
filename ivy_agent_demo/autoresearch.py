from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from . import autoresearch_metrics


REPO_ROOT = Path("C:/ivy")
DEFAULT_CONFIG = REPO_ROOT / "ivy_agent_demo" / "autoresearch_config.json"
DEFAULT_CANDIDATES_DIR = REPO_ROOT / "ivy_agent_demo" / "autoresearch_candidates"

AGENT_LOOP_PATH = REPO_ROOT / "ivy_agent_demo" / "agent_loop.py"


@dataclass
class GuardrailReport:
    ok: bool
    warnings: list[str]
    errors: list[str]
    forbidden_diffs: list[str]
    prompt_injection_hits: list[str]
    git_status: dict[str, Any] | None = None


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def list_candidates(candidate_dir: Path) -> list[Path]:
    if not candidate_dir.exists():
        return []
    return sorted(candidate_dir.glob("*.json"))


def load_candidate(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    payload.setdefault("id", path.stem)
    return payload


def resolve_allowed(config: dict[str, Any]) -> list[str]:
    return list(config.get("allowed_files") or [])


def resolve_forbidden(config: dict[str, Any]) -> list[str]:
    return list(config.get("forbidden_files") or [])


def read_file_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def normalize_rel_path(path_text: str) -> str:
    path = Path(path_text)
    try:
        rel = path.relative_to(REPO_ROOT)
        return rel.as_posix()
    except ValueError:
        return path.as_posix().lstrip("./")


def match_glob(path_text: str, patterns: list[str]) -> bool:
    import fnmatch

    norm = path_text.replace("\\", "/")
    return any(fnmatch.fnmatch(norm, pattern.replace("\\", "/")) for pattern in patterns)


def git_available() -> bool:
    return shutil.which("git") is not None


def run_command(cmd: str, cwd: Path, timeout: int | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), shell=True, capture_output=True, text=True, timeout=timeout)


def get_git_status(cwd: Path) -> dict[str, Any]:
    if not git_available():
        return {"available": False, "error": "git not available"}
    result = run_command("git status --porcelain", cwd)
    if result.returncode != 0:
        return {"available": False, "error": result.stderr.strip()}
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return {"available": True, "dirty": bool(lines), "lines": lines}


def git_diff_for_paths(cwd: Path, paths: list[str]) -> list[str]:
    if not git_available():
        return []
    diffs: list[str] = []
    for path in paths:
        result = run_command(f"git diff -- {path}", cwd)
        if result.returncode == 0 and result.stdout.strip():
            diffs.append(path)
    return diffs


def git_changed_files(cwd: Path) -> list[str]:
    if not git_available():
        return []
    result = run_command("git status --porcelain", cwd)
    if result.returncode != 0:
        return []
    files: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path_part = line[3:].strip()
        if " -> " in path_part:
            path_part = path_part.split(" -> ")[-1].strip()
        files.append(path_part)
    return files


def save_git_diff(cwd: Path, out_path: Path, paths: list[str] | None = None) -> None:
    if not git_available():
        return
    if paths:
        cmd = "git diff -- " + " ".join(paths)
    else:
        cmd = "git diff"
    result = run_command(cmd, cwd)
    out_path.write_text(result.stdout or "", encoding="utf-8")


def check_prompt_injection() -> list[str]:
    hits: list[str] = []
    text = read_file_text(AGENT_LOOP_PATH)
    if not text:
        return hits
    lower = text.lower()
    if "memory_packet" in lower:
        hits.append("agent_loop_memory_packet")
    lines = text.splitlines()
    prompt_anchors = [
        idx
        for idx, line in enumerate(lines)
        if "_full_prompt" in line or "PHASE1_STABLE_PREFIX" in line
    ]
    for idx, line in enumerate(lines):
        if "inject" in line.lower():
            if not prompt_anchors or any(abs(idx - anchor) <= 20 for anchor in prompt_anchors):
                hits.append("agent_loop_inject_near_prompt")
                break
    dynamic_idx = None
    for idx, line in enumerate(lines):
        if line.strip().startswith("def _build_dynamic_task"):
            dynamic_idx = idx
            break
    if dynamic_idx is not None:
        for line in lines[dynamic_idx + 1 :]:
            if line.strip().startswith("def "):
                break
            if "memory" in line.lower():
                hits.append("agent_loop_dynamic_suffix_memory")
                break
    return hits


def validate_config(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "experiment_name",
        "allowed_files",
        "forbidden_files",
        "max_iterations",
        "max_minutes",
        "baseline_commands",
        "eval_commands",
        "success_criteria",
        "failure_criteria",
        "metrics_to_track",
        "rollback_policy",
        "report_paths",
    ]
    for key in required:
        if key not in config:
            errors.append(f"missing config field: {key}")
    if not isinstance(config.get("allowed_files"), list):
        errors.append("allowed_files must be a list")
    if not isinstance(config.get("forbidden_files"), list):
        errors.append("forbidden_files must be a list")
    if not isinstance(config.get("baseline_commands"), list):
        errors.append("baseline_commands must be a list")
    if not isinstance(config.get("eval_commands"), list):
        errors.append("eval_commands must be a list")
    return errors


def collect_metrics() -> dict[str, Any]:
    snapshot = autoresearch_metrics.collect_latest()
    return snapshot.metrics


def compare_metrics(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    return autoresearch_metrics.metric_delta(before, after)


def candidate_target_files_allowed(candidate: dict[str, Any], allowed: list[str], forbidden: list[str]) -> tuple[bool, list[str]]:
    violations: list[str] = []
    targets = candidate.get("target_files") or []
    for path in targets:
        norm = normalize_rel_path(path)
        if match_glob(norm, forbidden):
            violations.append(f"target in forbidden list: {norm}")
            continue
        if not match_glob(norm, allowed):
            violations.append(f"target outside allowed list: {norm}")
    return (not violations), violations


def check_metric_thresholds(metrics: dict[str, Any], thresholds: dict[str, Any], baseline: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    for key, rules in thresholds.items():
        value = metrics.get(key)
        if "max" in rules and value is not None and value > rules["max"]:
            failures.append(f"{key}={value} exceeds max {rules['max']}")
        if "min" in rules and value is not None and value < rules["min"]:
            failures.append(f"{key}={value} below min {rules['min']}")
        if "delta_min" in rules:
            current = autoresearch_metrics.safe_float(metrics.get(key))
            base = autoresearch_metrics.safe_float(baseline.get(key))
            if current is not None and base is not None:
                if current - base < rules["delta_min"]:
                    failures.append(f"{key} delta {round(current - base, 4)} below {rules['delta_min']}")
        if "delta_max" in rules:
            current = autoresearch_metrics.safe_float(metrics.get(key))
            base = autoresearch_metrics.safe_float(baseline.get(key))
            if current is not None and base is not None:
                if current - base > rules["delta_max"]:
                    failures.append(f"{key} delta {round(current - base, 4)} above {rules['delta_max']}")
        if "max_relative_to_baseline" in rules:
            base = autoresearch_metrics.safe_float(baseline.get(key))
            val = autoresearch_metrics.safe_float(metrics.get(key))
            if base is not None and val is not None:
                limit = base * (1 + float(rules["max_relative_to_baseline"]))
                if val > limit:
                    failures.append(f"{key}={val} exceeds baseline limit {round(limit, 4)}")
        if "min_relative_to_baseline" in rules:
            base = autoresearch_metrics.safe_float(baseline.get(key))
            val = autoresearch_metrics.safe_float(metrics.get(key))
            if base is not None and val is not None:
                limit = base + float(rules["min_relative_to_baseline"])
                if val < limit:
                    failures.append(f"{key}={val} below baseline floor {round(limit, 4)}")
    return (not failures), failures


def run_eval_commands(commands: list[str], cwd: Path, timeout_minutes: int, stdout_path: Path, stderr_path: Path) -> bool:
    start = time.time()
    with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
        for cmd in commands:
            out.write(f"$ {cmd}\n")
            out.flush()
            elapsed = time.time() - start
            total_budget = timeout_minutes * 60
            remaining = max(1, int(total_budget - elapsed))
            if elapsed > total_budget:
                err.write("Time budget exceeded before running command.\n")
                return False
            try:
                result = subprocess.run(cmd, cwd=str(cwd), shell=True, capture_output=True, text=True, timeout=remaining)
            except subprocess.TimeoutExpired:
                err.write(f"Command timed out after {remaining}s: {cmd}\n")
                return False
            out.write(result.stdout or "")
            err.write(result.stderr or "")
            out.flush()
            err.flush()
            if result.returncode != 0:
                err.write(f"Command failed with code {result.returncode}\n")
                return False
    return True


def guardrails_pre(config: dict[str, Any]) -> GuardrailReport:
    warnings: list[str] = []
    errors: list[str] = []
    forbidden_diffs: list[str] = []

    status = get_git_status(REPO_ROOT)
    if status.get("available"):
        if status.get("dirty"):
            warnings.append("working tree has uncommitted changes")
    else:
        warnings.append("git not available; diff checks limited")

    forbidden = resolve_forbidden(config)
    if status.get("available"):
        forbidden_diffs = git_diff_for_paths(REPO_ROOT, forbidden)
        if forbidden_diffs:
            errors.append(f"forbidden files have diffs: {forbidden_diffs}")

        changed = git_changed_files(REPO_ROOT)
        allowed = resolve_allowed(config)
        report_root = Path(config.get("report_paths", {}).get("output_root", "runs/autoresearch"))
        report_root_norm = normalize_rel_path(str(report_root))
        outside_allowed = []
        for path in changed:
            norm = normalize_rel_path(path)
            if norm.startswith(report_root_norm):
                continue
            if match_glob(norm, forbidden):
                continue
            if match_glob(norm, allowed):
                continue
            outside_allowed.append(norm)
        if outside_allowed:
            warnings.append(f"dirty files outside allowed list: {outside_allowed}")

    cmd_check = shutil.which("python") is not None
    if not cmd_check:
        errors.append("python not available on PATH")

    commands = (config.get("baseline_commands") or []) + (config.get("eval_commands") or [])
    for cmd in commands:
        if not cmd.strip():
            continue
        first = cmd.strip().split()[0]
        if first.lower().startswith("python"):
            if not cmd_check:
                errors.append(f"python required for command: {cmd}")
            continue
        if shutil.which(first) is None:
            warnings.append(f"command not found on PATH: {first}")

    try:
        import ivy_agent_demo.autoresearch_metrics as _metrics
        _ = _metrics.collect_latest()
    except Exception as exc:
        errors.append(f"failed to import metrics: {exc}")

    return GuardrailReport(
        ok=not errors,
        warnings=warnings,
        errors=errors,
        forbidden_diffs=forbidden_diffs,
        prompt_injection_hits=[],
        git_status=status,
    )


def guardrails_post(config: dict[str, Any]) -> GuardrailReport:
    warnings: list[str] = []
    errors: list[str] = []
    forbidden_diffs: list[str] = []
    forbidden = resolve_forbidden(config)

    if git_available():
        forbidden_diffs = git_diff_for_paths(REPO_ROOT, forbidden)
        if forbidden_diffs:
            errors.append(f"forbidden files changed: {forbidden_diffs}")
        changed = git_changed_files(REPO_ROOT)
        allowed = resolve_allowed(config)
        report_root = Path(config.get("report_paths", {}).get("output_root", "runs/autoresearch"))
        report_root_norm = normalize_rel_path(str(report_root))
        outside_allowed = []
        for path in changed:
            norm = normalize_rel_path(path)
            if norm.startswith(report_root_norm):
                continue
            if match_glob(norm, forbidden):
                continue
            if match_glob(norm, allowed):
                continue
            outside_allowed.append(norm)
        if outside_allowed:
            warnings.append(f"dirty files outside allowed list: {outside_allowed}")
    else:
        warnings.append("git not available; forbidden diff check skipped")

    prompt_hits = check_prompt_injection()
    if prompt_hits:
        errors.append(f"prompt injection guard hit: {prompt_hits}")

    status = get_git_status(REPO_ROOT)
    return GuardrailReport(
        ok=not errors,
        warnings=warnings,
        errors=errors,
        forbidden_diffs=forbidden_diffs,
        prompt_injection_hits=prompt_hits,
        git_status=status,
    )


def write_history(root: Path, row: dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    jsonl = root / "history.jsonl"
    with jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    csv_path = root / "history.csv"
    fields = ["run_id", "experiment_name", "candidate_id", "decision", "timestamp"]
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        if write_header:
            f.write(",".join(fields) + "\n")
        f.write(",".join(str(row.get(field, "")) for field in fields) + "\n")


def save_candidate_stub(out_dir: Path, candidate: dict[str, Any]) -> None:
    stub = {
        "candidate_id": candidate.get("id"),
        "target_files": candidate.get("target_files"),
        "todo": "Implement candidate changes manually in allowed files, then rerun autoresearch.",
    }
    (out_dir / "candidate_todo.json").write_text(json.dumps(stub, indent=2), encoding="utf-8")


def build_iteration_report(iter_dir: Path, decision: dict[str, Any]) -> None:
    lines = ["# AutoResearch Iteration", "", f"Decision: `{decision.get('decision')}`", ""]
    notes = decision.get("notes") or []
    if notes:
        lines.append("## Notes")
        lines.extend([f"- {note}" for note in notes])
    (iter_dir / "iteration_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_autoresearch_report(out_dir: Path, results: list[dict[str, Any]]) -> None:
    lines = ["# AutoResearch Report", "", "## Iterations", ""]
    for entry in results:
        lines.append(f"- {entry.get('iteration_id')}: {entry.get('decision')} (candidate={entry.get('candidate_id')})")
    (out_dir / "autoresearch_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_self_test() -> int:
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as td:
        root = Path(td)
        fake_run = root / "runs"
        sweep_dir = fake_run / "memory_packet_sweep" / "fake"
        sweep_dir.mkdir(parents=True, exist_ok=True)
        sweep_payload = {
            "summary": {
                "packet_term_hit_rate": 0.5,
                "empty_packet_count": 1,
                "overclaim_risk_count": 0,
                "overcompression_risk_count": 1,
                "average_latency_ms": 12.3,
                "average_packet_chars": 456.0,
            },
            "results": [{"category": "safety", "packet_term_hit": True}],
            "config": {"run_id": "fake"},
        }
        (sweep_dir / "sweep_results.json").write_text(json.dumps(sweep_payload), encoding="utf-8")
        rank_dir = fake_run / "memory_ranking_eval" / "fake"
        rank_dir.mkdir(parents=True, exist_ok=True)
        rank_payload = {
            "summary": {
                "top_1_source_family_hit_rate": 1.0,
                "top_3_source_family_hit_rate": 1.0,
                "term_hit_rate": 0.7,
                "provenance_rate": 1.0,
                "avg_latency_ms": 2.1,
            },
            "config": {"run_id": "fake"},
        }
        (rank_dir / "ranking_eval_results.json").write_text(json.dumps(rank_payload), encoding="utf-8")

        metrics = autoresearch_metrics.collect_latest(run_root=fake_run)
        if metrics.metrics.get("packet_term_hit_rate") != 0.5:
            print("FAIL metrics parser")
            return 1
        if metrics.metrics.get("safety_hit_rate") != 1.0:
            print("FAIL safety hit rate")
            return 1

        config = load_json(DEFAULT_CONFIG)
        errors = validate_config(config)
        if errors:
            print("FAIL config validation")
            return 1

        baseline = {"packet_term_hit_rate": 0.5}
        current = {"packet_term_hit_rate": 0.52}
        ok, failures = check_metric_thresholds(current, {"packet_term_hit_rate": {"delta_min": 0.01}}, baseline)
        if not ok or failures:
            print("FAIL metric threshold")
            return 1

        guard = guardrails_pre(config)
        if guard.errors:
            print("FAIL guardrails pre")
            return 1

        report_dir = root / "autoresearch"
        report_dir.mkdir(parents=True, exist_ok=True)
        decision = {"decision": "accepted", "notes": ["synthetic"]}
        build_iteration_report(report_dir, decision)
        if not (report_dir / "iteration_report.md").exists():
            print("FAIL report")
            return 1

    print("PASS")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run bounded AutoResearch loops for IVY memory experiments.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-apply", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--max-iterations", type=int)
    parser.add_argument("--max-minutes", type=int)
    parser.add_argument("--research-target")
    args = parser.parse_args()

    if args.self_test:
        raise SystemExit(run_self_test())

    config = load_json(Path(args.config))
    errors = validate_config(config)
    if errors:
        raise SystemExit("\n".join(errors))

    if args.max_iterations is not None:
        config["max_iterations"] = args.max_iterations
    if args.max_minutes is not None:
        config["max_minutes"] = args.max_minutes

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    report_root = REPO_ROOT / config["report_paths"]["output_root"] / run_id
    report_root.mkdir(parents=True, exist_ok=True)

    guard_pre = guardrails_pre(config)
    if not guard_pre.ok:
        write_json(report_root / "guard_pre.json", guard_pre.__dict__)
        raise SystemExit("Guardrails failed before run. See guard_pre.json")
    write_json(report_root / "guard_pre.json", guard_pre.__dict__)

    write_json(report_root / "autoresearch_config_used.json", config)

    if config.get("baseline_commands"):
        baseline_stdout = report_root / "baseline_stdout.log"
        baseline_stderr = report_root / "baseline_stderr.log"
        run_eval_commands(config.get("baseline_commands") or [], REPO_ROOT, int(config.get("max_minutes", 30)), baseline_stdout, baseline_stderr)

    baseline_metrics = collect_metrics()
    write_json(report_root / "baseline_metrics.json", baseline_metrics)

    candidates = [load_candidate(p) for p in list_candidates(DEFAULT_CANDIDATES_DIR)]
    if args.research_target:
        candidates = [c for c in candidates if c.get("id") == args.research_target]
    if not candidates:
        raise SystemExit("No candidates available.")

    if args.dry_run:
        payload = {
            "run_id": run_id,
            "candidates": [c.get("id") for c in candidates],
            "baseline_commands": config.get("baseline_commands"),
            "eval_commands": config.get("eval_commands"),
            "success_criteria": config.get("success_criteria"),
            "failure_criteria": config.get("failure_criteria"),
        }
        write_json(report_root / "dry_run_plan.json", payload)
        print(json.dumps(payload, indent=2))
        return

    results: list[dict[str, Any]] = []
    max_iter = int(config.get("max_iterations", 1))
    max_minutes = int(config.get("max_minutes", 30))
    stop_on_first_success = bool(config.get("stop_on_first_success", True))
    start_time = time.time()

    for idx, candidate in enumerate(candidates[:max_iter], start=1):
        if time.time() - start_time > max_minutes * 60:
            results.append({"iteration_id": f"iteration_{idx:03d}", "decision": "stopped", "candidate_id": candidate.get("id")})
            break
        iteration_id = f"iteration_{idx:03d}"
        iter_dir = report_root / iteration_id
        iter_dir.mkdir(parents=True, exist_ok=True)
        write_json(iter_dir / "candidate_spec.json", candidate)

        target_ok, target_violations = candidate_target_files_allowed(
            candidate,
            resolve_allowed(config),
            resolve_forbidden(config),
        )
        if not target_ok:
            decision_payload = {
                "decision": "rejected",
                "notes": target_violations,
                "candidate_id": candidate.get("id"),
                "eval_ok": False,
                "guardrails_ok": False,
                "metric_deltas": {},
            }
            write_json(iter_dir / "decision.json", decision_payload)
            build_iteration_report(iter_dir, decision_payload)
            results.append({"iteration_id": iteration_id, "decision": "rejected", "candidate_id": candidate.get("id")})
            continue

        pre_metrics = collect_metrics()
        write_json(iter_dir / "pre_metrics.json", pre_metrics)

        if args.no_apply:
            save_candidate_stub(iter_dir, candidate)

        stdout_path = iter_dir / "eval_stdout.log"
        stderr_path = iter_dir / "eval_stderr.log"
        commands = candidate.get("required_tests") or config.get("eval_commands") or []
        eval_ok = run_eval_commands(commands, REPO_ROOT, max_minutes, stdout_path, stderr_path)

        post_metrics = collect_metrics()
        write_json(iter_dir / "post_metrics.json", post_metrics)

        if git_available():
            save_git_diff(REPO_ROOT, iter_dir / "diff.patch")
            save_git_diff(REPO_ROOT, iter_dir / "forbidden_files.patch", resolve_forbidden(config))

        guard_post = guardrails_post(config)
        write_json(iter_dir / "guard_post.json", guard_post.__dict__)

        success_ok, success_failures = check_metric_thresholds(
            post_metrics,
            (candidate.get("success_criteria") or {}).get("metrics", {}),
            baseline_metrics,
        )
        _failure_ok, failure_failures = check_metric_thresholds(
            post_metrics,
            (candidate.get("failure_criteria") or {}).get("metrics", {}),
            baseline_metrics,
        )

        decision = "rejected"
        notes: list[str] = []
        if not eval_ok:
            decision = "failed"
            notes.append("eval command failed")
        if guard_post.errors:
            decision = "failed"
            notes.append("guardrails failed")
        if failure_failures:
            decision = "rejected"
            notes.extend(failure_failures)
        if success_ok and not failure_failures and eval_ok and guard_post.ok:
            decision = "accepted"
        else:
            if success_failures:
                notes.extend(success_failures)

        decision_payload = {
            "decision": decision,
            "notes": notes,
            "candidate_id": candidate.get("id"),
            "eval_ok": eval_ok,
            "guardrails_ok": guard_post.ok,
            "metric_deltas": compare_metrics(pre_metrics, post_metrics),
        }
        write_json(iter_dir / "decision.json", decision_payload)
        build_iteration_report(iter_dir, decision_payload)

        results.append({"iteration_id": iteration_id, "decision": decision, "candidate_id": candidate.get("id")})
        if decision == "accepted" and stop_on_first_success:
            break

    write_autoresearch_report(report_root, results)
    write_json(report_root / "autoresearch_results.json", {"run_id": run_id, "results": results})
    write_history(REPO_ROOT / config["report_paths"]["output_root"], {
        "run_id": run_id,
        "experiment_name": config.get("experiment_name"),
        "candidate_id": results[-1]["candidate_id"] if results else "",
        "decision": results[-1]["decision"] if results else "",
        "timestamp": run_id,
    })

    print(f"autoresearch run: {report_root}")


if __name__ == "__main__":
    main()
