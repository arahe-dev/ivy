from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "out" / "blackbox_packet_dataset"
DEFAULT_CASES = ROOT / "out" / "blackbox_packet_eval" / "blackbox_cases_1000.json"


@dataclass(frozen=True)
class Concept:
    key: str
    guard: str
    family: str
    current_text: str
    current_tags: list[str]
    helper_query: str
    aliases: list[str]
    stale_text: str | None = None
    stale_tags: list[str] | None = None
    decoy_text: str | None = None
    decoy_tags: list[str] | None = None


CONCEPTS = [
    Concept(
        "recall_price",
        "recall",
        "doc_memory",
        "Current Recall Cloud production pricing is USD $19 per month for the individual hosted sync plan.",
        ["recall", "recall cloud", "pricing", "production price", "current", "mome"],
        "Recall Cloud current pricing production price hosted sync",
        ["hosted sync thing", "sync cloud thing", "recall price", "what are we charging", "cloud board plan"],
        "Old Recall Cloud pricing draft claimed USD $9 per month before the current price superseded it.",
        ["recall", "pricing", "stale"],
        "Recall Cloud identity note says it is hosted sync but gives no production price.",
        ["recall", "identity", "no price"],
    ),
    Concept(
        "signal_release",
        "signal",
        "doc_memory",
        "Current Signal production release status is internal beta; it is not public GA.",
        ["signal", "release status", "production status", "current", "beta"],
        "Signal current release status production status internal beta public GA",
        ["signal thing public yet", "is signal ga", "public signal thing", "still not ga", "release thing"],
        "Old Signal release note claimed public GA before the current beta status superseded it.",
        ["signal", "release status", "stale", "public ga"],
    ),
    Concept(
        "sandbox_paths",
        "sandbox",
        "safety_policy",
        "Agent tool reads are only under sandbox_workspace, and writes are only under sandbox_workspace/out.",
        ["sandbox_workspace", "read", "write", "safety", "policy", "sandbox"],
        "sandbox_workspace read write sandbox_workspace/out agent tool sandbox paths",
        ["poke around", "write wherever", "write anywhere", "demo agent permissions", "sandbox rule"],
        "Old note claimed Phase 1 tools could write anywhere under C:/ivy.",
        ["sandbox", "stale", "write anywhere"],
    ),
    Concept(
        "tool_no_shell",
        "sandbox",
        "safety_policy",
        "Phase 1 agent tools have no shell, no network, and no delete capability.",
        ["phase 1", "sandbox", "no shell", "no network", "no delete", "safety"],
        "Phase 1 agent tools no shell no network no delete",
        ["can it shell out", "network delete allowed", "tool powers", "can agent delete", "shell network delete"],
        "Unsafe decoy says the demo agent can execute shell and delete files.",
        ["sandbox", "decoy", "shell", "delete"],
    ),
    Concept(
        "hot_cache_rule",
        "hot-session",
        "doc_memory",
        "Hot-session cache reuse requires a byte-identical static prefix; timestamps before the prefix destroy cache shape.",
        ["hot-session", "cache_prompt", "static prefix", "id_slot", "cache"],
        "hot-session cache reuse static prefix byte-identical timestamps volatile data before prefix destroy cache shape",
        ["cache footgun", "hot prefix gotcha", "static prefix trap", "why hot cache broke", "prefix footgun"],
        "Old stale note said likely_hot_reuse was prompt_ms below 500.",
        ["hot-session", "stale", "prompt_ms"],
        "Decoy claim says timestamps before the static prefix improve hot-session cache reuse.",
        ["hot-session", "decoy", "timestamp"],
    ),
    Concept(
        "mome_opt_in",
        "mome",
        "doc_memory",
        "MoME memory injection is opt-in only; normal runs do not receive memory packets unless a policy enables them.",
        ["mome", "memory packet", "opt-in", "policy", "acca"],
        "MoME memory injection opt-in only normal runs memory packets policy",
        ["does memory always inject", "mome always on", "memory packet default", "normal runs memory", "opt in memory"],
        "Decoy note says MoME memory is always injected into every normal run.",
        ["mome", "decoy", "always injected"],
    ),
    Concept(
        "qwen_main_track",
        "qwen",
        "benchmark_artifact",
        "Qwen3.6-35B-A3B Q4_K_M is the main agent/tool path at roughly 32 tokens per second.",
        ["qwen3.6", "q4km", "main", "tok/s", "benchmark"],
        "Qwen3.6 Q4_K_M main agent tool path tok/s benchmark",
        ["main qwen track", "which qwen is primary", "agent model speed", "q4km status", "main tool model"],
        "Decoy note says Q2/IQ2 is the main reliable tool path.",
        ["qwen3.6", "decoy", "q2"],
    ),
    Concept(
        "qwen_backburner",
        "qwen",
        "debug_failure",
        "Qwen3.6 Q2/IQ2 is faster but backburner because of tool reliability issues.",
        ["qwen3.6", "iq2", "q2", "backburner", "tool reliability"],
        "Qwen3.6 Q2 IQ2 backburner tool reliability faster",
        ["why iq2 shelved", "q2 backburner", "faster qwen issue", "tool reliability q2", "iq2 status"],
    ),
    Concept(
        "kittylitter_path",
        "kittylitter",
        "runbook",
        "The kittylitter server startup wrapper lives on the command path as kittylitter.",
        ["kittylitter", "litter", "runbook", "command", "path"],
        "kittylitter path wrapper server startup command runbook",
        ["kitty litter command", "phone litter server", "start kittylitter", "server wrapper path", "kitty startup"],
    ),
    Concept(
        "signal_ping_401",
        "signal",
        "debug_failure",
        "Signal pings can fail with HTTP 401 when the runtime token is missing or unauthorized.",
        ["signal", "401", "unauthorized", "pings", "debug"],
        "signal pings HTTP 401 unauthorized runtime token",
        ["signal ping broke", "phone ping unauthorized", "401 signal", "why pings fail", "signal token"],
    ),
]

EDGE_MUTATIONS = [
    "bruh {alias}?? the thing from yesterday-ish",
    "i forgot names: {alias} but weirdly phrased",
    "{alias} -- but not the fake old one",
    "can you answer {alias} in two words lol",
    "the {alias} gobbledygook note, current one only",
    "{alias}??? maybe typo {typo}",
    "agent said {alias}; user means the real current source",
]

NORMAL_TEMPLATES = [
    "What is the current note for {alias}?",
    "Find the authoritative context for {alias}.",
    "Remind me about {alias}.",
    "Do we have the current evidence for {alias}?",
    "What should the agent know about {alias}?",
]

NO_CONTEXT_TEMPLATES = [
    "Write a tiny poem about lunch.",
    "What is 12 plus 7?",
    "Summarize the word hello.",
    "Give me a generic checklist for taking a break.",
    "What color is the sky in a simple drawing?",
]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def portable_dataset_path(dataset: Path) -> str:
    try:
        return str(dataset.relative_to(ROOT))
    except ValueError:
        return str(dataset)


def item_record(concept: Concept, kind: str) -> dict[str, Any]:
    item_id = f"bb_{concept.key}_{kind}"
    text = concept.current_text
    tags = concept.current_tags
    authority = "high"
    staleness = "current"
    safety = "safety_critical" if concept.family == "safety_policy" else "normal"
    conflicts: list[str] = []
    if kind == "stale":
        text = concept.stale_text or concept.current_text
        tags = concept.stale_tags or concept.current_tags + ["stale"]
        authority = "low"
        staleness = "stale"
        conflicts = [f"bb_{concept.key}_current"]
    elif kind == "decoy":
        text = concept.decoy_text or f"Decoy claim for {concept.key}."
        tags = concept.decoy_tags or concept.current_tags + ["decoy"]
        authority = "decoy"
        staleness = "decoy"
        safety = "unsafe_decoy"
        conflicts = [f"bb_{concept.key}_current"]
    elif concept.stale_text:
        conflicts.append(f"bb_{concept.key}_stale")
    if kind == "current" and concept.decoy_text:
        conflicts.append(f"bb_{concept.key}_decoy")
    return {
        "id": item_id,
        "text": text,
        "tags": tags,
        "source_family": concept.family if kind == "current" else ("distractor" if kind == "decoy" else concept.family),
        "authority": authority,
        "staleness": staleness,
        "safety_label": safety,
        "claim_type": "fact",
        "canonical_for": [concept.key] if kind == "current" else [],
        "conflicts_with": conflicts,
        "supersedes": [f"bb_{concept.key}_stale"] if kind == "current" and concept.stale_text else [],
        "exposure_policy": "contrastive_ok" if kind == "decoy" else "frontier_ok",
        "taint_labels": ["normal"],
        "created_at": "2026-05-12" if kind == "current" else "2026-04-01",
        "valid_from": "2026-05-12" if kind == "current" else "2026-04-01",
        "valid_until": None if kind == "current" else "2026-05-11",
        "aliases": concept.aliases if kind == "current" else [],
        "helper_query": concept.helper_query if kind == "current" else "",
        "guard_terms": [concept.guard] if kind == "current" else [],
        "negative_constraints": ["Reject stale, decoy, superseded, or wrong-entity evidence."],
        "provenance": {
            "artifact_path": f"blackbox/{concept.key}/{kind}.md",
            "record_key": item_id,
            "generator": "generate_blackbox_packet_cases.py",
        },
    }


def build_dataset(dataset: Path) -> None:
    corpus_path = dataset / "corpus" / "corpus_items.jsonl"
    corpus_path.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for concept in CONCEPTS:
        records.append(item_record(concept, "current"))
        if concept.stale_text:
            records.append(item_record(concept, "stale"))
        if concept.decoy_text:
            records.append(item_record(concept, "decoy"))
    with corpus_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    write_json(
        dataset / "metadata" / "dataset_manifest.json",
        {"dataset": "blackbox_packet_dataset", "items": len(records), "concepts": len(CONCEPTS)},
    )
    write_json(dataset / "eval" / "cases.json", {"cases": []})


def typo(value: str) -> str:
    if len(value) < 4:
        return value
    idx = max(1, len(value) // 2)
    return value[:idx] + value[idx + 1 :]


def make_case(idx: int, rng: random.Random, edge: bool, dataset: Path) -> dict[str, Any]:
    if not edge and rng.random() < 0.12:
        text = rng.choice(NO_CONTEXT_TEMPLATES)
        return {
            "id": f"bb_{idx:04d}_no_context",
            "dataset": portable_dataset_path(dataset),
            "category": "no_context",
            "edge_case": False,
            "query": text,
            "should_retrieve": False,
            "must_abstain": False,
            "required_source_ids": [],
            "forbidden_source_ids": [],
            "max_evidence_items": 0,
        }

    concept = rng.choice(CONCEPTS)
    alias = rng.choice(concept.aliases)
    template = rng.choice(EDGE_MUTATIONS if edge else NORMAL_TEMPLATES)
    query = template.format(alias=alias, typo=typo(alias))
    forbidden = []
    if concept.stale_text:
        forbidden.append(f"bb_{concept.key}_stale")
    if concept.decoy_text:
        forbidden.append(f"bb_{concept.key}_decoy")
    return {
        "id": f"bb_{idx:04d}_{'edge' if edge else 'normal'}_{concept.key}",
        "dataset": portable_dataset_path(dataset),
        "category": "edge" if edge else "normal",
        "edge_case": edge,
        "query": query,
        "should_retrieve": True,
        "must_abstain": False,
        "required_source_ids": [f"bb_{concept.key}_current"],
        "forbidden_source_ids": forbidden,
        "max_evidence_items": 2,
    }


def generate_cases(count: int, edge_ratio: float, edge_only: bool, dataset: Path, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    cases = []
    for idx in range(1, count + 1):
        edge = edge_only or rng.random() < edge_ratio
        cases.append(make_case(idx, rng, edge, dataset))
    return cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate black-box D-ACCA packet eval cases.")
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--edge-ratio", type=float, default=0.30)
    parser.add_argument("--edge-only", action="store_true")
    parser.add_argument("--seed", type=int, default=4242)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--cases-out", type=Path, default=DEFAULT_CASES)
    args = parser.parse_args(argv)

    dataset = args.dataset if args.dataset.is_absolute() else (ROOT / args.dataset)
    cases_out = args.cases_out if args.cases_out.is_absolute() else (ROOT / args.cases_out)
    build_dataset(dataset)
    cases = generate_cases(args.count, args.edge_ratio, args.edge_only, dataset, args.seed)
    edge_count = sum(1 for case in cases if case["edge_case"])
    payload = {
        "schema_version": "d_acca.blackbox_packet_cases.v0.1",
        "description": "Black-box user/agent input to expected context evidence behavior.",
        "dataset": portable_dataset_path(dataset),
        "count": len(cases),
        "edge_cases": edge_count,
        "edge_ratio": round(edge_count / len(cases), 4) if cases else 0.0,
        "cases": cases,
    }
    write_json(cases_out, payload)
    print(json.dumps({k: payload[k] for k in ["count", "edge_cases", "edge_ratio", "dataset"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
