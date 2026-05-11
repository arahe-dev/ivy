from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "mine_autoresearch_failures.py"


def test_failure_miner_extracts_selection_drift_case(tmp_path: Path) -> None:
    result = {
        "iterations": [
            {
                "candidates": [
                    {
                        "max_prefilter_items": 32,
                        "rows": [
                            {
                                "query": "What should memory select?",
                                "passed": True,
                                "router_latency_ms": 2.0,
                                "packet_mode": "proof_lite",
                                "selected_ids": ["note_fast"],
                            }
                        ],
                    },
                    {
                        "max_prefilter_items": 192,
                        "rows": [
                            {
                                "query": "What should memory select?",
                                "passed": True,
                                "router_latency_ms": 9.5,
                                "packet_mode": "proof_lite",
                                "selected_ids": ["doc_deep"],
                            }
                        ],
                    },
                ]
            }
        ]
    }
    result_path = tmp_path / "result.json"
    out_path = tmp_path / "cases.json"
    report_path = tmp_path / "report.md"
    result_path.write_text(json.dumps(result), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--result", str(result_path), "--out", str(out_path), "--report", str(report_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    payload = json.loads(proc.stdout)
    cases = json.loads(out_path.read_text(encoding="utf-8"))["cases"]

    assert payload["mined"] == 1
    assert cases[0]["query"] == "What should memory select?"
    assert cases[0]["required_source_ids"] == ["note_fast"]
    assert "selection_changes_with_prefilter_depth" in cases[0]["notes"]
    assert report_path.exists()
