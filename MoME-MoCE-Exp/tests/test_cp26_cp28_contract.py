from __future__ import annotations

from pathlib import Path

from scripts.generate_ambiguity_contradiction_dataset import write_dataset as write_cp22_dataset
from scripts.generate_freshness_authority_dataset import write_dataset as write_cp27_dataset
from scripts.generate_ivy_real_v3_dataset import write_dataset as write_v3_dataset
from scripts.ingest_external_corpus import DEFAULT_EXTENSIONS, ingest, signal_recall_cases, write_dataset as write_ingested_dataset
from scripts.mome_moce_harness import MoMEMoCERouter, benchmark, load_cases, load_corpus
from scripts.run_final_answer_ab import run_eval as run_final_answer_ab


ROOT = Path(__file__).resolve().parents[1]
IVY_REAL_V2 = ROOT / "out" / "context_stress_ivy_real_v2"


def write_synthetic_external_roots(tmp_path: Path) -> list[Path]:
    signal = tmp_path / "signal-v01-tauri"
    recall = tmp_path / "recall-board-excalidraw"
    (signal / "docs").mkdir(parents=True)
    (recall / "docs" / "wiki").mkdir(parents=True)
    (signal / "README.md").write_text(
        """# Signal

## iPhone Web Push
Signal reaches an iPhone through Safari Home Screen Web Push and Tailscale Serve without a public VPS.

## Event Log
Signal uses an append-only SQLite event log as the source of truth for durable coordination.
""",
        encoding="utf-8",
    )
    (signal / "docs" / "risk.md").write_text(
        """# Risk

## Daemon Boundary
The Signal daemon and worker boundary keeps shell execution in a separate worker with policy grants.
""",
        encoding="utf-8",
    )
    (recall / "docs" / "wiki" / "AI-Context-and-Exports.md").write_text(
        """# AI Context and Exports

## Why Text Graph Export Exists
Screenshots are expensive and ambiguous for AI models. Recall Board exports text graph and AI context so the board can be understood without screenshots.
""",
        encoding="utf-8",
    )
    (recall / "docs" / "wiki" / "User-Guide.md").write_text(
        """# User Guide

## Import and Export
Recall Board can import Recall Graph IR JSON and export board state in several forms for the AI to Excalidraw pipeline.
""",
        encoding="utf-8",
    )
    return [signal, recall]


def test_cp26_external_ingester_routes_smoke_cases(tmp_path: Path) -> None:
    roots = write_synthetic_external_roots(tmp_path)
    items = ingest(roots, max_chars=1800, max_files=None, extensions=DEFAULT_EXTENSIONS)
    cases = signal_recall_cases(items)
    assert len(cases) >= 6
    dataset = tmp_path / "context_stress_external_ingested_cp26"
    write_ingested_dataset(dataset, source_roots=roots, items=items, cases=cases, dataset_id="test_external_ingested_cp26")
    router = MoMEMoCERouter(load_corpus(dataset), candidate_backend="indexed", dataset_path=dataset)
    summary = benchmark(router, load_cases(dataset), validate_artifacts=False)
    assert summary["passed"] == summary["cases"]
    assert summary["evidence_metrics"]["forbidden_hits"] == 0


def test_cp27_freshness_authority_gate_routes_and_abstains(tmp_path: Path) -> None:
    dataset = tmp_path / "context_stress_freshness_authority_cp27"
    write_cp27_dataset(dataset)
    router = MoMEMoCERouter(load_corpus(dataset), candidate_backend="indexed", dataset_path=dataset)
    summary = benchmark(router, load_cases(dataset), validate_artifacts=False)
    assert summary["passed"] == summary["cases"]
    assert summary["evidence_metrics"]["required_recall"] == 1.0
    assert summary["evidence_metrics"]["required_only_precision"] == 1.0


def test_cp28_final_answer_ab_prefers_contradiction_aware(tmp_path: Path) -> None:
    v3_dataset = tmp_path / "context_stress_ivy_real_v3"
    cp22_dataset = tmp_path / "context_stress_ambiguity_cp22"
    write_v3_dataset(IVY_REAL_V2, v3_dataset)
    write_cp22_dataset(v3_dataset, cp22_dataset)
    payload = run_final_answer_ab(cp22_dataset, backend="indexed")
    assert payload["best_variant"] == "contradiction_aware"
    assert payload["summary"]["contradiction_aware"]["quality"] == 1.0
    assert payload["summary"]["contradiction_aware"]["conflict_quality"] == 1.0
    assert payload["summary"]["compact_default"]["quality"] < 1.0
