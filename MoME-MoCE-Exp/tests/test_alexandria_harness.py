from __future__ import annotations

import threading
from http.server import ThreadingHTTPServer

import pytest

from alexandria_harness import ContractError, DogfoodHooksObjectClient, DogfoodHttpClient, validate_bundle
from alexandria_harness.scenario_runner import ALEXANDRIA_SCENARIOS, HarnessScenario, run_scenario
from scripts.d_acca_dogfood_service import DogfoodHooks, make_handler


def test_harness_builds_dashboard_view_from_hook_object(tmp_path) -> None:
    hooks = DogfoodHooks(tmp_path / "dogfood")
    client = DogfoodHooksObjectClient(hooks)

    result = run_scenario(client, ALEXANDRIA_SCENARIOS["answerable"], output_dir=tmp_path / "harness" / "answerable")

    view = result["dashboard_view"]
    report = result["report"]
    assert report["valid"] is True
    assert report["selected_ids"]
    assert view["status"]["valid"] is True
    assert view["model_packet"]["role"] == "frontier_model_context_packet"
    assert view["dashboard"]["metrics"]["confidence"] >= 80
    assert view["dashboard"]["context_packet"]["relevant_memory"] == len(report["selected_ids"])
    assert (tmp_path / "harness" / "answerable" / "dashboard_view.json").exists()
    assert (tmp_path / "harness" / "answerable" / "packet_response.json").exists()


def test_empty_corpus_view_stays_empty_not_demo_populated(tmp_path) -> None:
    hooks = DogfoodHooks(tmp_path / "dogfood")
    client = DogfoodHooksObjectClient(hooks)
    scenario = HarnessScenario(name="empty_local", query="What project memory exists?", seed_items=[], max_evidence_items=3)

    result = run_scenario(client, scenario, ingest=False)
    view = result["dashboard_view"]

    assert result["report"]["valid"] is True
    assert result["report"]["memory_count_after"] == 0
    assert result["packet_response"]["selected_ids"] == []
    assert view["status"]["memory_count"] == 0
    assert view["dashboard"]["memory_overview"]["total"] == 0
    assert view["dashboard"]["context_packet"]["relevant_memory"] == 0
    assert view["dashboard"]["memory_rows"] == []


def test_contract_rejects_packet_proof_mismatch() -> None:
    snapshot = {
        "health": {"ok": True, "service_version": "d_acca.dogfood_hooks.v0.1", "memory_count": 1},
        "hooks": {"service_version": "d_acca.dogfood_hooks.v0.1", "endpoints": []},
        "memories": {"total": 1, "items": []},
    }
    packet = {
        "route_id": "route_a",
        "strategy": "helper-lazy",
        "decision": "context_packet_ready",
        "confidence": 0.9,
        "selected_ids": ["memory_a"],
        "latency_ms": 0.5,
        "packet": {
            "packet_version": "d_acca.dogfood_context_packet.v0.1",
            "role": "frontier_model_context_packet",
            "query": "query",
            "evidence": [{"id": "memory_a", "text": "fact"}],
            "context_budget": {"max_evidence_items": 1, "selected_evidence_items": 1, "frontier_packet_tokens": 1},
            "constraints": [],
        },
        "artifact_errors": [],
    }
    proof = {
        "route_id": "route_a",
        "route_proof": {
            "route_id": "route_a",
            "strategy": "helper-lazy",
            "decision": "context_packet_ready",
            "selected_ids": ["memory_b"],
        },
    }

    with pytest.raises(ContractError, match="proof selected ids"):
        validate_bundle(snapshot, packet, proof)


def test_http_client_smoke_runs_same_harness_contract(tmp_path) -> None:
    hooks = DogfoodHooks(tmp_path / "dogfood")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(hooks))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = DogfoodHttpClient(f"http://127.0.0.1:{server.server_port}")
        result = run_scenario(client, ALEXANDRIA_SCENARIOS["answerable"])
        assert result["report"]["valid"] is True
        assert result["dashboard_view"]["api_base"] == f"http://127.0.0.1:{server.server_port}"
        assert result["dashboard_view"]["raw_refs"]["route_id"].startswith("route_")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
