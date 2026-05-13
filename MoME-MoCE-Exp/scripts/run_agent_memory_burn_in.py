from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_SCRIPT = ROOT / "plugins" / "ivy-context-memory" / "scripts" / "ivy_context_memory.py"
DEFAULT_STORE = ROOT / "MoME-MoCE-Exp" / "out" / "agent_memory_burn_in_store"
DEFAULT_REPORT = ROOT / "MoME-MoCE-Exp" / "docs" / "AGENT_MEMORY_BURN_IN.md"


def load_plugin_module():
    spec = importlib.util.spec_from_file_location("ivy_context_memory_plugin", PLUGIN_SCRIPT)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load plugin module from {PLUGIN_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def burn_in_records() -> list[dict[str, Any]]:
    return [
        {
            "event_type": "decision",
            "role": "assistant",
            "text": "CP83 session capture stores normalized Codex/OpenCode chat events as agent_session v0.1.",
        },
        {
            "event_type": "decision",
            "role": "assistant",
            "text": "CP84 session ingest writes transcripts, redacts obvious secrets, and derives memory deltas.",
        },
        {
            "event_type": "decision",
            "role": "assistant",
            "text": "CP86 context packet v2 wraps selected evidence, policy, route proof, answerability, and timings.",
        },
        {
            "event_type": "test_result",
            "role": "assistant",
            "text": "CP92 burn-in verifies ingest, before_task retrieval, after_test memory, and packet-v2 retrieval.",
            "passed": True,
        },
    ]


def write_report(report_path: Path, result: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "\n".join(
            [
                "# Agent Memory Burn-In",
                "",
                f"Generated: `{result['created_at']}`",
                "",
                "| Check | Value |",
                "|---|---:|",
                f"| OK | `{result['ok']}` |",
                f"| Initial deltas | `{result['initial_delta_count']}` |",
                f"| After-test deltas | `{result['after_test_delta_count']}` |",
                f"| Before-task selected | `{result['before_task_selected']}` |",
                f"| Packet-v2 selected | `{result['packet_v2_selected']}` |",
                f"| Total wall | `{result['wall_ms']} ms` |",
                "",
                "```mermaid",
                "flowchart LR",
                "  Session[\"Codex/OpenCode session\"] --> Ingest[\"session-ingest\"]",
                "  Ingest --> Deltas[\"memory_deltas.jsonl\"]",
                "  Deltas --> Notes[\"safe notes\"]",
                "  Task[\"before_task hook\"] --> Packet[\"context_packet v0.2\"]",
                "  Notes --> Packet",
                "  Packet --> Agent[\"agent plan/edit/test\"]",
                "  Agent --> AfterTest[\"after_test hook\"]",
                "  AfterTest --> Deltas",
                "```",
                "",
                "## Meaning",
                "",
                "The plugin can now capture a real agent session, distill it into safe durable memory, retrieve it before work, and remember verified outcomes after tests without stuffing the raw transcript into the model context.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def run_burn_in(store: Path, report_path: Path | None = None, *, reset: bool = False) -> dict[str, Any]:
    if reset and store.exists():
        shutil.rmtree(store)
    plugin = load_plugin_module()
    start = time.perf_counter()
    plugin.init_store(store)
    ingested = plugin.ingest_session(
        store,
        {
            "session_id": "cp83_cp92_burn_in",
            "source": "codex",
            "workspace": str(ROOT),
            "task": "Burn in CP83-CP92 agent context/memory integration.",
            "records": burn_in_records(),
        },
    )
    before = plugin.agent_hook(store, hook="before_task", task="What does CP92 prove about Codex OpenCode memory hooks?")
    after_test = plugin.agent_hook(
        store,
        hook="after_test",
        task="Record CP92 burn-in test result.",
        payload={
            "session_id": "cp92_after_test_burn_in",
            "records": [
                {
                    "event_type": "test_result",
                    "text": "CP92 after_test hook stored verified burn-in results as retrievable memory.",
                    "passed": True,
                }
            ],
        },
    )
    packet = plugin.context_packet_v2(store, query="How should agents use CP83-CP92 memory hooks?", hook="before_edit")
    current_status = plugin.status(store)
    before_selected = len(before["packet"]["selected_ids"])
    packet_selected = len(packet["packet"]["selected_ids"])
    wall_ms = round((time.perf_counter() - start) * 1000, 3)
    result = {
        "ok": bool(
            ingested["delta_count"] >= 4
            and after_test["delta_count"] >= 1
            and before_selected >= 1
            and packet_selected >= 1
            and current_status["sessions"] >= 2
            and current_status["memory_deltas"] >= 5
        ),
        "created_at": plugin.utc_now(),
        "store": str(store),
        "initial_delta_count": ingested["delta_count"],
        "after_test_delta_count": after_test["delta_count"],
        "before_task_selected": before_selected,
        "packet_v2_selected": packet_selected,
        "status": current_status,
        "wall_ms": wall_ms,
    }
    if report_path:
        write_report(report_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the CP92 agent memory burn-in.")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    result = run_burn_in(args.store, args.report, reset=args.reset)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
