from __future__ import annotations

import json
from pathlib import Path

from scripts.run_reranker_feature_eval import FEATURE_PROFILES, write_feature_report


def test_feature_profiles_are_named_and_reported(tmp_path: Path) -> None:
    assert "checkpoint_guard" in FEATURE_PROFILES
    out = tmp_path / "feature_report.md"
    row = {
        "feature_profile": "checkpoint_guard",
        "max_prefilter_items": 32,
        "passed": 1,
        "total": 1,
        "avg_wall_ms": 10.0,
        "avg_router_latency_ms": 2.0,
        "rows": [
            {
                "case_id": "case_1",
                "passed": True,
                "packet_mode": "proof_lite",
                "selected_ids": ["note_1"],
                "router_latency_ms": 2.0,
            }
        ],
    }
    write_feature_report([row], row, out)

    text = out.read_text(encoding="utf-8")
    assert "checkpoint_guard" in text
    assert "note_1" in text
