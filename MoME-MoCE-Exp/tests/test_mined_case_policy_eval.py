from __future__ import annotations

import json
from pathlib import Path

from scripts.run_mined_case_policy_eval import write_report


def test_mined_case_policy_report_selects_fastest_full_pass(tmp_path: Path) -> None:
    out = tmp_path / "report.md"
    report = write_report(
        [
            {"max_prefilter_items": 64, "passed": 1, "total": 1, "avg_wall_ms": 20.0, "avg_router_latency_ms": 4.0, "rows": []},
            {"max_prefilter_items": 32, "passed": 1, "total": 1, "avg_wall_ms": 10.0, "avg_router_latency_ms": 2.0, "rows": []},
        ],
        out,
    )

    assert report["winner"]["max_prefilter_items"] == 32
    assert "max_prefilter_items = 32" in out.read_text(encoding="utf-8")
