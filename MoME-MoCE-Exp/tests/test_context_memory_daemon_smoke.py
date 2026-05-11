from __future__ import annotations

from pathlib import Path

from scripts.run_context_memory_daemon_smoke import free_port, write_report


def test_free_port_returns_int() -> None:
    assert isinstance(free_port(), int)


def test_write_daemon_smoke_report(tmp_path: Path) -> None:
    out = tmp_path / "daemon.md"
    write_report(
        {
            "created_at": "2026-05-11T00:00:00Z",
            "passed": True,
            "base_url": "http://127.0.0.1:12345",
            "wall_ms": 100.0,
            "warm_summary": {
                "warmed_queries": 4,
                "index_items": 10,
                "query_index_cache_entries": 1,
                "item_feature_cache_entries": 10,
                "corpus_item_cache_entries": 8,
                "wall_ms": 20.0,
            },
            "query_summary": {
                "selected_ids": ["note_1"],
                "packet_mode": "proof_lite",
                "wall_ms": 7.5,
                "latency_ms": 2.5,
                "timings_ms": {"prefilter": 1.0, "route": 2.5},
            },
        },
        out,
    )

    text = out.read_text(encoding="utf-8")
    assert "Daemon Smoke Test" in text
    assert "note_1" in text
