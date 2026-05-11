from __future__ import annotations

from pathlib import Path

from scripts.generate_ambiguity_contradiction_dataset import write_dataset as write_cp22_dataset
from scripts.generate_external_signal_recall_dataset import write_dataset as write_cp23_dataset
from scripts.generate_ivy_real_v3_dataset import write_dataset as write_v3_dataset
from scripts.mome_moce_harness import MoMEMoCERouter, benchmark, load_cases, load_corpus
from scripts.run_agent_outcome_eval import run_eval as run_agent_outcome_eval
from scripts.run_external_generalization_gate import run_gate as run_external_generalization_gate
from scripts.run_packet_format_ab import run_eval as run_packet_format_ab


ROOT = Path(__file__).resolve().parents[1]
IVY_REAL_V2 = ROOT / "out" / "context_stress_ivy_real_v2"


def test_cp21_agent_outcome_eval_prefers_d_acca(tmp_path: Path) -> None:
    dataset = tmp_path / "context_stress_ivy_real_v3"
    write_v3_dataset(IVY_REAL_V2, dataset)
    payload = run_agent_outcome_eval(dataset, ROOT / "eval" / "agent_outcome_cases.json", backend="indexed")
    summary = payload["summary"]
    assert summary["d_acca"]["quality"] == 1.0
    assert summary["d_acca"]["quality"] > summary["no_context"]["quality"]
    assert summary["d_acca"]["quality"] > summary["naive_bm25"]["quality"]
    assert summary["d_acca"]["forbidden_context_failures"] == 0


def test_cp22_ambiguity_contradiction_pack_routes_cleanly(tmp_path: Path) -> None:
    v3_dataset = tmp_path / "context_stress_ivy_real_v3"
    cp22_dataset = tmp_path / "context_stress_ambiguity_cp22"
    write_v3_dataset(IVY_REAL_V2, v3_dataset)
    write_cp22_dataset(v3_dataset, cp22_dataset)
    router = MoMEMoCERouter(load_corpus(cp22_dataset), candidate_backend="indexed", dataset_path=cp22_dataset)
    summary = benchmark(router, load_cases(cp22_dataset), validate_artifacts=False)
    assert summary["passed"] == summary["cases"]
    assert summary["evidence_metrics"]["forbidden_hits"] == 0
    assert summary["evidence_metrics"]["required_only_precision"] == 1.0


def test_cp24_contradiction_aware_packet_wins(tmp_path: Path) -> None:
    v3_dataset = tmp_path / "context_stress_ivy_real_v3"
    cp22_dataset = tmp_path / "context_stress_ambiguity_cp22"
    write_v3_dataset(IVY_REAL_V2, v3_dataset)
    write_cp22_dataset(v3_dataset, cp22_dataset)
    payload = run_packet_format_ab(cp22_dataset, backend="indexed")
    assert payload["best_variant"] == "contradiction_aware"
    best = payload["summary"]["contradiction_aware"]
    assert best["quality"] == 1.0
    assert best["conflict_pass_rate"] == 1.0


def test_cp23_external_signal_recall_generalizes(tmp_path: Path) -> None:
    dataset = tmp_path / "context_stress_external_signal_recall"
    write_cp23_dataset(dataset)
    router = MoMEMoCERouter(load_corpus(dataset), candidate_backend="indexed", dataset_path=dataset)
    summary = benchmark(router, load_cases(dataset), validate_artifacts=False)
    assert summary["passed"] == summary["cases"]
    assert summary["evidence_metrics"]["required_recall"] == 1.0
    assert summary["evidence_metrics"]["required_only_precision"] == 1.0
    assert summary["evidence_metrics"]["forbidden_hits"] == 0


def test_cp74_external_generalization_gate(tmp_path: Path) -> None:
    dataset = tmp_path / "context_stress_external_signal_recall"
    gate = run_external_generalization_gate(dataset, max_mean_latency_ms=2.0, max_p95_latency_ms=5.0)
    summary = gate["summary"]
    ablation = gate["no_exact_anchor_ablation"]
    assert gate["status"]["passed"]
    assert summary["passed"] == summary["cases"] == 9
    assert summary["evidence_metrics"]["required_recall"] == 1.0
    assert summary["evidence_metrics"]["required_only_precision"] == 1.0
    assert summary["evidence_metrics"]["forbidden_hits"] == 0
    assert ablation["passed"] == ablation["cases"] == 9
    assert ablation["evidence_metrics"]["required_only_precision"] == 1.0
    assert gate["status"]["checks"]["no_exact_anchor_all_cases_pass"]
