from __future__ import annotations

from pathlib import Path

from scripts.run_reranker_feature_eval import FEATURE_PROFILES, promotion_decision, write_feature_report


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


def test_promotion_decision_requires_latency_win() -> None:
    baseline = {"feature_profile": "baseline", "passed": 5, "total": 5, "avg_router_latency_ms": 2.5}
    winner = {"feature_profile": "code_penalty", "passed": 5, "total": 5, "avg_router_latency_ms": 2.1}
    assert promotion_decision(winner, baseline)[0] is True

    slower = {**winner, "avg_router_latency_ms": 2.9}
    promoted, reason = promotion_decision(slower, baseline)
    assert promoted is False
    assert "slower" in reason
