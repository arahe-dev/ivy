from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts.mome_moce_harness import MoMEMoCERouter, benchmark, load_cases, load_corpus
from scripts.run_rust_index_probe import evaluate_candidate_recall, run_rust_index
from scripts.validate_context_stress_dataset import validate_dataset


ROOT = Path(__file__).resolve().parents[1]


def test_cp7_ivy_real_dataset_validates_and_routes() -> None:
    dataset = ROOT / "out" / "context_stress_ivy_real"
    errors, warnings, summary = validate_dataset(dataset)

    assert errors == []
    assert summary["cases"] == 30
    assert summary["items"] >= 30
    assert set(summary["categories"]) == {
        "adversarial_decoy",
        "benchmark",
        "debug",
        "exact_command",
        "general",
        "local_codebase",
        "safety",
        "stale_conflict",
        "unanswerable",
        "workflow",
    }
    assert all("dangling" not in warning for warning in warnings)

    items = load_corpus(dataset)
    cases = load_cases(dataset)
    for backend in ("scan", "indexed"):
        result = benchmark(MoMEMoCERouter(items, candidate_backend=backend), cases)
        assert result["candidate_backend"] == backend
        assert result["quality"] == 1.0
        assert result["artifact_errors"] == []
        assert result["evidence_metrics"]["required_only_precision"] == 1.0


def test_cp8_indexed_backend_preserves_stress_quality() -> None:
    dataset = ROOT / "out" / "context_stress_stress"
    items = load_corpus(dataset)
    cases = load_cases(dataset)

    result = benchmark(MoMEMoCERouter(items, candidate_backend="indexed"), cases)

    assert result["candidate_backend"] == "indexed"
    assert result["passed"] == 62
    assert result["quality"] == 1.0
    assert result["artifact_errors"] == []
    assert result["evidence_metrics"]["required_recall"] == 1.0
    assert result["evidence_metrics"]["required_only_precision"] == 1.0


def test_cp9_rust_candidate_index_recall_on_ivy_real() -> None:
    if shutil.which("cargo") is None:
        pytest.skip("cargo is not installed")
    dataset = ROOT / "out" / "context_stress_ivy_real"
    cases = load_cases(dataset)

    rust_payload, _elapsed_ms = run_rust_index(dataset, top_k=32, release=False)
    summary = evaluate_candidate_recall(cases, rust_payload)

    assert summary["failed_cases"] == 0
    assert summary["required_recall_at_k"] == 1.0


def test_cp9_rust_backend_preserves_ivy_real_route_quality() -> None:
    if shutil.which("cargo") is None:
        pytest.skip("cargo is not installed")
    dataset = ROOT / "out" / "context_stress_ivy_real"
    items = load_corpus(dataset)
    cases = load_cases(dataset)

    result = benchmark(MoMEMoCERouter(items, candidate_backend="rust", dataset_path=dataset), cases)

    assert result["candidate_backend"] == "rust"
    assert result["quality"] == 1.0
    assert result["artifact_errors"] == []
    assert result["evidence_metrics"]["required_recall"] == 1.0
    assert result["evidence_metrics"]["required_only_precision"] == 1.0


def test_taint_exposure_survives_proof_and_packet() -> None:
    dataset = ROOT / "out" / "context_stress_ivy_real"
    items = load_corpus(dataset)
    cases = {case["id"]: case for case in load_cases(dataset)}
    router = MoMEMoCERouter(items, candidate_backend="indexed")

    result = router.route(cases["safety_001"]["query"])

    assert result.route_proof["exposure_summary"]["forbidden_selected"] == 0
    assert result.frontier_packet["exposure_summary"] == result.route_proof["exposure_summary"]
    for evidence in result.frontier_packet["evidence"]:
        assert "taint_labels" in evidence
        assert "exposure_policy" in evidence
        assert evidence["exposure_policy"] != "forbidden"


def test_ivy_real_v2_dataset_preserves_indexed_and_rust_quality() -> None:
    if shutil.which("cargo") is None:
        pytest.skip("cargo is not installed")
    dataset = ROOT / "out" / "context_stress_ivy_real_v2"
    errors, warnings, summary = validate_dataset(dataset)
    assert errors == []
    assert summary["cases"] >= 100
    assert summary["items"] >= 40
    assert all("dangling" not in warning for warning in warnings)

    items = load_corpus(dataset)
    cases = load_cases(dataset)
    for backend in ("indexed", "rust"):
        result = benchmark(MoMEMoCERouter(items, candidate_backend=backend, dataset_path=dataset), cases)
        assert result["quality"] == 1.0
        assert result["artifact_errors"] == []
        assert result["evidence_metrics"]["required_recall"] == 1.0
        assert result["evidence_metrics"]["required_only_precision"] == 1.0
