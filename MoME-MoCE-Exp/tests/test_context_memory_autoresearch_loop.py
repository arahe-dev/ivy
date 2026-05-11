from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_context_memory_autoresearch_loop.py"


def test_autoresearch_loop_stashes_realish_conversation_and_rates_capacity(tmp_path: Path) -> None:
    convo_root = tmp_path / "sessions"
    convo_root.mkdir()
    (convo_root / "rollout.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"role": "user", "content": "Build an IVY memory plugin that can query context before coding tasks."}),
                json.dumps({"role": "assistant", "content": "Implemented MCP tools, benchmark loops, and safe note writeback for context memory."}),
            ]
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    store = tmp_path / "store"
    scoreboard = tmp_path / "scoreboard.md"

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--store",
            str(store),
            "--out-dir",
            str(out_dir),
            "--conversation-root",
            str(convo_root),
            "--max-conversation-files",
            "1",
            "--max-records",
            "4",
            "--iterations",
            "1",
            "--target-token-rating",
            "1000",
            "--scoreboard-path",
            str(scoreboard),
            "--reset",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    payload = json.loads(proc.stdout)
    result = json.loads((out_dir / "autoresearch_loop_result.json").read_text(encoding="utf-8"))

    assert payload["ok"] is True
    assert result["stash"]["records"] == 2
    assert result["capacity_rating"]["target_tokens"] == 1000
    assert "max_prefilter_items" in result["selected_policy"]
    assert scoreboard.exists()
