from __future__ import annotations

from pathlib import Path

from scripts.run_context_memory_daemon_smoke import daemon_checks, free_port, write_report


def test_free_port_returns_int() -> None:
    assert isinstance(free_port(), int)


def sample_result() -> dict:
    return {
        "created_at": "2026-05-11T00:00:00Z",
        "passed": True,
        "base_url": "http://127.0.0.1:12345",
        "wall_ms": 100.0,
        "health": {"ok": True},
        "ingest_summary": {"corpus_items": 10},
        "warm_summary": {
            "warmed_queries": 4,
            "index_items": 10,
            "query_index_cache_entries": 1,
            "item_feature_cache_entries": 10,
            "corpus_item_cache_entries": 8,
            "wall_ms": 20.0,
        },
        "status_process_caches": {
            "query_index_cache_entries": 1,
            "item_feature_cache_entries": 10,
            "corpus_item_cache_entries": 8,
        },
        "query_summary": {
            "selected_ids": ["note_1"],
            "packet_mode": "proof_lite",
            "wall_ms": 7.5,
            "latency_ms": 2.5,
            "timings_ms": {"prefilter": 1.0, "route": 2.5},
        },
    }


def test_daemon_checks_enforce_latency_budget() -> None:
    result = sample_result()
    status = daemon_checks(result, max_query_wall_ms=15.0, max_router_ms=5.0)
    assert status["passed"] is True

    result["query_summary"]["wall_ms"] = 20.0
    status = daemon_checks(result, max_query_wall_ms=15.0, max_router_ms=5.0)
    assert status["passed"] is False
    assert status["checks"]["query_wall_under_budget"] is False


def test_write_daemon_smoke_report(tmp_path: Path) -> None:
    out = tmp_path / "daemon.md"
    result = sample_result()
    result["status"] = daemon_checks(result, max_query_wall_ms=15.0, max_router_ms=5.0)
    write_report(result, out)

    text = out.read_text(encoding="utf-8")
    assert "Daemon Smoke Test" in text
    assert "note_1" in text
    assert "query_wall_under_budget" in text
