from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .engine_client import DogfoodHttpClient
from .transform import build_dashboard_view
from .validate import collect_contract_issues, validate_bundle


@dataclass(frozen=True)
class HarnessScenario:
    name: str
    query: str
    seed_items: list[dict[str, Any]] = field(default_factory=list)
    strategy: str = "helper-lazy"
    max_evidence_items: int = 3


ALEXANDRIA_SCENARIOS: dict[str, HarnessScenario] = {
    "empty": HarnessScenario(
        name="empty",
        query="What does Alexandria know about the dashboard hook boundary?",
        seed_items=[],
    ),
    "answerable": HarnessScenario(
        name="answerable",
        query="How should Alexandria connect the website to D-ACCA hooks?",
        seed_items=[
            {
                "id": "alexandria_contract_boundary",
                "text": (
                    "Alexandria should connect the website to D-ACCA through a harness boundary, not raw React fetches. "
                    "The harness validates engine responses, enforces route/proof invariants, and emits a dashboard view model."
                ),
                "source_family": "source_code",
                "authority": "high",
                "claim_type": "fact",
                "tags": ["alexandria", "harness", "d-acca", "frontend"],
                "aliases": ["website hook boundary", "dashboard view model", "D-ACCA harness"],
                "helper_query": "Alexandria website D-ACCA harness dashboard view model contract boundary",
                "guard_terms": ["alexandria", "harness"],
                "replay_match_terms": ["website", "d-acca", "hooks", "harness"],
                "distillation_patterns": [["alexandria", "harness"], ["website", "d-acca"]],
            },
            {
                "id": "alexandria_model_visible_packet",
                "text": (
                    "Only the /packet packet is model-visible by default. Route proof and helper advice are dashboard-only debug data."
                ),
                "source_family": "safety_policy",
                "authority": "high",
                "claim_type": "policy",
                "tags": ["alexandria", "packet", "proof", "model_visible"],
                "aliases": ["model visible packet", "route proof is dashboard only"],
                "helper_query": "Alexandria model visible packet proof dashboard only",
                "guard_terms": ["packet", "proof"],
                "replay_match_terms": ["model visible", "proof", "dashboard"],
                "distillation_patterns": [["model", "visible"], ["route", "proof"]],
            },
        ],
    ),
    "stale_conflict": HarnessScenario(
        name="stale_conflict",
        query="What is the current rule for exposing Alexandria proof data?",
        seed_items=[
            {
                "id": "alexandria_old_proof_rule",
                "text": "Old draft: Alexandria may expose raw proof traces directly to the model prompt.",
                "source_family": "doc_memory",
                "authority": "low",
                "claim_type": "policy",
                "staleness": "stale",
                "tags": ["alexandria", "proof", "stale"],
                "aliases": ["old proof rule", "raw proof to model"],
                "helper_query": "old Alexandria raw proof model prompt stale",
                "guard_terms": ["proof"],
            },
            {
                "id": "alexandria_current_proof_rule",
                "text": "Current rule: Alexandria keeps proof and helper advice in dashboard-only state; only admitted packet evidence is model-visible.",
                "source_family": "safety_policy",
                "authority": "high",
                "claim_type": "policy",
                "staleness": "current",
                "tags": ["alexandria", "proof", "model_visible"],
                "aliases": ["current proof rule", "dashboard-only proof", "admitted packet evidence"],
                "helper_query": "current Alexandria proof dashboard-only admitted packet evidence model-visible",
                "guard_terms": ["proof", "packet"],
                "replay_match_terms": ["current", "proof", "model visible"],
                "distillation_patterns": [["current", "proof"], ["dashboard", "only"]],
            },
        ],
    ),
    "safety_block": HarnessScenario(
        name="safety_block",
        query="Should Alexandria reveal private API keys to a model?",
        seed_items=[
            {
                "id": "alexandria_private_key_decoy",
                "text": "Do not expose secrets. Example fake key: sk-test-never-send-this.",
                "source_family": "safety_policy",
                "authority": "high",
                "claim_type": "policy",
                "safety_label": "secret_like",
                "exposure_policy": "forbidden",
                "tags": ["alexandria", "security", "secret"],
                "aliases": ["private API key", "secret key", "do not expose secrets"],
                "helper_query": "Alexandria private API keys secrets forbidden",
                "guard_terms": ["secret", "key"],
            }
        ],
    ),
}


def run_scenario(
    client: Any,
    scenario: HarnessScenario,
    *,
    output_dir: Path | None = None,
    ingest: bool = True,
    include_proof: bool = False,
) -> dict[str, Any]:
    ingest_response = None
    if ingest and scenario.seed_items:
        ingest_response = client.ingest(
            {
                "source": f"alexandria_harness_{scenario.name}",
                "project": "alexandria",
                "items": scenario.seed_items,
            }
        )

    snapshot = client.snapshot(limit=100, include_text=False)
    request = {
        "query": scenario.query,
        "strategy": scenario.strategy,
        "include_proof": include_proof,
        "max_evidence_items": scenario.max_evidence_items,
    }
    packet_response = client.packet(request)
    proof_path = packet_response.get("_proof_path") or packet_response.get("route_id")
    proof_response = client.proof(proof_path) if proof_path else None
    snapshot_after = client.snapshot(limit=100, include_text=False)
    snapshot_dict = snapshot_after.to_dict()
    validation = collect_contract_issues(snapshot_dict, packet_response, proof_response)
    if validation["valid"]:
        validate_bundle(snapshot_dict, packet_response, proof_response)
    dashboard_view = build_dashboard_view(
        snapshot_after,
        packet_response,
        proof_response,
        api_base=getattr(client, "base_url", "local://dogfood-hooks"),
        command=scenario.query,
    )
    report = {
        "scenario": scenario.name,
        "valid": validation["valid"],
        "errors": validation["errors"],
        "warnings": validation["warnings"],
        "memory_count_before": snapshot.health.get("memory_count"),
        "memory_count_after": snapshot_after.health.get("memory_count"),
        "route_id": packet_response.get("route_id"),
        "selected_ids": packet_response.get("selected_ids", []),
        "confidence": packet_response.get("confidence"),
        "latency_ms": packet_response.get("latency_ms"),
    }
    result = {
        "request": request,
        "ingest_response": ingest_response,
        "snapshot": snapshot_dict,
        "packet_response": packet_response,
        "proof_response": proof_response,
        "dashboard_view": dashboard_view,
        "report": report,
    }
    if output_dir is not None:
        write_result(output_dir, result)
    return result


def write_result(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in (
        ("request.json", result["request"]),
        ("ingest_response.json", result["ingest_response"] or {}),
        ("snapshot.json", result["snapshot"]),
        ("packet_response.json", result["packet_response"]),
        ("proof_response.json", result["proof_response"] or {}),
        ("dashboard_view.json", result["dashboard_view"]),
        ("report.json", result["report"]),
    ):
        (output_dir / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Alexandria harness scenarios against D-ACCA dogfood hooks.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8766")
    parser.add_argument("--scenario", choices=sorted(ALEXANDRIA_SCENARIOS), default="answerable")
    parser.add_argument("--query", default="")
    parser.add_argument("--output", type=Path, default=Path("out") / "alexandria_harness")
    parser.add_argument("--no-ingest", action="store_true")
    parser.add_argument("--include-proof", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)

    if args.list:
        for scenario_name in sorted(ALEXANDRIA_SCENARIOS):
            print(scenario_name)
        return 0

    scenario = ALEXANDRIA_SCENARIOS[args.scenario]
    if args.query:
        scenario = HarnessScenario(
            name=scenario.name,
            query=args.query,
            seed_items=scenario.seed_items,
            strategy=scenario.strategy,
            max_evidence_items=scenario.max_evidence_items,
        )
    client = DogfoodHttpClient(args.base_url)
    result = run_scenario(
        client,
        scenario,
        output_dir=args.output / scenario.name,
        ingest=not args.no_ingest,
        include_proof=args.include_proof,
    )
    print(json.dumps(result["report"], ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["report"]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
