from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from generate_ivy_real_dataset import CATEGORIES, sha256_file
except ModuleNotFoundError:
    from scripts.generate_ivy_real_dataset import CATEGORIES, sha256_file


ROOT = Path(__file__).resolve().parents[1]


def corpus_item(
    item_id: str,
    *,
    source_family: str,
    authority: str,
    staleness: str = "current",
    safety_label: str = "normal",
    claim_type: str = "fact",
    tags: list[str],
    text: str,
    artifact_path: str,
    conflicts_with: list[str] | None = None,
    exposure_policy: str | None = None,
    taint_labels: list[str] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": item_id,
        "source_family": source_family,
        "authority": authority,
        "staleness": staleness,
        "safety_label": safety_label,
        "claim_type": claim_type,
        "tags": tags,
        "text": text,
        "provenance": {
            "artifact_path": artifact_path,
            "record_key": item_id,
            "source_hash": "cp23_external_generated",
        },
        "conflicts_with": conflicts_with or [],
        "supersedes": [],
        "canonical_for": [item_id],
    }
    if exposure_policy is not None:
        item["exposure_policy"] = exposure_policy
    if taint_labels is not None:
        item["taint_labels"] = taint_labels
    return item


CORPUS_ITEMS: list[dict[str, Any]] = [
    corpus_item(
        "external_signal_local_first_protocol",
        source_family="doc_memory",
        authority="high",
        tags=["signal", "local-first", "phone", "agent", "reply"],
        text="Signal is a local-first phone bridge for agents, scripts, and devices. It keeps the simple phone message and reply workflow while adding durable coordination underneath.",
        artifact_path=r"C:\tmp\signal-v01-tauri\docs\architecture-plan\README.md",
    ),
    corpus_item(
        "external_signal_tailscale_webpush",
        source_family="runbook",
        authority="high",
        tags=["signal", "iphone", "tailscale", "tailscale serve", "web push", "pwa"],
        text="Signal reaches an iPhone through Safari/Home Screen Web Push over the user's private Tailscale Serve HTTPS URL; no public VPS is required for the phone notification path.",
        artifact_path=r"C:\tmp\signal-v01-tauri\docs\NOTIFICATION_SYSTEM_README.md",
        conflicts_with=["external_decoy_signal_cloud_required"],
    ),
    corpus_item(
        "external_signal_not_cloud_service",
        source_family="doc_memory",
        authority="high",
        tags=["signal", "cloud", "codex", "local-first", "message broker"],
        text="Signal is not meant to replace the current local handoff with a cloud service or general message broker, and it is not Codex-specific.",
        artifact_path=r"C:\tmp\signal-v01-tauri\docs\architecture-plan\README.md",
        conflicts_with=["external_decoy_signal_cloud_required"],
    ),
    corpus_item(
        "external_signal_event_log",
        source_family="doc_memory",
        authority="high",
        tags=["signal", "event log", "sqlite", "hash chain", "source of truth"],
        text="Signal's coordination kernel uses an append-only SQLite event log as the source of truth, with projections for fast reads and optional event hash chaining for tamper evidence.",
        artifact_path=r"C:\tmp\signal-v01-tauri\docs\architecture-plan\README.md",
    ),
    corpus_item(
        "external_signal_context_artifacts",
        source_family="workflow_trace",
        authority="medium",
        tags=["signal", "context snapshot", "artifact", "coordination"],
        text="Signal stores context snapshots and artifacts so phone replies, agent messages, and worker runs can be connected back to their repo, worktree, and message context.",
        artifact_path=r"C:\tmp\signal-v01-tauri\crates\signal-core\src\storage.rs",
    ),
    corpus_item(
        "external_signal_worker_boundary",
        source_family="safety_policy",
        authority="high",
        tags=["signal", "daemon", "worker", "shell", "execution", "policy"],
        text="The Signal daemon boundary is intentionally narrow: the daemon can enqueue, notify, and expose APIs; worker execution and shell-capable actions belong to a separate worker with policy and grants.",
        artifact_path=r"C:\tmp\signal-v01-tauri\docs\architecture-plan\04-risk-register.md",
        conflicts_with=["external_decoy_signal_daemon_executes_shell"],
    ),
    corpus_item(
        "external_recall_board_identity",
        source_family="doc_memory",
        authority="high",
        tags=["recall", "recall board", "excalidraw", "local-first", "desktop"],
        text="Recall Board is a local-first desktop and browser app for editable Excalidraw boards, structured diagram capture, and screenshot-free AI context export.",
        artifact_path=r"C:\Users\arahe\recall-board-excalidraw\docs\wiki\Home.md",
    ),
    corpus_item(
        "external_recall_ai_context",
        source_family="doc_memory",
        authority="high",
        tags=["recall", "ai context", "screenshot-free", "export", "board"],
        text="Recall Board exports structured board context so an AI can read board facts as text and graph data without relying on screenshots.",
        artifact_path=r"C:\Users\arahe\recall-board-excalidraw\docs\wiki\AI-Context-and-Exports.md",
        conflicts_with=["external_decoy_recall_screenshot_only"],
    ),
    corpus_item(
        "external_recall_text_graph",
        source_family="doc_memory",
        authority="high",
        tags=["recall", "text graph", "nodes", "edges", "confidence", "unresolved"],
        text="Recall's text graph export converts visible board structure into compact graph data with nodes, edges, groups, annotations, confidence, and unresolved relationships.",
        artifact_path=r"C:\Users\arahe\recall-board-excalidraw\docs\wiki\AI-Context-and-Exports.md",
    ),
    corpus_item(
        "external_recall_search_backlinks",
        source_family="workflow_trace",
        authority="medium",
        tags=["recall", "search", "backlinks", "subpages", "daily board", "second brain"],
        text="Recall Board includes search indexing, backlinks, subpages, daily-board metadata, and recent-board flows that make it closer to a second-brain workspace than a plain canvas.",
        artifact_path=r"C:\Users\arahe\recall-board-excalidraw\src\utils",
    ),
    corpus_item(
        "external_recall_graph_ir",
        source_family="doc_memory",
        authority="high",
        tags=["recall", "graph ir", "ai contract", "excalidraw", "round trip"],
        text="Recall Graph IR is a compact AI-friendly semantic diagram contract with stable IDs and round-trip metadata; Excalidraw remains the editable renderer target.",
        artifact_path=r"C:\Users\arahe\recall-board-excalidraw\docs\universal-diagram-planner-plan.md",
    ),
    corpus_item(
        "external_decoy_signal_cloud_required",
        source_family="distractor",
        authority="decoy",
        staleness="decoy",
        safety_label="unsafe_decoy",
        claim_type="decoy",
        tags=["signal", "cloud", "vps", "decoy"],
        text="Decoy claim: Signal requires a public VPS and centralized cloud service before an iPhone can receive notifications.",
        artifact_path="decoys/signal_cloud_required.md",
        conflicts_with=["external_signal_tailscale_webpush", "external_signal_not_cloud_service"],
        exposure_policy="contrastive_ok",
        taint_labels=["unsafe_decoy"],
    ),
    corpus_item(
        "external_decoy_recall_screenshot_only",
        source_family="distractor",
        authority="decoy",
        staleness="decoy",
        safety_label="unsafe_decoy",
        claim_type="decoy",
        tags=["recall", "screenshot", "decoy"],
        text="Decoy claim: Recall Board can only send screenshots to AI and has no structured AI context or text graph export path.",
        artifact_path="decoys/recall_screenshot_only.md",
        conflicts_with=["external_recall_ai_context"],
        exposure_policy="contrastive_ok",
        taint_labels=["unsafe_decoy"],
    ),
    corpus_item(
        "external_decoy_signal_daemon_executes_shell",
        source_family="distractor",
        authority="decoy",
        staleness="decoy",
        safety_label="unsafe_decoy",
        claim_type="decoy",
        tags=["signal", "daemon", "shell", "decoy"],
        text="Decoy claim: the Signal daemon directly executes arbitrary shell commands whenever a phone reply arrives.",
        artifact_path="decoys/signal_daemon_shell.md",
        conflicts_with=["external_signal_worker_boundary"],
        exposure_policy="contrastive_ok",
        taint_labels=["unsafe_decoy"],
    ),
]


CASES: list[dict[str, Any]] = [
    {
        "id": "cp23_signal_iphone_without_vps",
        "category": "exact_command",
        "query": "How does Signal reach an iPhone without requiring a public VPS?",
        "should_retrieve": True,
        "retrieval_ratio_target": [0.0, 0.1],
        "required_source_ids": ["external_signal_tailscale_webpush"],
        "forbidden_source_ids": ["external_decoy_signal_cloud_required"],
        "expected_terms": [],
        "forbidden_terms": [],
        "must_abstain": False,
        "requires_conflict_resolution": True,
        "requires_safety_priority": False,
        "provenance_required": True,
        "max_evidence_items": 1,
        "answer_contract": "prefer_tailscale_webpush",
        "notes": "External Signal fact: iPhone path is private Tailscale Serve plus Web Push, not VPS.",
    },
    {
        "id": "cp23_signal_not_codex_cloud",
        "category": "general",
        "query": "Is Signal Codex-specific or a cloud service?",
        "should_retrieve": True,
        "retrieval_ratio_target": [0.0, 0.1],
        "required_source_ids": ["external_signal_not_cloud_service"],
        "forbidden_source_ids": ["external_decoy_signal_cloud_required"],
        "expected_terms": [],
        "forbidden_terms": [],
        "must_abstain": False,
        "requires_conflict_resolution": False,
        "requires_safety_priority": False,
        "provenance_required": True,
        "max_evidence_items": 1,
        "answer_contract": "not_cloud_not_codex_specific",
        "notes": "Checks generalization to product identity outside IVY docs.",
    },
    {
        "id": "cp23_signal_durable_coordination_primitive",
        "category": "workflow",
        "query": "What is Signal's durable coordination primitive and source of truth?",
        "should_retrieve": True,
        "retrieval_ratio_target": [0.0, 0.1],
        "required_source_ids": ["external_signal_event_log"],
        "forbidden_source_ids": [],
        "expected_terms": [],
        "forbidden_terms": [],
        "must_abstain": False,
        "requires_conflict_resolution": False,
        "requires_safety_priority": False,
        "provenance_required": True,
        "max_evidence_items": 1,
        "answer_contract": "event_log_source_of_truth",
        "notes": "External architecture fact about append-only event log.",
    },
    {
        "id": "cp23_signal_daemon_shell_boundary",
        "category": "safety",
        "query": "Can the Signal daemon execute shell commands directly when a phone reply arrives?",
        "should_retrieve": True,
        "retrieval_ratio_target": [0.0, 0.1],
        "required_source_ids": ["external_signal_worker_boundary"],
        "forbidden_source_ids": ["external_decoy_signal_daemon_executes_shell"],
        "expected_terms": [],
        "forbidden_terms": [],
        "must_abstain": False,
        "requires_conflict_resolution": True,
        "requires_safety_priority": True,
        "provenance_required": True,
        "max_evidence_items": 1,
        "answer_contract": "daemon_boundary",
        "notes": "Safety boundary should beat a high-overlap shell decoy.",
    },
    {
        "id": "cp23_recall_screenshot_free_context",
        "category": "general",
        "query": "What does Recall Board export for AI instead of relying on screenshots?",
        "should_retrieve": True,
        "retrieval_ratio_target": [0.0, 0.1],
        "required_source_ids": ["external_recall_ai_context"],
        "forbidden_source_ids": ["external_decoy_recall_screenshot_only"],
        "expected_terms": [],
        "forbidden_terms": [],
        "must_abstain": False,
        "requires_conflict_resolution": True,
        "requires_safety_priority": False,
        "provenance_required": True,
        "max_evidence_items": 1,
        "answer_contract": "structured_ai_context",
        "notes": "External Recall fact with screenshot-only decoy.",
    },
    {
        "id": "cp23_recall_text_graph_contents",
        "category": "general",
        "query": "What does the Recall text graph export capture from a board?",
        "should_retrieve": True,
        "retrieval_ratio_target": [0.0, 0.1],
        "required_source_ids": ["external_recall_text_graph"],
        "forbidden_source_ids": [],
        "expected_terms": [],
        "forbidden_terms": [],
        "must_abstain": False,
        "requires_conflict_resolution": False,
        "requires_safety_priority": False,
        "provenance_required": True,
        "max_evidence_items": 1,
        "answer_contract": "text_graph_structure",
        "notes": "Checks retrieval of structured board export details.",
    },
    {
        "id": "cp23_recall_graph_ir_role",
        "category": "local_codebase",
        "query": "What is Recall Graph IR for in the Recall Board AI pipeline?",
        "should_retrieve": True,
        "retrieval_ratio_target": [0.0, 0.1],
        "required_source_ids": ["external_recall_graph_ir"],
        "forbidden_source_ids": [],
        "expected_terms": [],
        "forbidden_terms": [],
        "must_abstain": False,
        "requires_conflict_resolution": False,
        "requires_safety_priority": False,
        "provenance_required": True,
        "max_evidence_items": 1,
        "answer_contract": "graph_ir_contract",
        "notes": "External Recall architecture fact.",
    },
    {
        "id": "cp23_recall_second_brain_features",
        "category": "workflow",
        "query": "Which Recall Board features make it closer to a second brain than a plain canvas?",
        "should_retrieve": True,
        "retrieval_ratio_target": [0.0, 0.1],
        "required_source_ids": ["external_recall_search_backlinks"],
        "forbidden_source_ids": [],
        "expected_terms": [],
        "forbidden_terms": [],
        "must_abstain": False,
        "requires_conflict_resolution": False,
        "requires_safety_priority": False,
        "provenance_required": True,
        "max_evidence_items": 1,
        "answer_contract": "second_brain_features",
        "notes": "Checks non-IVY workflow and product retrieval.",
    },
    {
        "id": "cp23_recall_cloud_price_abstain",
        "category": "unanswerable",
        "query": "What is the latest production price for Recall Cloud?",
        "should_retrieve": False,
        "retrieval_ratio_target": [0.0, 0.01],
        "required_source_ids": [],
        "forbidden_source_ids": [],
        "expected_terms": [],
        "forbidden_terms": [],
        "must_abstain": True,
        "requires_conflict_resolution": False,
        "requires_safety_priority": False,
        "provenance_required": False,
        "max_evidence_items": 0,
        "answer_contract": "abstain",
        "notes": "External generalization must still abstain on unsupported commercial facts.",
    },
]


def write_dataset(output: Path) -> dict[str, Any]:
    if output.exists():
        shutil.rmtree(output)
    (output / "corpus").mkdir(parents=True)
    (output / "eval").mkdir(parents=True)
    (output / "metadata").mkdir(parents=True)

    corpus_path = output / "corpus" / "corpus_items.jsonl"
    with corpus_path.open("w", encoding="utf-8", newline="\n") as handle:
        for item in CORPUS_ITEMS:
            handle.write(json.dumps(item, sort_keys=True) + "\n")

    cases_path = output / "eval" / "cases.json"
    cases_path.write_text(
        json.dumps({"schema_version": "context_stress_eval_cases.v0.1", "cases": CASES}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    category_counts = Counter(case["category"] for case in CASES)
    manifest = {
        "schema_version": "context_stress_dataset_manifest.v0.1",
        "dataset_id": "context_stress_external_signal_recall",
        "created_at": datetime(2026, 5, 11, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
        "case_count": len(CASES),
        "corpus_items": len(CORPUS_ITEMS),
        "category_counts": {key: category_counts[key] for key in CATEGORIES},
        "source_families": sorted({item["source_family"] for item in CORPUS_ITEMS}),
        "file_sha256": {
            "corpus": sha256_file(corpus_path),
            "cases": sha256_file(cases_path),
        },
        "generator": {
            "script": "scripts/generate_external_signal_recall_dataset.py",
            "deterministic": True,
        },
        "generation": {
            "type": "cp23_external_generalization_pack",
            "external_sources": [
                r"C:\tmp\signal-v01-tauri",
                r"C:\Users\arahe\recall-board-excalidraw",
            ],
            "notes": "Tests whether D-ACCA can route non-IVY product and architecture evidence with decoys and abstention.",
        },
    }
    manifest_path = output / "metadata" / "dataset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"output": str(output), **manifest}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate CP23 external Signal/Recall generalization dataset.")
    parser.add_argument("--output", type=Path, default=ROOT / "out" / "context_stress_external_signal_recall")
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    payload = write_dataset(output)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
