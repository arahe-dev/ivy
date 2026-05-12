from __future__ import annotations

from pathlib import Path

from scripts.run_context_memory_hot_query_benchmark import summarize, write_report


def test_summarize_hot_query_rows() -> None:
    rows = [
        {
            "wall_ms": 10.0,
            "plugin_wall_ms": 9.0,
            "router_latency_ms": 2.0,
            "timings_ms": {"prefilter": 3.0, "corpus": 1.0, "router_init": 1.0, "route": 2.0, "render": 0.1, "packet_write": 0.5, "total": 9.0},
        },
        {
            "wall_ms": 20.0,
            "plugin_wall_ms": 19.0,
            "router_latency_ms": 4.0,
            "timings_ms": {"prefilter": 5.0, "corpus": 3.0, "router_init": 1.0, "route": 4.0, "render": 0.1, "packet_write": 0.5, "total": 19.0},
        },
    ]

    summary = summarize(rows)

    assert summary["avg_wall_ms"] == 15.0
    assert summary["avg_router_latency_ms"] == 3.0
    assert summary["avg_timings_ms"]["prefilter"] == 4.0


def test_write_hot_query_report(tmp_path: Path) -> None:
    out = tmp_path / "hot.md"
    write_report(
        {
            "created_at": "2026-05-11T00:00:00Z",
            "passes": [
                {
                    "pass": 1,
                    "summary": {"avg_wall_ms": 10.0, "avg_plugin_wall_ms": 9.0, "avg_router_latency_ms": 2.0, "avg_timings_ms": {"prefilter": 3.0, "corpus": 1.0}},
                    "rows": [{"query": "q", "wall_ms": 10.0, "router_latency_ms": 2.0, "packet_mode": "proof_lite", "selected_count": 1}],
                }
            ],
        },
        out,
    )

    text = out.read_text(encoding="utf-8")
    assert "Hot Query Benchmark" in text
    assert "proof_lite" in text
