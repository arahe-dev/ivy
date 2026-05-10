from __future__ import annotations

import json
from pathlib import Path

from scripts.mome_moce_harness import MoMEMoCERouter, benchmark, load_cases, load_corpus
from scripts.run_baseline_comparison import run_baselines
from scripts.run_mutation_dropout_suite import DROPOUTS, run_router_cases


ROOT = Path(__file__).resolve().parents[1]


def smoke_items_and_cases() -> tuple[list, list[dict]]:
    dataset = ROOT / "out" / "context_stress_smoke"
    return load_corpus(dataset), load_cases(dataset)


def test_cp3_writes_valid_first_class_artifacts(tmp_path: Path) -> None:
    items, cases = smoke_items_and_cases()
    router = MoMEMoCERouter(items)
    summary = benchmark(router, cases[:8], write_artifacts=tmp_path)

    assert summary["artifact_errors"] == []
    assert summary["quality"] == 1.0
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert index["artifact_version"] == "acca.routing_artifacts.v0.1"
    assert index["cases"] == 8
    assert len(index["entries"]) == 8
    for entry in index["entries"]:
        assert (tmp_path / entry["route_proof"]).exists()
        assert (tmp_path / entry["frontier_packet"]).exists()
        assert len(entry["route_proof_sha256"]) == 64
        assert len(entry["frontier_packet_sha256"]) == 64


def test_cp4_compact_acca_preserves_full_precision() -> None:
    items, cases = smoke_items_and_cases()
    router = MoMEMoCERouter(items)
    summary = benchmark(router, cases)

    assert summary["passed"] == 62
    assert summary["artifact_errors"] == []
    assert summary["evidence_metrics"]["required_recall"] == 1.0
    assert summary["evidence_metrics"]["required_only_precision"] == 1.0
    assert summary["evidence_metrics"]["avg_selected"] == summary["evidence_metrics"]["avg_required"]
    assert all(result["compactness_pass"] for result in summary["results"])


def test_cp5_baselines_show_compact_acca_precision_gap() -> None:
    items, cases = smoke_items_and_cases()
    modes = run_baselines(items, cases, top_k=5)

    assert modes["compact_acca"]["quality"] == 1.0
    assert modes["compact_acca"]["required_only_precision"] == 1.0
    assert modes["naive_bm25_top_k"]["required_only_precision"] < 0.5
    assert modes["source_family_bm25_top_k"]["forbidden_hits"] > 0


def test_cp6_mutation_and_dropout_suite_has_signal() -> None:
    items, cases = smoke_items_and_cases()
    baseline_router = MoMEMoCERouter(items)
    baseline = run_router_cases(cases, baseline_router)
    mutation = run_router_cases(cases, baseline_router, mutate=True)

    assert baseline["quality"] == 1.0
    assert mutation["quality"] == 1.0

    dropout_scores = []
    for name, disabled in DROPOUTS.items():
        if name == "baseline_compact_acca":
            continue
        router = MoMEMoCERouter(items, disabled_experts=disabled)
        dropout_scores.append(run_router_cases(cases, router)["quality"])
    assert min(dropout_scores) < baseline["quality"]
