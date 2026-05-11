from __future__ import annotations

from pathlib import Path

from scripts.run_context_memory_regression_gate import gate_status, write_gate_report


def sample_gate() -> dict:
    return {
        "created_at": "2026-05-11T00:00:00Z",
        "mined_policy": {
            "winner": {"max_prefilter_items": 32, "passed": 5, "total": 5, "avg_wall_ms": 10.0, "avg_router_latency_ms": 2.0},
            "results": [{"max_prefilter_items": 32, "passed": 5, "total": 5, "avg_wall_ms": 10.0, "avg_router_latency_ms": 2.0}],
        },
        "feature_eval": {
            "winner": {"feature_profile": "code_penalty", "passed": 5, "total": 5, "avg_wall_ms": 11.0, "avg_router_latency_ms": 2.1},
            "promotion": {"promoted": False},
            "results": [{"feature_profile": "code_penalty", "passed": 5, "total": 5, "avg_wall_ms": 11.0, "avg_router_latency_ms": 2.1}],
        },
        "plugin_benchmark": {"summary": {"passed_expectations": 6, "query_count": 6, "avg_query_wall_ms": 28.0, "avg_router_latency_ms": 2.2}},
    }


def add_external_gate(gate: dict, *, passed: bool = True) -> dict:
    gate["external_generalization"] = {
        "status": {"passed": passed, "p95_latency_ms": 0.8},
        "summary": {
            "cases": 9,
            "passed": 9 if passed else 8,
            "evidence_metrics": {
                "required_recall": 1.0,
                "required_only_precision": 1.0,
                "forbidden_hits": 0,
            },
            "latency_ms": {"mean": 0.4},
            "results": [{"case_id": "cp23_signal_iphone_without_vps", "passed": passed, "selected_ids": ["external_signal_tailscale_webpush"], "latency_ms": 0.7}],
        },
    }
    return gate


def test_gate_status_requires_all_checks() -> None:
    gate = sample_gate()
    assert gate_status(gate, max_router_ms=5.0, max_plugin_router_ms=15.0, max_wall_ms=35.0, max_plugin_wall_ms=25.0)["passed"] is False
    gate["plugin_benchmark"]["summary"]["avg_query_wall_ms"] = 18.0
    assert gate_status(gate, max_router_ms=5.0, max_plugin_router_ms=15.0, max_wall_ms=35.0, max_plugin_wall_ms=25.0)["passed"] is True

    gate["plugin_benchmark"]["summary"]["passed_expectations"] = 5
    status = gate_status(gate, max_router_ms=5.0, max_plugin_router_ms=15.0, max_wall_ms=35.0, max_plugin_wall_ms=25.0)
    assert status["passed"] is False
    assert status["checks"]["plugin_benchmark_all_pass"] is False


def test_gate_status_includes_external_generalization_when_present() -> None:
    gate = add_external_gate(sample_gate())
    gate["plugin_benchmark"]["summary"]["avg_query_wall_ms"] = 18.0

    status = gate_status(gate, max_router_ms=5.0, max_plugin_router_ms=15.0, max_wall_ms=35.0, max_plugin_wall_ms=25.0)

    assert status["passed"] is True
    assert status["checks"]["external_generalization_all_pass"] is True

    gate["external_generalization"]["summary"]["evidence_metrics"]["forbidden_hits"] = 1
    status = gate_status(gate, max_router_ms=5.0, max_plugin_router_ms=15.0, max_wall_ms=35.0, max_plugin_wall_ms=25.0)
    assert status["passed"] is False
    assert status["checks"]["external_generalization_no_forbidden_hits"] is False


def test_gate_status_tracks_wall_time_budget() -> None:
    gate = sample_gate()
    gate["plugin_benchmark"]["summary"]["avg_query_wall_ms"] = 55.0

    status = gate_status(gate, max_router_ms=5.0, max_plugin_router_ms=15.0, max_wall_ms=35.0, max_plugin_wall_ms=25.0)

    assert status["passed"] is False
    assert status["checks"]["plugin_wall_under_budget"] is False


def test_write_gate_report_contains_core_sections(tmp_path: Path) -> None:
    gate = add_external_gate(sample_gate())
    gate["status"] = gate_status(gate, max_router_ms=5.0, max_plugin_router_ms=15.0, max_wall_ms=35.0, max_plugin_wall_ms=25.0)
    out = tmp_path / "gate.md"
    write_gate_report(gate, out)

    text = out.read_text(encoding="utf-8")
    assert "Regression Gate" in text
    assert "code_penalty" in text
    assert "Mined Policy Candidates" in text
    assert "External Generalization" in text
    assert "external_signal_tailscale_webpush" in text
