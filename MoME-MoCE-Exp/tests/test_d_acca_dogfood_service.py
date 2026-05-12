from __future__ import annotations

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from scripts.d_acca_dogfood_service import DogfoodHooks, make_handler


def test_dogfood_hooks_ingest_packet_proof_feedback_and_forget(tmp_path) -> None:
    hooks = DogfoodHooks(tmp_path / "dogfood")

    ingest = hooks.ingest(
        {
            "items": [
                {
                    "id": "signal_phone_bridge",
                    "text": "Signal phone pings use the local Signal daemon plus the phone bridge. Use this memory for ping-my-phone agent progress updates.",
                    "source_family": "runbook",
                    "authority": "high",
                    "tags": ["signal", "phone", "runbook"],
                    "aliases": ["ping my phone", "signalcli", "phone bridge"],
                    "helper_query": "Signal local push reply phone daemon Tailscale Web Push agent pings",
                    "guard_terms": ["signal"],
                    "replay_match_terms": ["ping my phone", "signalcli"],
                    "distillation_patterns": [["ping", "phone"], ["signalcli"]],
                },
                {
                    "id": "recall_board_memory",
                    "text": "Recall Board is the visual second-brain surface for editable Excalidraw graph context.",
                    "source_family": "doc_memory",
                    "authority": "medium",
                    "tags": ["recall", "second brain"],
                    "aliases": ["recall-board", "visual second brain"],
                },
            ]
        }
    )
    assert ingest["ingested"] == 2
    signal_id = next(item_id for item_id in ingest["ids"] if item_id.startswith("signal_phone_bridge"))

    search = hooks.search("signalcli ping my phone", include_text=False)
    assert search["items"][0]["id"] == signal_id
    assert "text_preview" in search["items"][0]
    assert "text" not in search["items"][0]

    packet = hooks.packet(
        {
            "query": "how do I ping my phone from codex with signalcli?",
            "strategy": "helper-lazy",
            "include_proof": True,
        }
    )
    assert packet["strategy"] == "helper-lazy"
    assert signal_id in packet["selected_ids"]
    assert packet["packet"]["evidence"][0]["id"] == signal_id
    assert packet["route_proof"]["selected_ids"] == packet["selected_ids"]

    stored = hooks.proof(packet["route_id"])
    assert stored["route_id"] == packet["route_id"]
    assert stored["route_proof"]["selected_ids"] == packet["selected_ids"]

    feedback = hooks.feedback({"route_id": packet["route_id"], "rating": "useful", "note": "correct phone bridge memory"})
    assert feedback["saved"] is True
    assert feedback["feedback"]["rating"] == "useful"

    forgotten = hooks.forget({"ids": [signal_id], "reason": "test cleanup"})
    assert forgotten["removed"] == 1
    assert signal_id not in {item["id"] for item in hooks.list_memories(include_text=True)["items"]}


def test_dogfood_hooks_direct_d_acca_packet(tmp_path) -> None:
    hooks = DogfoodHooks(tmp_path / "dogfood")
    ingest = hooks.ingest(
        {
            "text": "ACCA packets are compact admissible context packets with selected evidence and route proofs.",
            "source": "manual",
            "source_family": "doc_memory",
            "authority": "high",
            "tags": ["acca", "context packet"],
        }
    )
    item_id = ingest["ids"][0]

    packet = hooks.packet({"query": "ACCA context packet route proof", "strategy": "d-acca", "include_proof": True})
    assert packet["strategy"] == "d-acca"
    assert item_id in packet["selected_ids"]
    assert packet["artifact_errors"] == []
    assert packet["packet"]["packet_version"] == "acca.frontier_context_packet.v0.1"


def test_dogfood_hooks_discovery_contract(tmp_path) -> None:
    hooks = DogfoodHooks(tmp_path / "dogfood")
    spec = hooks.hooks()
    paths = {(endpoint["method"], endpoint["path"]) for endpoint in spec["endpoints"]}
    assert ("POST", "/packet") in paths
    assert ("POST", "/ingest") in paths
    assert ("GET", "/proof/{route_id}") in paths
    assert spec["model_visible_default"].startswith("Only /packet.packet")


def test_dogfood_http_hooks_smoke(tmp_path) -> None:
    hooks = DogfoodHooks(tmp_path / "dogfood")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(hooks))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        spec = http_get_json(f"{base_url}/hooks")
        assert spec["service_version"] == "d_acca.dogfood_hooks.v0.1"

        ingest = http_post_json(
            f"{base_url}/ingest",
            {
                "text": "ACCA service hooks expose packet, proof, feedback, search, and forget APIs.",
                "tags": ["acca", "hooks"],
                "aliases": ["exposable hooks"],
            },
        )
        assert ingest["ingested"] == 1

        packet = http_post_json(
            f"{base_url}/packet",
            {"query": "ACCA exposable hooks packet proof feedback", "strategy": "helper-lazy"},
        )
        assert packet["route_id"].startswith("route_")
        assert "packet" in packet

        proof = http_get_json(f"{base_url}/proof/{packet['route_id']}")
        assert proof["route_id"] == packet["route_id"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def http_get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def http_post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))
