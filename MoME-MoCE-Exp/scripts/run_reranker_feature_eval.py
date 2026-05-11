from __future__ import annotations

import argparse
import importlib.util
import json
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


def write_feature_report(results: list[dict[str, Any]], winner: dict[str, Any], out: Path) -> None:
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
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate deterministic reranker feature profiles against mined cases.")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-prefilter-items", type=int, default=32)
    args = parser.parse_args()

    results, winner = run_feature_eval(args.store.resolve(), args.cases.resolve(), max_prefilter_items=args.max_prefilter_items)
    write_feature_report(results, winner, args.out.resolve())
    print(json.dumps({"ok": True, "winner": winner, "report": str(args.out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
