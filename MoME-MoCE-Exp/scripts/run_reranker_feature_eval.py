from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from run_mined_case_policy_eval import evaluate, load_cases
except ModuleNotFoundError:
    from scripts.run_mined_case_policy_eval import evaluate, load_cases


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
PLUGIN_SCRIPT = REPO_ROOT / "plugins" / "ivy-context-memory" / "scripts" / "ivy_context_memory.py"
DEFAULT_STORE = ROOT / "out" / "autoresearch_loop" / "memory_store"
DEFAULT_CASES = ROOT / "docs" / "AUTORESEARCH_MINED_EVAL_CASES.json"
DEFAULT_OUT = ROOT / "docs" / "AUTORESEARCH_RERANKER_FEATURE_EVAL.md"


FEATURE_PROFILES: dict[str, dict[str, Any]] = {
    "baseline": {
        "prefilter_feature_profile": "baseline",
        "prefilter_feature_weights": {"agent_note_boost": 500.0},
    },
    "checkpoint_guard": {
        "prefilter_feature_profile": "checkpoint_guard",
        "prefilter_feature_weights": {
            "agent_note_boost": 500.0,
            "checkpoint_match_boost": 220.0,
            "agent_note_checkpoint_mismatch_penalty": -320.0,
        },
    },
    "code_penalty": {
        "prefilter_feature_profile": "code_penalty",
        "prefilter_feature_weights": {
            "agent_note_boost": 500.0,
            "checkpoint_match_boost": 160.0,
            "agent_note_checkpoint_mismatch_penalty": -220.0,
            "source_code_non_code_penalty": -180.0,
        },
    },
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_plugin() -> Any:
    spec = importlib.util.spec_from_file_location("ivy_context_memory_feature_eval", PLUGIN_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load plugin: {PLUGIN_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def policy_path(store: Path) -> Path:
    return store / "policy" / "autoresearch_policy.json"


def read_policy(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_policy(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_feature_eval(store: Path, cases_path: Path, *, max_prefilter_items: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cases = load_cases(cases_path)
    path = policy_path(store)
    original = read_policy(path)
    results: list[dict[str, Any]] = []
    try:
        for name, profile in FEATURE_PROFILES.items():
            policy = {
                "schema_version": "ivy_context_memory.autoresearch_policy.v0.1",
                "max_prefilter_items": max_prefilter_items,
                **profile,
            }
            write_policy(path, policy)
            result = evaluate(store, cases, max_prefilter_items=max_prefilter_items)
            result["feature_profile"] = name
            results.append(result)
    finally:
        if original is None:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        else:
            write_policy(path, original)
    ranked = sorted(results, key=lambda row: (row["passed"], -row["avg_router_latency_ms"], -row["avg_wall_ms"]), reverse=True)
    winner = ranked[0]
    return ranked, winner


def baseline_result(results: list[dict[str, Any]]) -> dict[str, Any]:
    for row in results:
        if row.get("feature_profile") == "baseline":
            return row
    raise ValueError("baseline result missing")


def promotion_decision(winner: dict[str, Any], baseline: dict[str, Any]) -> tuple[bool, str]:
    if winner.get("feature_profile") == "baseline":
        return False, "baseline already wins"
    if int(winner.get("passed", 0)) < int(winner.get("total", 0)):
        return False, "winner does not pass all cases"
    if int(winner.get("passed", 0)) < int(baseline.get("passed", 0)):
        return False, "winner regresses pass count versus baseline"
    if float(winner.get("avg_router_latency_ms", 0.0)) > float(baseline.get("avg_router_latency_ms", 0.0)):
        return False, "winner is slower than baseline on router latency"
    return True, "winner preserves pass rate and improves router latency"


def promote_winner_policy(store: Path, winner: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    should_promote, reason = promotion_decision(winner, baseline)
    if not should_promote:
        return {"promoted": False, "reason": reason}
    profile_name = str(winner["feature_profile"])
    current = read_policy(policy_path(store)) or {}
    next_policy = {
        **current,
        "schema_version": "ivy_context_memory.autoresearch_policy.v0.1",
        "updated_at": utc_now(),
        "iteration": int(current.get("iteration", 0)) + 1,
        "max_prefilter_items": int(winner["max_prefilter_items"]),
        "objective": "minimum latency with all benchmark expectations passing",
        **FEATURE_PROFILES[profile_name],
        "feature_eval_metrics": {
            "baseline": {
                "passed": baseline["passed"],
                "total": baseline["total"],
                "avg_wall_ms": baseline["avg_wall_ms"],
                "avg_router_latency_ms": baseline["avg_router_latency_ms"],
            },
            "winner": {
                "profile": profile_name,
                "passed": winner["passed"],
                "total": winner["total"],
                "avg_wall_ms": winner["avg_wall_ms"],
                "avg_router_latency_ms": winner["avg_router_latency_ms"],
            },
            "promotion_reason": reason,
        },
    }
    write_policy(policy_path(store), next_policy)
    return {"promoted": True, "reason": reason, "policy": str(policy_path(store)), "profile": profile_name}


def write_feature_report(results: list[dict[str, Any]], winner: dict[str, Any], out: Path, promotion: dict[str, Any] | None = None) -> None:
    lines = [
        "# Autoresearch Reranker Feature Eval",
        "",
        f"Winner: `{winner['feature_profile']}` at `max_prefilter_items={winner['max_prefilter_items']}`",
        "",
        "| Profile | Passed | Avg wall ms | Avg router ms |",
        "|---|---:|---:|---:|",
    ]
    for row in results:
        lines.append(f"| {row['feature_profile']} | {row['passed']} / {row['total']} | {row['avg_wall_ms']} | {row['avg_router_latency_ms']} |")
    lines.extend(["", "## Details", ""])
    for row in results:
        lines.append(f"### {row['feature_profile']}")
        lines.append("")
        lines.append("| Case | Pass | Mode | Selected | Router ms |")
        lines.append("|---|---|---|---|---:|")
        for item in row["rows"]:
            lines.append(
                f"| {item['case_id']} | {item['passed']} | {item['packet_mode']} | "
                f"`{', '.join(item['selected_ids']) or 'none'}` | {item['router_latency_ms']} |"
            )
        lines.append("")
    if promotion is not None:
        lines.extend(
            [
                "## Promotion",
                "",
                f"- promoted: `{promotion.get('promoted')}`",
                f"- reason: `{promotion.get('reason')}`",
            ]
        )
        if promotion.get("policy"):
            lines.append(f"- policy: `{promotion['policy']}`")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate deterministic reranker feature profiles against mined cases.")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-prefilter-items", type=int, default=32)
    parser.add_argument("--promote", action="store_true", help="Write the winning profile to the runtime policy when it beats baseline safely.")
    args = parser.parse_args()

    results, winner = run_feature_eval(args.store.resolve(), args.cases.resolve(), max_prefilter_items=args.max_prefilter_items)
    promotion = promote_winner_policy(args.store.resolve(), winner, baseline_result(results)) if args.promote else None
    write_feature_report(results, winner, args.out.resolve(), promotion=promotion)
    print(json.dumps({"ok": True, "winner": winner, "promotion": promotion, "report": str(args.out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
