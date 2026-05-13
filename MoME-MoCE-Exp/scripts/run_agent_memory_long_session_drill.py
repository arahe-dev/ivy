from __future__ import annotations

import argparse
import importlib.util
import json
import math
import shutil
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_SCRIPT = ROOT / "plugins" / "ivy-context-memory" / "scripts" / "ivy_context_memory.py"
DEFAULT_STORE = ROOT / "MoME-MoCE-Exp" / "out" / "agent_memory_long_session_store"
DEFAULT_REPORT = ROOT / "MoME-MoCE-Exp" / "docs" / "AGENT_MEMORY_LONG_SESSION_DRILL.md"


def load_plugin_module():
    spec = importlib.util.spec_from_file_location("ivy_context_memory_plugin", PLUGIN_SCRIPT)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load plugin module from {PLUGIN_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_records(count: int) -> list[dict[str, Any]]:
    filler_count = max(0, count - 3)
    records = [
        {
            "event_type": "message",
            "role": "assistant",
            "text": f"Non-durable scratch turn {idx}: implementation chatter that should stay in the session file but not become memory.",
        }
        for idx in range(filler_count)
    ]
    records.extend(
        [
            {
                "event_type": "decision",
                "text": "CP100 long-session drill proves large raw conversations can be distilled into a few durable memory deltas.",
            },
            {
                "event_type": "test_result",
                "text": "CP100 retrieval after long-session ingest selected the durable long-session evidence.",
                "passed": True,
            },
            {
                "event_type": "outcome",
                "text": "CP100 supports the unlimited context claim by storing transcripts externally and retrieving compact packet-v2 memory.",
            },
        ]
    )
    return records


def run_long_session_drill(
    store: Path,
    report: Path | None = None,
    *,
    records: int = 1000,
    target_tokens: int = 10_000_000,
    reset: bool = False,
) -> dict[str, Any]:
    if reset and store.exists():
        shutil.rmtree(store)
    plugin = load_plugin_module()
    started = time.perf_counter()
    plugin.init_store(store)
    session_records = make_records(records)
    raw_tokens = sum(plugin.rough_tokens(record["text"]) for record in session_records)
    ingested = plugin.ingest_session(
        store,
        {
            "session_id": f"cp100_long_session_{records}",
            "source": "codex_long_session_drill",
            "workspace": str(ROOT),
            "task": "Run CP100 long-session memory drill.",
            "records": session_records,
        },
    )
    packet = plugin.context_packet_v2(store, query="What does CP100 prove about long sessions and unlimited context?", hook="before_task")
    status = plugin.status(store)
    projected_shards = max(1, math.ceil(target_tokens / max(1, raw_tokens)))
    result = {
        "ok": bool(ingested["delta_count"] == 3 and packet["packet"]["selected_ids"] and status["memory_deltas"] >= 3),
        "created_at": plugin.utc_now(),
        "store": str(store),
        "records": records,
        "raw_tokens_estimate": raw_tokens,
        "target_tokens": target_tokens,
        "projected_shards_for_target": projected_shards,
        "delta_count": ingested["delta_count"],
        "selected_count": len(packet["packet"]["selected_ids"]),
        "packet_wall_ms": packet["timings_ms"]["total"],
        "wall_ms": round((time.perf_counter() - started) * 1000, 3),
    }
    if report:
        write_report(report, result)
    return result


def write_report(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# Agent Memory Long-Session Drill",
                "",
                f"Generated: `{result['created_at']}`",
                f"OK: `{result['ok']}`",
                "",
                "| Metric | Value |",
                "|---|---:|",
                f"| Records | `{result['records']}` |",
                f"| Raw tokens estimate | `{result['raw_tokens_estimate']}` |",
                f"| Durable deltas | `{result['delta_count']}` |",
                f"| Selected evidence | `{result['selected_count']}` |",
                f"| Packet wall | `{result['packet_wall_ms']} ms` |",
                f"| 10M-token projected shards | `{result['projected_shards_for_target']}` |",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CP100 long-session memory drill.")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--records", type=int, default=1000)
    parser.add_argument("--target-tokens", type=int, default=10_000_000)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    result = run_long_session_drill(args.store, args.report, records=args.records, target_tokens=args.target_tokens, reset=args.reset)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
