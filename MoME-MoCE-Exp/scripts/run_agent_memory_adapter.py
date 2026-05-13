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
DEFAULT_STORE = ROOT / "MoME-MoCE-Exp" / "out" / "agent_memory_adapter_store"
DEFAULT_REPORT = ROOT / "MoME-MoCE-Exp" / "docs" / "AGENT_MEMORY_ADAPTER_RUN.md"


def load_plugin_module():
    spec = importlib.util.spec_from_file_location("ivy_context_memory_plugin", PLUGIN_SCRIPT)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load plugin module from {PLUGIN_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_report(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# Agent Memory Adapter Run",
                "",
                f"Generated: `{result['created_at']}`",
                f"OK: `{result['ok']}`",
                "",
                "| Hook | Selected | Deltas |",
                "|---|---:|---:|",
                f"| before_task | `{result['before_task_selected']}` | `` |",
                f"| before_edit | `{result['before_edit_selected']}` | `` |",
                f"| after_test | `` | `{result['after_test_delta_count']}` |",
                f"| after_task | `` | `{result['after_task_delta_count']}` |",
                "",
                "```mermaid",
                "sequenceDiagram",
                "  participant Agent",
                "  participant Adapter",
                "  participant Memory",
                "  Agent->>Adapter: task",
                "  Adapter->>Memory: before_task",
                "  Adapter->>Memory: before_edit",
                "  Agent->>Adapter: test result",
                "  Adapter->>Memory: after_test",
                "  Agent->>Adapter: final outcome",
                "  Adapter->>Memory: after_task",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )


def run_adapter(store: Path, report: Path | None = None, *, reset: bool = False) -> dict[str, Any]:
    if reset and store.exists():
        shutil.rmtree(store)
    plugin = load_plugin_module()
    started = time.perf_counter()
    plugin.init_store(store)
    plugin.ingest_session(
        store,
        {
            "session_id": "cp93_adapter_seed",
            "source": "codex",
            "workspace": str(ROOT),
            "task": "Seed CP93 adapter memory.",
            "records": [
                {
                    "event_type": "decision",
                    "text": "CP93 agent adapter automatically calls before_task, before_edit, after_test, and after_task hooks around coding work.",
                }
            ],
        },
    )
    before_task = plugin.agent_hook(store, hook="before_task", task="What does the CP93 agent adapter do?")
    before_edit = plugin.agent_hook(store, hook="before_edit", task="How should CP93 adapter handle file edits?")
    after_test = plugin.agent_hook(
        store,
        hook="after_test",
        task="Record CP94 adapter verification.",
        payload={
            "session_id": "cp94_adapter_after_test",
            "records": [
                {
                    "event_type": "test_result",
                    "text": "CP94 adapter hook runner verified before_task, before_edit, after_test, and after_task sequencing.",
                    "passed": True,
                }
            ],
        },
    )
    after_task = plugin.agent_hook(
        store,
        hook="after_task",
        task="Finish CP95 adapter contract.",
        payload={
            "session_id": "cp95_adapter_after_task",
            "records": [
                {
                    "event_type": "outcome",
                    "text": "CP95 adapter contract gives Codex and OpenCode a minimal automatic memory lifecycle without manual query calls.",
                }
            ],
        },
    )
    doctor = plugin.agent_memory_doctor(store)
    result = {
        "ok": bool(
            before_task["packet"]["selected_ids"]
            and before_edit["packet"]["selected_ids"]
            and after_test["delta_count"] == 1
            and after_task["delta_count"] == 1
            and doctor["ok"]
        ),
        "created_at": plugin.utc_now(),
        "store": str(store),
        "before_task_selected": len(before_task["packet"]["selected_ids"]),
        "before_edit_selected": len(before_edit["packet"]["selected_ids"]),
        "after_test_delta_count": after_test["delta_count"],
        "after_task_delta_count": after_task["delta_count"],
        "doctor_ok": doctor["ok"],
        "wall_ms": round((time.perf_counter() - started) * 1000, 3),
    }
    if report:
        write_report(report, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a CP93-CP95 agent memory adapter lifecycle.")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    result = run_adapter(args.store, args.report, reset=args.reset)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
