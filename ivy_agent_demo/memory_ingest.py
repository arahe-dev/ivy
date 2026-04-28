from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from .memory_store import MemoryStore, utc_now


ARTIFACT_PATTERNS = [
    "run_summary.json",
    "final_answer.txt",
    "tool_call_*.json",
    "tool_result_*.json",
    "validation_*.json",
    "model_request_*.json",
    "model_response_*.json",
    "result.json",
    "failure.json",
    "response.json",
    "config.json",
    "summary.csv",
    "report.md",
]


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def read_text(path: Path, limit: int = 4000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        return ""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def short_text(value: Any, max_len: int = 240) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = json.dumps(value, sort_keys=True, ensure_ascii=True)
    value = re.sub(r"\s+", " ", value).strip()
    return value[: max_len - 3] + "..." if len(value) > max_len else value


def hash_args(args: Any) -> str:
    canonical = json.dumps(args if args is not None else {}, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def summarize_args(args: Any) -> str:
    if not isinstance(args, dict):
        return short_text(args)
    parts = []
    for key in sorted(args):
        value = args[key]
        if key.lower() in {"content", "text", "body"}:
            parts.append(f"{key}=<text:{len(str(value))} chars>")
        else:
            parts.append(f"{key}={short_text(value, 80)}")
    return short_text(", ".join(parts), 240)


def summarize_result(result: Any) -> str:
    if isinstance(result, dict):
        safe = {}
        for key in sorted(result):
            value = result[key]
            if key.lower() in {"content", "stdout", "stderr", "text"}:
                safe[key] = f"<text:{len(str(value))} chars>"
            else:
                safe[key] = value
        return short_text(safe)
    return short_text(result)


def discover_run_dirs(root: Path) -> list[Path]:
    candidates = []
    for path in root.rglob("*"):
        if not path.is_dir():
            continue
        if any((path / name).exists() for name in ("run_summary.json", "result.json", "failure.json", "config.json")):
            candidates.append(path)
    return sorted(candidates)


def artifact_kind(path: Path) -> str:
    name = path.name
    if name.startswith("tool_call_"):
        return "tool_call"
    if name.startswith("tool_result_"):
        return "tool_result"
    if name.startswith("validation_"):
        return "validation"
    if name.startswith("model_request_"):
        return "model_request"
    if name.startswith("model_response_"):
        return "model_response"
    return path.stem


def iter_artifacts(run_dir: Path) -> Iterable[Path]:
    seen: set[Path] = set()
    for pattern in ARTIFACT_PATTERNS:
        for path in run_dir.glob(pattern):
            if path.is_file() and path not in seen:
                seen.add(path)
                yield path


def infer_episode(run_dir: Path) -> dict[str, Any]:
    summary = read_json(run_dir / "run_summary.json")
    result = read_json(run_dir / "result.json")
    failure = read_json(run_dir / "failure.json")
    config = read_json(run_dir / "config.json")

    if isinstance(summary, dict):
        return {
            "run_id": summary.get("scenario_id") or run_dir.name,
            "task_text": summary.get("user_task"),
            "outcome": summary.get("verdict") or summary.get("status"),
            "success": summary.get("passed") if "passed" in summary else summary.get("scenario_pass"),
            "failure_type": None if summary.get("passed") else summary.get("notes"),
            "artifact_path": str(run_dir),
            "model_profile": None,
            "total_steps": len(summary.get("steps") or []),
            "source_kind": "agent_demo",
        }

    if isinstance(result, dict) or isinstance(failure, dict) or isinstance(config, dict):
        success = bool(result.get("http_success")) if isinstance(result, dict) else False
        task = None
        request = read_json(run_dir / "request.json")
        if isinstance(request, dict):
            task = short_text(request.get("prompt"), 500)
        model_profile = None
        if isinstance(config, dict):
            model_profile = Path(str(config.get("model_path", ""))).name or None
        return {
            "run_id": run_dir.name,
            "task_text": task,
            "outcome": "http_success" if success else "failed",
            "success": success,
            "failure_type": failure.get("error") if isinstance(failure, dict) else None,
            "artifact_path": str(run_dir),
            "model_profile": model_profile,
            "total_steps": None,
            "source_kind": "benchmark",
        }

    return {
        "run_id": run_dir.name,
        "task_text": None,
        "outcome": None,
        "success": None,
        "failure_type": None,
        "artifact_path": str(run_dir),
        "model_profile": None,
        "total_steps": None,
        "source_kind": "unknown",
    }


def create_memory_items(run_dir: Path, episode_id: int, episode: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    summary = read_json(run_dir / "run_summary.json")
    failure = read_json(run_dir / "failure.json")
    result = read_json(run_dir / "result.json")
    response = read_json(run_dir / "response.json")
    config = read_json(run_dir / "config.json")

    if isinstance(summary, dict):
        if summary.get("passed") or summary.get("scenario_pass"):
            items.append({
                "kind": "successful_pattern",
                "text": f"Scenario {summary.get('scenario_id')} succeeded with tools {summary.get('tool_calls', [])}: {short_text(summary.get('notes'), 180)}",
                "importance": 0.6,
                "confidence": 0.9,
                "source_artifact_path": str(run_dir / "run_summary.json"),
            })
        else:
            items.append({
                "kind": "failure_warning",
                "text": f"Scenario {summary.get('scenario_id')} failed or stopped safely: {short_text(summary.get('notes') or summary.get('final_answer'), 220)}",
                "importance": 0.7,
                "confidence": 0.9,
                "source_artifact_path": str(run_dir / "run_summary.json"),
            })
        for blocked in summary.get("blocked_calls") or []:
            items.append({
                "kind": "policy_warning",
                "text": f"Policy blocked tool {blocked.get('tool')} with failures {blocked.get('failures')}.",
                "importance": 0.8,
                "confidence": 0.95,
                "source_artifact_path": str(run_dir / "run_summary.json"),
            })

    for validation_path in run_dir.glob("validation_*.json"):
        data = read_json(validation_path)
        if isinstance(data, dict) and not data.get("ok", True):
            failures = data.get("failure_taxonomy") or []
            items.append({
                "kind": "validation_warning",
                "text": f"Validation failed with taxonomy {failures}.",
                "importance": 0.75,
                "confidence": 0.95,
                "source_artifact_path": str(validation_path),
            })
        raw = data.get("raw_output") if isinstance(data, dict) else ""
        if isinstance(raw, str) and re.search(r"</?think>", raw, re.IGNORECASE):
            items.append({
                "kind": "json_contamination_warning",
                "text": "Model output contained think tags in a validated response artifact.",
                "importance": 0.8,
                "confidence": 0.9,
                "source_artifact_path": str(validation_path),
            })

    content = response.get("content") if isinstance(response, dict) else ""
    if isinstance(content, str) and re.search(r"</?think>", content, re.IGNORECASE):
        items.append({
            "kind": "json_contamination_warning",
            "text": "Benchmark response contained think tags before or inside generated text.",
            "importance": 0.65,
            "confidence": 0.85,
            "source_artifact_path": str(run_dir / "response.json"),
        })

    if isinstance(result, dict) and isinstance(config, dict):
        timings = response.get("timings") if isinstance(response, dict) else {}
        tps = timings.get("predicted_per_second") if isinstance(timings, dict) else None
        items.append({
            "kind": "benchmark_result",
            "text": (
                f"Qwen benchmark config ctx={config.get('ctx')} cache_k={config.get('cache_k')} "
                f"cache_v={config.get('cache_v')} cpu_moe={config.get('cpu_moe')} "
                f"n_gpu_layers={config.get('n_gpu_layers')} prompt={config.get('prompt_name')} "
                f"http_success={result.get('http_success')} decode_tps={tps}."
            ),
            "importance": 0.55,
            "confidence": 0.9,
            "source_artifact_path": str(run_dir / "result.json"),
        })

    if isinstance(failure, dict):
        items.append({
            "kind": "failure_warning",
            "text": f"Run failed during load/start/request: {short_text(failure.get('error'), 240)}",
            "importance": 0.75,
            "confidence": 0.9,
            "source_artifact_path": str(run_dir / "failure.json"),
        })

    return items


def ingest_run_dir(run_dir: str | Path, db_path: str | Path | None = None) -> dict[str, int]:
    run_dir = Path(run_dir)
    if not run_dir.exists() or not run_dir.is_dir():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")
    store = MemoryStore(db_path)
    store.init_schema()
    episode = infer_episode(run_dir)
    conn = store.connect()
    try:
        with conn:
            cur = conn.execute(
                """
                INSERT INTO episodes
                (run_id, created_at, task_text, outcome, success, failure_type, artifact_path, model_profile, total_steps, source_kind)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    episode.get("run_id"),
                    utc_now(),
                    episode.get("task_text"),
                    episode.get("outcome"),
                    None if episode.get("success") is None else int(bool(episode.get("success"))),
                    episode.get("failure_type"),
                    episode.get("artifact_path"),
                    episode.get("model_profile"),
                    episode.get("total_steps"),
                    episode.get("source_kind"),
                ),
            )
            episode_id = int(cur.lastrowid)
            artifact_count = 0
            for artifact in iter_artifacts(run_dir):
                conn.execute(
                    """
                    INSERT OR IGNORE INTO artifacts(episode_id, path, kind, sha256, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (episode_id, str(artifact), artifact_kind(artifact), sha256_file(artifact), utc_now()),
                )
                artifact_count += 1

            tool_count = 0
            for call_path in sorted(run_dir.glob("tool_call_*.json")):
                call = read_json(call_path)
                if not isinstance(call, dict):
                    continue
                step_match = re.search(r"tool_call_(\d+)", call_path.name)
                step = int(step_match.group(1)) if step_match else None
                result_path = run_dir / f"tool_result_{step}.json" if step is not None else None
                result = read_json(result_path) if result_path and result_path.exists() else None
                args = call.get("arguments")
                conn.execute(
                    """
                    INSERT INTO tool_traces
                    (episode_id, step_index, tool_name, status, args_summary, args_hash, result_summary, artifact_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        episode_id,
                        step,
                        call.get("tool"),
                        "approved" if call.get("policy_approved") else "blocked",
                        summarize_args(args),
                        hash_args(args),
                        summarize_result(result.get("result") if isinstance(result, dict) else result),
                        str(call_path),
                    ),
                )
                tool_count += 1

            item_count = 0
            for item in create_memory_items(run_dir, episode_id, episode):
                store.insert_memory_item(conn, source_episode_id=episode_id, status="active", **item)
                item_count += 1
    finally:
        conn.close()
    return {"episodes": 1, "artifacts": artifact_count, "tool_traces": tool_count, "memory_items": item_count}


def ingest_runs_root(runs_root: str | Path, db_path: str | Path | None = None) -> dict[str, int]:
    totals = {"episodes": 0, "artifacts": 0, "tool_traces": 0, "memory_items": 0}
    for run_dir in discover_run_dirs(Path(runs_root)):
        counts = ingest_run_dir(run_dir, db_path)
        for key, value in counts.items():
            totals[key] += value
    return totals
