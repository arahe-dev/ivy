from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_SCRIPT = ROOT / "plugins" / "ivy-context-memory" / "scripts" / "ivy_context_memory.py"
DEFAULT_STORE = ROOT / "MoME-MoCE-Exp" / "out" / "agent_memory_answer_ab_store"
DEFAULT_REPORT = ROOT / "MoME-MoCE-Exp" / "docs" / "AGENT_MEMORY_ANSWER_AB.md"


CASES = [
    {
        "id": "cp96_answer_quality",
        "query": "What does CP96 prove about agent memory answer quality?",
        "expected_terms": ["cp96", "answer-quality", "packet-v2", "without memory"],
    },
    {
        "id": "cp97_task_outcome",
        "query": "What CP97 result should future agents remember?",
        "expected_terms": ["cp97", "with-memory", "selected evidence"],
    },
    {
        "id": "cp98_batch_ingest",
        "query": "Why does CP98 batch ingest matter?",
        "expected_terms": ["cp98", "batch ingest", "single rebuild"],
    },
]


def load_plugin_module():
    spec = importlib.util.spec_from_file_location("ivy_context_memory_plugin", PLUGIN_SCRIPT)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load plugin module from {PLUGIN_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seed_memory(plugin: Any, store: Path) -> dict[str, Any]:
    return plugin.ingest_session_batch(
        store,
        {
            "sessions": [
                {
                    "session_id": "cp96_answer_quality",
                    "task": "Seed answer-quality A/B memory.",
                    "records": [
                        {
                            "event_type": "decision",
                            "text": "CP96 answer-quality A/B shows packet-v2 memory answers with selected evidence while the without memory baseline abstains.",
                        }
                    ],
                },
                {
                    "session_id": "cp97_task_outcome",
                    "task": "Seed future agent outcome memory.",
                    "records": [
                        {
                            "event_type": "outcome",
                            "text": "CP97 with-memory mode produces selected evidence for future agents and no-memory mode cannot cite anything.",
                        }
                    ],
                },
                {
                    "session_id": "cp98_batch_ingest",
                    "task": "Seed batch ingest memory.",
                    "records": [
                        {
                            "event_type": "decision",
                            "text": "CP98 batch ingest matters because many session deltas can be remembered with a single rebuild instead of rebuilding after every note.",
                        }
                    ],
                },
            ]
        },
    )


def score_packet(packet_text: str, selected_ids: list[str], expected_terms: list[str]) -> dict[str, Any]:
    lower = packet_text.lower()
    missing_terms = [term for term in expected_terms if term.lower() not in lower]
    passed = bool(selected_ids) and not missing_terms
    return {"passed": passed, "missing_terms": missing_terms, "selected_ids": selected_ids}


def run_answer_ab(store: Path, report: Path | None = None, *, reset: bool = False) -> dict[str, Any]:
    if reset and store.exists():
        shutil.rmtree(store)
    plugin = load_plugin_module()
    plugin.init_store(store)
    seeded = seed_memory(plugin, store)
    rows = []
    for case in CASES:
        no_memory = {"passed": False, "missing_terms": list(case["expected_terms"]), "selected_ids": []}
        packet = plugin.context_packet_v2(store, query=case["query"], hook="before_task")
        with_memory = score_packet(packet["packet"]["text"], list(packet["packet"]["selected_ids"]), list(case["expected_terms"]))
        rows.append({"case": case, "no_memory": no_memory, "with_memory": with_memory, "wall_ms": packet["timings_ms"]["total"]})
    no_memory_passed = sum(1 for row in rows if row["no_memory"]["passed"])
    with_memory_passed = sum(1 for row in rows if row["with_memory"]["passed"])
    result = {
        "ok": with_memory_passed == len(rows) and no_memory_passed == 0,
        "created_at": plugin.utc_now(),
        "store": str(store),
        "seeded_delta_count": seeded["delta_count"],
        "cases": len(rows),
        "no_memory_passed": no_memory_passed,
        "with_memory_passed": with_memory_passed,
        "with_memory_quality": round(with_memory_passed / len(rows), 4),
        "no_memory_quality": round(no_memory_passed / len(rows), 4),
        "avg_packet_wall_ms": round(statistics.fmean(row["wall_ms"] for row in rows), 3),
        "rows": rows,
    }
    if report:
        write_report(report, result)
    return result


def write_report(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Agent Memory Answer A/B",
        "",
        f"Generated: `{result['created_at']}`",
        f"OK: `{result['ok']}`",
        "",
        "| Mode | Passed | Quality |",
        "|---|---:|---:|",
        f"| no memory | `{result['no_memory_passed']} / {result['cases']}` | `{result['no_memory_quality']}` |",
        f"| packet-v2 memory | `{result['with_memory_passed']} / {result['cases']}` | `{result['with_memory_quality']}` |",
        "",
        "| Case | Memory selected | Missing terms |",
        "|---|---:|---|",
    ]
    for row in result["rows"]:
        lines.append(
            f"| `{row['case']['id']}` | `{', '.join(row['with_memory']['selected_ids'])}` | `{', '.join(row['with_memory']['missing_terms'])}` |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CP96-CP98 answer-quality A/B for agent memory.")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    result = run_answer_ab(args.store, args.report, reset=args.reset)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
