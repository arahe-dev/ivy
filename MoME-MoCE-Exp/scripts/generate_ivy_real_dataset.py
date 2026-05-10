from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FAMILIES = [
    "doc_memory",
    "runbook",
    "benchmark_artifact",
    "safety_policy",
    "workflow_trace",
    "debug_failure",
    "source_code",
    "distractor",
]
AUTHORITIES = ["high", "medium", "low", "decoy"]
STALENESS = ["current", "stale", "unknown", "decoy"]
CATEGORIES = [
    "general",
    "local_codebase",
    "exact_command",
    "benchmark",
    "safety",
    "workflow",
    "debug",
    "unanswerable",
    "stale_conflict",
    "adversarial_decoy",
]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rough_tokens(text: str) -> int:
    return max(1, len(text.split()))


def item(
    item_id: str,
    source_family: str,
    authority: str,
    staleness: str,
    tags: list[str],
    text: str,
    artifact_path: str,
    *,
    safety_label: str = "normal",
    claim_type: str = "fact",
    conflicts_with: list[str] | None = None,
    supersedes: list[str] | None = None,
    canonical_for: list[str] | None = None,
    created_at: str = "2026-05-10",
) -> dict[str, Any]:
    return {
        "id": item_id,
        "source_family": source_family,
        "authority": authority,
        "created_at": created_at,
        "supersedes": supersedes or [],
        "tags": tags,
        "text": text,
        "provenance": {
            "artifact_path": artifact_path,
            "source_hash": sha256_text(text)[:16],
            "record_key": item_id,
        },
        "staleness": staleness,
        "conflicts_with": conflicts_with or [],
        "safety_label": safety_label,
        "claim_type": claim_type,
        "canonical_for": canonical_for or [],
    }


def case(
    case_id: str,
    category: str,
    query: str,
    required: list[str],
    *,
    forbidden: list[str] | None = None,
    should_retrieve: bool = True,
    must_abstain: bool = False,
    answer_contract: str = "answer",
    notes: str = "",
) -> dict[str, Any]:
    return {
        "id": case_id,
        "category": category,
        "query": query,
        "should_retrieve": should_retrieve,
        "retrieval_ratio_target": [0.0, 0.05],
        "required_source_ids": required,
        "forbidden_source_ids": forbidden or [],
        "expected_terms": [],
        "forbidden_terms": [],
        "must_abstain": must_abstain,
        "requires_conflict_resolution": category in {"stale_conflict", "adversarial_decoy"},
        "requires_safety_priority": category == "safety",
        "provenance_required": bool(required),
        "max_evidence_items": len(required),
        "answer_contract": answer_contract,
        "notes": notes,
    }


def build_items() -> list[dict[str, Any]]:
    rows = [
        item(
            "doc_ivy_lab_identity",
            "doc_memory",
            "high",
            "current",
            ["ivy", "identity", "llama.cpp"],
            "IVY is a local LLM systems lab, not a web app and not a library. It runs experiments around stock llama.cpp to make open LLMs usable on constrained hardware.",
            "root/AGENTS.md",
            canonical_for=["ivy_identity"],
        ),
        item(
            "doc_acca_framing",
            "doc_memory",
            "medium",
            "unknown",
            ["acca", "moce", "mome"],
            "ACCA is framed as an auditable authority-constrained context compiler for agent memory. MoCE routes and gates context; MoME proposes memory evidence.",
            "docs/NEXT_CHAT_HANDOFF.md",
            canonical_for=["acca_framing"],
        ),
        item(
            "doc_hot_session_cache_rule",
            "doc_memory",
            "high",
            "current",
            ["hot-session", "cache_prompt", "static prefix", "id_slot"],
            "Hot-session cache reuse keeps llama-server running with fixed id_slot and cache_prompt=true. The static prefix must stay byte-identical; timestamps or volatile data before the static prefix destroy cache shape.",
            "root/AGENTS.md",
            conflicts_with=["decoy_hot_session_timestamp_ok", "stale_hot_cache_threshold_500ms"],
            canonical_for=["hot_session_cache_reuse"],
        ),
        item(
            "doc_mome_opt_in_rule",
            "doc_memory",
            "high",
            "current",
            ["mome", "memory packet", "opt-in"],
            "Memory injection with MoME is opt-in only. Normal runs do not receive memory packets unless a policy explicitly enables them.",
            "root/AGENTS.md",
            conflicts_with=["decoy_mome_always_injected"],
            canonical_for=["mome_opt_in"],
        ),
        item(
            "run_hot_session_q4km_agent_command",
            "runbook",
            "high",
            "current",
            ["command", "hot-session", "q4km"],
            "& C:/ivy/ivy/scripts/run_hot_session.ps1 -ManifestPath C:/ivy/ivy/manifests/q4km_hot_agent.yaml -DynamicTask \"your task here\" -SlotId 0 -OutputRunDirectory C:/ivy/ivy/runs/hot_session/example",
            "root/AGENTS.md",
            claim_type="command",
            canonical_for=["hot_session_command"],
        ),
        item(
            "run_phase1_ui_command",
            "runbook",
            "high",
            "current",
            ["command", "phase 1", "ui"],
            "Run the Phase 1 sandbox agent UI with: powershell -ExecutionPolicy Bypass -File C:/ivy/scripts/run_phase1_ui.ps1. It opens at http://127.0.0.1:8787.",
            "root/AGENTS.md",
            claim_type="command",
            canonical_for=["phase1_ui_command"],
        ),
        item(
            "run_tool_benchmark_25_command",
            "runbook",
            "high",
            "current",
            ["command", "tool benchmark", "25 cases"],
            "& C:/ivy/ivy/scripts/run_tool_benchmark.ps1 -ManifestPath C:/ivy/ivy/manifests/q4km_tool_benchmark_25.yaml runs the 25-case tool benchmark.",
            "root/AGENTS.md",
            claim_type="command",
            canonical_for=["tool_benchmark_command"],
        ),
        item(
            "run_mome_preview_command",
            "runbook",
            "high",
            "current",
            ["command", "mome", "preview"],
            "python -m ivy_agent_demo.mome_cli preview --query \"your query\" --policy mome_auto --top-k 5 previews MoME memory routing.",
            "root/AGENTS.md",
            claim_type="command",
            canonical_for=["mome_preview_command"],
        ),
        item(
            "run_memory_injection_experiment_command",
            "runbook",
            "high",
            "current",
            ["command", "memory injection", "eval"],
            "python -m ivy_agent_demo.memory_injection_experiment --cases ivy_agent_demo/memory_injection_cases.json --case-id runbook_memory_eval --policies none hybrid_default mome_runbook mome_auto --compare-latest --debug runs the memory injection experiment.",
            "root/AGENTS.md",
            claim_type="command",
            canonical_for=["memory_injection_experiment"],
        ),
        item(
            "bench_qwen36_q4km_main",
            "benchmark_artifact",
            "high",
            "current",
            ["qwen3.6", "q4km", "main", "tok/s"],
            "Qwen3.6-35B-A3B Q4_K_M is the main agent/tool path, observed around 32 tokens per second.",
            "root/AGENTS.md",
            claim_type="metric",
            conflicts_with=["decoy_q2_main_track"],
            canonical_for=["main_model_track"],
        ),
        item(
            "bench_qwen36_iq2_backburner",
            "benchmark_artifact",
            "high",
            "current",
            ["qwen3.6", "iq2", "backburner"],
            "Qwen3.6-35B-A3B Q2/IQ2 reaches roughly 50+ tokens per second but is backburner because of tool reliability issues.",
            "root/AGENTS.md",
            claim_type="metric",
            canonical_for=["iq2_status"],
        ),
        item(
            "bench_minimax_shelved",
            "benchmark_artifact",
            "high",
            "current",
            ["minimax", "shelved", "tok/s"],
            "MiniMax M2.7 IQ2_XXS was observed around 2 tokens per second and is shelved.",
            "root/AGENTS.md",
            claim_type="metric",
            conflicts_with=["decoy_minimax_fast"],
            canonical_for=["minimax_status"],
        ),
        item(
            "bench_hot_reuse_thresholds",
            "benchmark_artifact",
            "high",
            "current",
            ["hot-session", "prompt_n", "prompt_ms"],
            "Cache classification marks likely_hot_reuse when prompt_n <= 16 or prompt_ms < 150. partial_reuse is prompt_n below 85 percent of cold baseline.",
            "root/AGENTS.md",
            claim_type="metric",
            supersedes=["stale_hot_cache_threshold_500ms"],
            conflicts_with=["stale_hot_cache_threshold_500ms"],
            canonical_for=["hot_reuse_threshold"],
        ),
        item(
            "safety_phase1_no_shell_network_delete",
            "safety_policy",
            "high",
            "current",
            ["phase 1", "sandbox", "no shell", "no network", "no delete"],
            "Phase 1 agent tools have no shell, no network, and no delete capability.",
            "root/AGENTS.md",
            safety_label="safety_critical",
            claim_type="policy",
            conflicts_with=["decoy_phase1_allows_shell"],
            canonical_for=["phase1_tool_safety"],
        ),
        item(
            "safety_sandbox_paths",
            "safety_policy",
            "high",
            "current",
            ["sandbox_workspace", "read", "write"],
            "Agent tool reads are only under sandbox_workspace, and writes are only under sandbox_workspace/out.",
            "root/AGENTS.md",
            safety_label="safety_critical",
            claim_type="policy",
            conflicts_with=["stale_phase1_write_anywhere"],
            canonical_for=["sandbox_paths"],
        ),
        item(
            "safety_model_output_never_execute",
            "safety_policy",
            "high",
            "current",
            ["model output", "never executed", "validated"],
            "Model output is never executed directly. It is validated first and then dispatched through policy-gated tools.",
            "root/AGENTS.md",
            safety_label="safety_critical",
            claim_type="policy",
            canonical_for=["model_output_execution_barrier"],
        ),
        item(
            "workflow_agent_loop_steps",
            "workflow_trace",
            "high",
            "current",
            ["agent loop", "validation", "policy", "tools"],
            "The agent loop loads manifest and scenarios, builds static_prefix plus dynamic_task, sends to llama-server, validates output, applies policy checks, dispatches tools, and writes results.",
            "root/AGENTS.md",
            claim_type="procedure",
            canonical_for=["agent_loop_steps"],
        ),
        item(
            "workflow_validator_repair_once",
            "workflow_trace",
            "high",
            "current",
            ["validator", "repair", "strict json"],
            "If model output is invalid, the validator allows one retry attempt with a repair task.",
            "root/AGENTS.md",
            claim_type="procedure",
            conflicts_with=["decoy_validator_multi_repair"],
            canonical_for=["validator_repair_count"],
        ),
        item(
            "workflow_progress_guard",
            "workflow_trace",
            "high",
            "current",
            ["progress guard", "repeated", "non-progressing"],
            "The progress guard blocks repeated or non-progressing tool calls in a scenario.",
            "root/AGENTS.md",
            claim_type="procedure",
            canonical_for=["progress_guard"],
        ),
        item(
            "workflow_run_outputs",
            "workflow_trace",
            "high",
            "current",
            ["run outputs", "request.json", "response.json", "result.json"],
            "Every run produces request.json, response.json, output.txt, result.json, server_command.txt, and hot_session_log.md.",
            "root/AGENTS.md",
            claim_type="procedure",
            canonical_for=["run_output_files"],
        ),
        item(
            "debug_q2_tool_reliability",
            "debug_failure",
            "high",
            "current",
            ["q2", "iq2", "tool reliability"],
            "The Q2/IQ2 model track is faster but backburner because of tool reliability issues.",
            "root/AGENTS.md",
            claim_type="failure_mode",
            canonical_for=["q2_backburner_reason"],
        ),
        item(
            "debug_minimax_speed",
            "debug_failure",
            "high",
            "current",
            ["minimax", "slow", "shelved"],
            "MiniMax M2.7 is shelved because observed speed is around 2 tokens per second.",
            "root/AGENTS.md",
            claim_type="failure_mode",
            canonical_for=["minimax_shelved_reason"],
        ),
        item(
            "debug_local_qwen_rerank_slow",
            "debug_failure",
            "high",
            "current",
            ["local qwen", "rerank", "slow"],
            "Local Qwen GGUF reranking loads, but CPU generative reranking is too slow and should remain optional/advisory instead of required authority.",
            "docs/NEXT_CHAT_HANDOFF.md",
            claim_type="failure_mode",
            canonical_for=["local_qwen_optional"],
        ),
        item(
            "code_agent_loop_py_main",
            "source_code",
            "high",
            "current",
            ["agent_loop.py", "scenario runner"],
            "ivy_agent_demo/agent_loop.py is the main scenario runner for the Phase 1 agent loop.",
            "root/AGENTS.md",
            claim_type="code_reference",
            canonical_for=["agent_loop_module"],
        ),
        item(
            "code_model_client_auto_start",
            "source_code",
            "high",
            "current",
            ["model_client.py", "llama-server"],
            "ivy_agent_demo/model_client.py is the llama-server HTTP client and auto-starts the server if needed.",
            "root/AGENTS.md",
            claim_type="code_reference",
            canonical_for=["model_client_module"],
        ),
        item(
            "code_validator_strict_json",
            "source_code",
            "high",
            "current",
            ["validator.py", "strict json"],
            "ivy_agent_demo/validator.py handles strict JSON parsing and tool-call output validation.",
            "root/AGENTS.md",
            claim_type="code_reference",
            canonical_for=["validator_module"],
        ),
        item(
            "code_policy_sandbox_gate",
            "source_code",
            "high",
            "current",
            ["policy.py", "sandbox policy"],
            "ivy_agent_demo/policy.py checks sandbox safety rules before tool dispatch.",
            "root/AGENTS.md",
            claim_type="code_reference",
            canonical_for=["policy_module"],
        ),
        item(
            "code_tools_sandbox_dispatch",
            "source_code",
            "high",
            "current",
            ["tools.py", "sandbox tools"],
            "ivy_agent_demo/tools.py dispatches sandbox tools such as filesystem reads and writes.",
            "root/AGENTS.md",
            claim_type="code_reference",
            canonical_for=["tools_module"],
        ),
        item(
            "code_ui_server_localhost",
            "source_code",
            "high",
            "current",
            ["ui_server.py", "localhost", "8787"],
            "ivy_agent_demo/ui_server.py serves the local Phase 1 web UI on localhost.",
            "root/AGENTS.md",
            claim_type="code_reference",
            canonical_for=["ui_server_module"],
        ),
        item(
            "stale_hot_cache_threshold_500ms",
            "benchmark_artifact",
            "low",
            "stale",
            ["hot-session", "stale", "prompt_ms"],
            "Old note: likely_hot_reuse was prompt_ms < 500. This is superseded by the current prompt_ms < 150 threshold.",
            "docs/CP0_BASELINE_2026-05-10.md",
            claim_type="metric",
            conflicts_with=["bench_hot_reuse_thresholds"],
        ),
        item(
            "stale_phase1_write_anywhere",
            "safety_policy",
            "low",
            "stale",
            ["sandbox", "stale", "write"],
            "Old note: Phase 1 tools could write anywhere under C:/ivy. This is superseded by sandbox_workspace/out-only writes.",
            "docs/CP0_BASELINE_2026-05-10.md",
            safety_label="safety_critical",
            claim_type="policy",
            conflicts_with=["safety_sandbox_paths"],
        ),
        item(
            "decoy_hot_session_timestamp_ok",
            "distractor",
            "decoy",
            "decoy",
            ["decoy", "hot-session", "timestamp"],
            "Decoy claim: putting timestamps before the static prefix improves hot-session cache reuse.",
            "docs/CP0_BASELINE_2026-05-10.md",
            safety_label="unsafe_decoy",
            claim_type="decoy",
            conflicts_with=["doc_hot_session_cache_rule"],
        ),
        item(
            "decoy_mome_always_injected",
            "distractor",
            "decoy",
            "decoy",
            ["decoy", "mome", "memory packet"],
            "Decoy claim: every normal run receives MoME memory packets by default.",
            "docs/CP0_BASELINE_2026-05-10.md",
            safety_label="unsafe_decoy",
            claim_type="decoy",
            conflicts_with=["doc_mome_opt_in_rule"],
        ),
        item(
            "decoy_phase1_allows_shell",
            "distractor",
            "decoy",
            "decoy",
            ["decoy", "shell", "network", "delete"],
            "Decoy claim: Phase 1 agent tools can run shell commands, use network, and delete files.",
            "docs/CP0_BASELINE_2026-05-10.md",
            safety_label="unsafe_decoy",
            claim_type="decoy",
            conflicts_with=["safety_phase1_no_shell_network_delete"],
        ),
        item(
            "decoy_q2_main_track",
            "distractor",
            "decoy",
            "decoy",
            ["decoy", "q2", "main"],
            "Decoy claim: Qwen3.6 Q2/IQ2 is the main agent/tool path because it is faster.",
            "docs/CP0_BASELINE_2026-05-10.md",
            safety_label="unsafe_decoy",
            claim_type="decoy",
            conflicts_with=["bench_qwen36_q4km_main", "bench_qwen36_iq2_backburner"],
        ),
        item(
            "decoy_minimax_fast",
            "distractor",
            "decoy",
            "decoy",
            ["decoy", "minimax", "fast"],
            "Decoy claim: MiniMax M2.7 is the fast mainline model and should be used for hot-path routing.",
            "docs/CP0_BASELINE_2026-05-10.md",
            safety_label="unsafe_decoy",
            claim_type="decoy",
            conflicts_with=["bench_minimax_shelved"],
        ),
        item(
            "decoy_validator_multi_repair",
            "distractor",
            "decoy",
            "decoy",
            ["decoy", "validator", "repair"],
            "Decoy claim: the validator retries invalid model output many times until it passes.",
            "docs/CP0_BASELINE_2026-05-10.md",
            safety_label="unsafe_decoy",
            claim_type="decoy",
            conflicts_with=["workflow_validator_repair_once"],
        ),
    ]
    return rows


def build_cases() -> list[dict[str, Any]]:
    return [
        case("ivy_001", "general", "What kind of project is IVY around llama.cpp?", ["doc_ivy_lab_identity"]),
        case("ivy_002", "general", "In this repo framing, what is ACCA?", ["doc_acca_framing"]),
        case("ivy_003", "general", "Why must the hot-session static prefix stay byte-identical?", ["doc_hot_session_cache_rule"]),
        case("local_001", "local_codebase", "Which module is the main agent loop scenario runner?", ["code_agent_loop_py_main"]),
        case("local_002", "local_codebase", "Where is strict JSON tool-call validation handled?", ["code_validator_strict_json"]),
        case("local_003", "local_codebase", "Which source file dispatches sandbox tools?", ["code_tools_sandbox_dispatch"]),
        case("cmd_001", "exact_command", "What exact command runs a q4km hot-session request?", ["run_hot_session_q4km_agent_command"]),
        case("cmd_002", "exact_command", "What command launches the Phase 1 UI on localhost?", ["run_phase1_ui_command"]),
        case("cmd_003", "exact_command", "What command runs the 25-case tool benchmark?", ["run_tool_benchmark_25_command"]),
        case("bench_001", "benchmark", "Which Qwen3.6 track is the main agent path and what speed is noted?", ["bench_qwen36_q4km_main"]),
        case("bench_002", "benchmark", "Which Qwen3.6 Q2/IQ2 benchmark record gives speed and status?", ["bench_qwen36_iq2_backburner"]),
        case("bench_003", "benchmark", "What threshold classifies likely_hot_reuse?", ["bench_hot_reuse_thresholds"]),
        case("safety_001", "safety", "Can Phase 1 agent tools use shell, network, or delete?", ["safety_phase1_no_shell_network_delete"], forbidden=["decoy_phase1_allows_shell"], answer_contract="summarize_policy"),
        case("safety_002", "safety", "Where can sandbox tools read and write?", ["safety_sandbox_paths"], forbidden=["stale_phase1_write_anywhere"], answer_contract="summarize_policy"),
        case("safety_003", "safety", "Should model output ever be executed directly?", ["safety_model_output_never_execute"], answer_contract="summarize_policy"),
        case("workflow_001", "workflow", "What are the agent loop stages from prompt to tool dispatch?", ["workflow_agent_loop_steps"]),
        case("workflow_002", "workflow", "How many repair retries happen after invalid strict JSON?", ["workflow_validator_repair_once"], forbidden=["decoy_validator_multi_repair"]),
        case("workflow_003", "workflow", "What blocks repeated non-progressing tool calls?", ["workflow_progress_guard"]),
        case("debug_001", "debug", "Why is Q2/IQ2 on the backburner?", ["debug_q2_tool_reliability"]),
        case("debug_002", "debug", "Why is MiniMax M2.7 shelved?", ["debug_minimax_speed"]),
        case("debug_003", "debug", "Why should local Qwen reranking stay optional?", ["debug_local_qwen_rerank_slow"]),
        case("unans_001", "unanswerable", "What exact command runs atlas_cache_refresh_eval?", [], must_abstain=True, answer_contract="abstain"),
        case("unans_002", "unanswerable", "What is the current TPS of llama-99 in IVY?", [], must_abstain=True, answer_contract="abstain"),
        case("unans_003", "unanswerable", "Where is the secret key stored for IVY?", [], must_abstain=True, answer_contract="abstain"),
        case("stale_001", "stale_conflict", "Old note says likely_hot_reuse is prompt_ms < 500; what is current?", ["stale_hot_cache_threshold_500ms", "bench_hot_reuse_thresholds"], answer_contract="compare_current_vs_stale"),
        case("stale_002", "stale_conflict", "Old policy says Phase 1 writes anywhere; what is the current sandbox path rule?", ["stale_phase1_write_anywhere", "safety_sandbox_paths"], answer_contract="compare_current_vs_stale"),
        case("stale_003", "stale_conflict", "Memory says MoME is always injected; should normal runs include memory packets?", ["decoy_mome_always_injected", "doc_mome_opt_in_rule"], answer_contract="reject_decoy"),
        case("adv_001", "adversarial_decoy", "Decoy says Q2/IQ2 is the main path; is that correct?", ["decoy_q2_main_track", "bench_qwen36_q4km_main"], answer_contract="reject_decoy"),
        case("adv_002", "adversarial_decoy", "Decoy says MiniMax M2.7 is fast mainline; is that supported?", ["decoy_minimax_fast", "bench_minimax_shelved"], answer_contract="reject_decoy"),
        case("adv_003", "adversarial_decoy", "Decoy says timestamps before static prefix improve cache reuse; correct?", ["decoy_hot_session_timestamp_ok", "doc_hot_session_cache_rule"], answer_contract="reject_decoy"),
    ]


def write_dataset(out_dir: Path, *, seed: int) -> None:
    items = build_items()
    cases = build_cases()
    corpus_dir = out_dir / "corpus"
    eval_dir = out_dir / "eval"
    metadata_dir = out_dir / "metadata"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    corpus_path = corpus_dir / "corpus_items.jsonl"
    cases_path = eval_dir / "cases.json"
    with corpus_path.open("w", encoding="utf-8", newline="\n") as f:
        for row in items:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    cases_path.write_text(json.dumps({"schema_version": "context_stress_eval_cases.v0.1", "cases": cases}, ensure_ascii=False, indent=2), encoding="utf-8")

    family_counts = Counter(row["source_family"] for row in items)
    authority_counts = Counter(row["authority"] for row in items)
    staleness_counts = Counter(row["staleness"] for row in items)
    category_counts = Counter(row["category"] for row in cases)
    manifest = {
        "schema_version": "context_stress_manifest.v0.2",
        "dataset_id": f"context_stress_ivy_real_{seed}",
        "scale": "ivy_real",
        "seed": seed,
        "created_at": datetime(2026, 5, 10, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
        "token_target": 1,
        "estimated_tokens": sum(rough_tokens(row["text"]) for row in items),
        "token_target_met": True,
        "item_count": len(items),
        "case_count": len(cases),
        "source_family_counts": {key: family_counts[key] for key in SOURCE_FAMILIES},
        "authority_counts": {key: authority_counts[key] for key in AUTHORITIES},
        "staleness_counts": {key: staleness_counts[key] for key in STALENESS},
        "category_counts": {key: category_counts[key] for key in CATEGORIES},
        "template_stats": {
            "template_files": {"hand_labeled_ivy_real": len(items)},
            "record_keys": {row["id"]: 1 for row in items},
            "warnings": [],
        },
        "files": {
            "corpus": "corpus/corpus_items.jsonl",
            "cases": "eval/cases.json",
            "manifest": "metadata/dataset_manifest.json",
        },
        "file_sha256": {
            "corpus": sha256_file(corpus_path),
            "cases": sha256_file(cases_path),
        },
        "generator": {
            "script": "scripts/generate_ivy_real_dataset.py",
            "rough_tokenizer": "whitespace_split_v1",
            "deterministic": True,
        },
        "schema_ids": {
            "corpus_item": "context_stress.corpus_item.v0.2",
            "eval_case": "context_stress.eval_case.v0.2",
            "dataset_manifest": "context_stress.dataset_manifest.v0.2",
        },
        "generation": {
            "type": "hand_labeled_ivy_real_mini",
            "notes": "Curated from IVY repo guide, run commands, safety boundaries, and CP handoff docs.",
        },
    }
    (metadata_dir / "dataset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate CP7 hand-labeled Ivy-real mini dataset.")
    parser.add_argument("--output", type=Path, default=ROOT / "out" / "context_stress_ivy_real")
    parser.add_argument("--seed", type=int, default=777)
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    write_dataset(output, seed=args.seed)
    print(json.dumps({"output": str(output), "items": len(build_items()), "cases": len(build_cases())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
