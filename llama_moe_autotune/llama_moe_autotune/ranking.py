from __future__ import annotations

from typing import Any


def rank_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(results, key=_score, reverse=True)
    for rank, result in enumerate(ranked, start=1):
        result["rank"] = rank
        result["score"] = round(_score(result), 4)
    return ranked


def best_result(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    ranked = rank_results([dict(item) for item in results])
    for result in ranked:
        if result.get("outcome") == "success":
            return result
    return None


def safest_result(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    successes = [item for item in results if item.get("outcome") == "success"]
    if not successes:
        return None
    return sorted(successes, key=_safe_key)[0]


def _score(result: dict[str, Any]) -> float:
    outcome = result.get("outcome")
    if outcome != "success":
        return -1000.0 + _failure_penalty(outcome)
    tps = float(result.get("decode_tps") or result.get("metrics", {}).get("decode_tps") or 0)
    wall = float(result.get("wall_seconds") or 9999)
    prompt_ms = float(result.get("metrics", {}).get("prompt_ms") or 0)
    estimated_penalty = 3.0 if result.get("decode_tps_estimated") else 0.0
    complexity = _complexity_penalty(result)
    memory_penalty = _memory_penalty(result)
    return tps * 100.0 - wall * 0.05 - prompt_ms * 0.002 - estimated_penalty - complexity - memory_penalty


def _safe_key(result: dict[str, Any]) -> tuple[float, int, int, int]:
    candidate = result.get("candidate", {})
    ngl = candidate.get("ngl", 0)
    ngl_num = ngl if isinstance(ngl, int) else 999
    return (
        -float(result.get("decode_tps") or 0),
        int(candidate.get("context") or 999999),
        int(ngl_num),
        int(candidate.get("batch") or 999999),
    )


def _failure_penalty(outcome: str | None) -> float:
    if outcome == "parse failure but command completed":
        return 100.0
    if outcome == "unsupported flag":
        return -50.0
    if outcome == "timeout":
        return -100.0
    if outcome == "out of memory":
        return -200.0
    return -150.0


def _complexity_penalty(result: dict[str, Any]) -> float:
    candidate = result.get("candidate", {})
    penalty = 0.0
    if candidate.get("direct_io"):
        penalty += 1.0
    if candidate.get("n_cpu_moe") is not None:
        penalty += 1.0
    if candidate.get("ngl") in ("auto", "all"):
        penalty += 0.5
    return penalty


def _memory_penalty(result: dict[str, Any]) -> float:
    gpu_before = result.get("gpu_before", {})
    gpu_after = result.get("gpu_after", {})
    try:
        before = gpu_before.get("gpus", [{}])[0].get("memory_free_mib")
        after = gpu_after.get("gpus", [{}])[0].get("memory_free_mib")
        if before is not None and after is not None:
            used = max(0, before - after)
            return used / 4096.0
    except Exception:
        pass
    return 0.0
