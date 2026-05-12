from __future__ import annotations

import argparse
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "out" / "real_replay_packet_dataset"
DEFAULT_CASES = ROOT / "out" / "real_replay_packet_eval" / "real_replay_cases_1000.json"
DEFAULT_SESSIONS_ROOT = Path.home() / ".codex" / "sessions"


@dataclass(frozen=True)
class ReplayConcept:
    key: str
    guard: str
    family: str
    current_text: str
    tags: list[str]
    helper_query: str
    aliases: list[str]
    match_terms: list[str]
    stale_text: str | None = None
    decoy_text: str | None = None


CONCEPTS = [
    ReplayConcept(
        "acca_identity",
        "acca",
        "doc_memory",
        "D-ACCA is a low-latency context and memory admission engine for agents. It selects, rejects, compacts, and explains evidence before a model answers.",
        ["acca", "d-acca", "context engine", "memory engine", "admission"],
        "D-ACCA context memory admission engine not search engine",
        ["what is acca", "search engine", "rag", "context system", "memory system", "context engine"],
        ["what have we actually made", "search engine", "rag", "memory and context", "context/memory", "acca actually"],
        decoy_text="Decoy claim: D-ACCA is only a normal search engine that returns textually similar documents.",
    ),
    ReplayConcept(
        "bm25_role",
        "bm25",
        "doc_memory",
        "BM25 remains useful as a cheap broad candidate generator, but it should not be the final context admission authority because it over-admits stale and forbidden evidence.",
        ["bm25", "candidate generator", "forbidden hits", "precision", "recall"],
        "BM25 candidate generator not final admission authority stale forbidden evidence",
        ["bm25", "naive bm25", "discard bm25", "retrieval primitive", "candidate generator", "bm25 precision"],
        ["bm25", "discard bm25", "naive", "precision", "retrieval primitive", "candidate generator"],
        decoy_text="Decoy claim: BM25 should be discarded entirely and never used in the D-ACCA stack.",
    ),
    ReplayConcept(
        "helper_lazy",
        "helper",
        "doc_memory",
        "Helper-lazy is a lightweight librarian path that uses learned aliases and helper metadata to draft one query while D-ACCA still verifies final evidence admission.",
        ["helper-lazy", "librarian", "aliases", "metadata", "draft query"],
        "helper-lazy learned alias metadata one query D-ACCA verifier",
        ["helper-lazy", "helper lazy", "helper librarian", "alias brain", "profile brain", "helper and lazy", "min max helper"],
        ["helper-lazy", "helper lazy", "librarian helping", "alias", "metadata", "profile", "helper and lazy"],
        decoy_text="Decoy claim: helper-lazy's synthetic score proves external real-world generalization without more tests.",
    ),
    ReplayConcept(
        "spec_dd_lazy",
        "spec",
        "benchmark_artifact",
        "Spec-DD-lazy is the current sub-millisecond speculative draft sidecar candidate: it drafts a query cheaply and lets final D-ACCA routing verify it.",
        ["spec-dd", "spec-dd-lazy", "speculative", "mtp", "draft", "verify"],
        "Spec-DD-lazy speculative draft sidecar final D-ACCA verifier sub millisecond",
        ["spec dd lazy", "spec decode", "mtp", "draft sidecar", "speculative", "sub ms", "min max latency", "lazy sidecar"],
        ["spec decode", "mtp", "spec-dd", "spec dd", "speculative", "draft", "lazy", "latency and quality"],
    ),
    ReplayConcept(
        "confidence_gate",
        "gate",
        "doc_memory",
        "Confidence Gate v1 should return accept, no_context, or escalate_librarian using deterministic features such as score margin, alias strength, stale conflict, forbidden risk, and no-context likelihood.",
        ["confidence gate", "early exit", "accept", "no_context", "escalate_librarian"],
        "confidence gate accept no_context escalate_librarian score margin stale conflict forbidden risk",
        ["confidence gate", "early exit", "when to deploy librarian", "activate librarian", "gated deterministic", "95% confidence"],
        ["confidence", "gate", "deploy the librarian", "activate the librarian", "early exit", "confidence answers", "confidence pass"],
    ),
    ReplayConcept(
        "distillation_loop",
        "distill",
        "doc_memory",
        "The distillation loop lets a slower librarian solve hard cases, then converts repeated wins into aliases, negative constraints, rules, and black-box tests for the fast deterministic path.",
        ["distillation", "learning", "aliases", "rules", "tests"],
        "librarian solves hard cases distill aliases negative constraints rules tests fast path",
        ["distillation loop", "learns user patterns", "brain that learns", "post deployment", "teach deterministic", "human brain", "sub second"],
        ["learns", "patterns", "distill", "post deployment", "brain", "user patterns", "future similar", "human brain"],
    ),
    ReplayConcept(
        "librarian_role",
        "librarian",
        "doc_memory",
        "The librarian is an advisory sidecar for special cases. It compiles intent, suggests query bundles, detects ambiguity, and proposes warnings, but D-ACCA remains the final admission authority.",
        ["librarian", "sidecar", "advisory", "intent compiler", "admission authority"],
        "librarian advisory sidecar intent compiler query bundle D-ACCA final admission authority",
        ["librarian", "library", "special cases", "advisory", "sub agent"],
        ["librarian", "library", "book", "special cases", "side track", "sub agent"],
    ),
    ReplayConcept(
        "deepseek_role",
        "deepseek",
        "doc_memory",
        "DeepSeek Flash is useful as a shadow or teacher librarian for hard intent cases, but prior live runs were too slow for every hot-path request.",
        ["deepseek", "flash", "teacher", "shadow", "latency"],
        "DeepSeek Flash shadow teacher librarian hard cases too slow hot path",
        ["deepseek", "deepseek flash", "v4 flash", "model librarian", "teacher model"],
        ["deepseek", "v4 flash", "flash", "hot path", "runtime", "teacher", "shadow"],
        decoy_text="Decoy claim: DeepSeek Flash should be called for every D-ACCA request on the hot path.",
    ),
    ReplayConcept(
        "blackbox_results",
        "blackbox",
        "benchmark_artifact",
        "The 1700-case packet was a synthetic black-box stress test: 1000 mixed cases plus 700 edge-only cases. It was more realistic than internal anchors, but not proof of external deployment.",
        ["black-box", "1700 cases", "synthetic", "edge", "real-world"],
        "1700 case black-box packet synthetic mixed edge not external deployment proof",
        ["1700 cases", "simulated environment", "real world oriented", "black box", "edge cases", "1000 test case packet", "700 edge"],
        ["1700", "simulated", "real world", "black box", "edge", "internal benchmark", "1000 test case", "test case packet"],
    ),
    ReplayConcept(
        "real_replay_testing",
        "replay",
        "doc_memory",
        "The next realism step is real conversation replay with metadata ablation and held-out aliases before adding more implementation that might overfit synthetic packets.",
        ["real replay", "metadata ablation", "held-out aliases", "codex logs", "opencode logs"],
        "real conversation replay metadata ablation held-out aliases Codex OpenCode logs",
        ["real world tests", "codex chatlogs", "opencode chatlogs", "metadata ablation", "held-out alias"],
        ["real world", "chatlogs", "codex logs", "opencode", "ablation", "held-out", "replay"],
    ),
    ReplayConcept(
        "signal_integration",
        "signal",
        "runbook",
        "Signal is the local push and reply layer: agents can send progress pings or blocking asks to a phone through a local daemon, Tailscale Serve, and Web Push.",
        ["signal", "phone", "push", "reply", "tailscale"],
        "Signal local push reply phone daemon Tailscale Web Push agent pings",
        ["signal", "signalcli", "phone ping", "pings via signal", "push reply", "ping as well", "notify phone"],
        ["signal", "signalcli", "phone", "ping", "notify", "tailscale", "pings"],
    ),
    ReplayConcept(
        "recall_board_integration",
        "recall",
        "doc_memory",
        "Recall Board is the visual second-brain surface: it exports editable Excalidraw boards as compact AI-readable graph and context JSON instead of screenshots.",
        ["recall board", "excalidraw", "second brain", "graph", "ai context"],
        "Recall Board Excalidraw visual second brain AI-readable graph context JSON",
        ["recall-board", "recall board", "excalidraw", "second brain", "visual memory"],
        ["recall", "recall-board", "excalidraw", "second brain", "dashboard", "board"],
    ),
    ReplayConcept(
        "startup_saas",
        "startup",
        "doc_memory",
        "The strongest SaaS wedge is context governance for AI agents: shadow recorder first, assisted injection second, and team memory governance later.",
        ["startup", "saas", "context governance", "shadow recorder", "assisted injection"],
        "SaaS context governance AI agents shadow recorder assisted injection team memory",
        ["startup", "saas", "revenue", "users", "product", "github stars", "basis of a SaaS", "real need", "get users", "product standpoint"],
        ["startup", "saas", "revenue", "users", "product", "commercial", "real need", "built and get users"],
    ),
    ReplayConcept(
        "codex_opencode_logs",
        "codex",
        "runbook",
        "Codex sessions are available under the local .codex sessions JSONL tree. OpenCode config is under .config/opencode, while desktop state may live in OpenCode WebView storage.",
        ["codex", "opencode", "logs", "sessions", "jsonl"],
        "Codex sessions .codex JSONL OpenCode .config opencode WebView storage logs",
        ["codex chatlogs", "opencode chatlogs", ".config/opencode", ".codex sessions", "jsonl", "opencode go", "codexgo", "codex plus", "openai key", "api key"],
        ["codex logs", "chatlogs", "opencode", ".config", ".codex", "sessions", "codexgo", "opencode go"],
    ),
    ReplayConcept(
        "worktree_branch",
        "worktree",
        "workflow_trace",
        "Current D-ACCA supercharge work is on the worktree branch codex/d-acca-dd-acca-librarian-supercharge under C:/ivy-worktrees/d-acca-dd-acca-librarian-supercharge.",
        ["worktree", "branch", "push", "merge", "codex/d-acca"],
        "worktree branch codex/d-acca-dd-acca-librarian-supercharge C:/ivy-worktrees",
        ["worktree", "main", "branch", "push commits", "merge", "pr", "non pushed commits", "milestone commit", "commits along the way"],
        ["worktree", "branch", "merge", "push", "pr", "main", "commits", "milestone"],
    ),
]


SLANG_MARKERS = {
    "bruh",
    "dawg",
    "aye",
    "hwo",
    "contunue",
    "misisng",
    "determnine",
    "frotnier",
    "determnistic",
    "g0oing",
    "mimmicking",
}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def portable_dataset_path(dataset: Path) -> str:
    try:
        return str(dataset.relative_to(ROOT))
    except ValueError:
        return str(dataset)


def norm(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").replace("-", " ").split())


def redact_text(text: str) -> str:
    text = re.sub(r"sk-[A-Za-z0-9_-]{12,}", "<api-key>", text)
    text = re.sub(r"sig_admin_[A-Za-z0-9_-]{8,}", "<signal-token>", text)
    text = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]{12,}", "Bearer <token>", text, flags=re.I)
    text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "<email>", text)
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<ip>", text)
    text = re.sub(r"https?://[^\s`'\"<>]+", "<url>", text)
    text = text.replace(str(Path.home()), "%USERPROFILE%")
    text = text.replace("C:\\Users\\arahe", "%USERPROFILE%")
    text = re.sub(r"\b[0-9a-f]{24,}\b", "<id>", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_content_text(content: Any) -> str:
    chunks: list[str] = []
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for part in content:
            if isinstance(part, str):
                chunks.append(part)
            elif isinstance(part, dict):
                for key in ("text", "input_text", "content"):
                    value = part.get(key)
                    if isinstance(value, str):
                        chunks.append(value)
                        break
    return "\n".join(chunks)


def extract_user_messages(sessions_root: Path, *, max_files: int = 80) -> list[dict[str, Any]]:
    if not sessions_root.exists():
        return []
    files = sorted(sessions_root.rglob("*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)[:max_files]
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            if event.get("type") != "response_item" or payload.get("type") != "message" or payload.get("role") != "user":
                continue
            text = extract_content_text(payload.get("content"))
            if not text.strip():
                continue
            if text.lstrip().startswith("<heartbeat") or "<automation_id>" in text:
                continue
            if "# AGENTS.md instructions" in text or "<environment_context>" in text:
                continue
            clean = redact_text(text)
            clean_lower = clean.lower()
            if clean_lower.startswith("<subagent_notification>"):
                continue
            if "you are not alone in the codebase" in clean_lower:
                continue
            if clean_lower.startswith("you are worker ") or clean_lower.startswith("you are gpt worker "):
                continue
            if "parallel research subagents" in clean_lower or "research track " in clean_lower:
                continue
            if len(clean) < 8:
                continue
            digest = norm(clean[:500])
            if digest in seen:
                continue
            seen.add(digest)
            rows.append(
                {
                    "text": clean,
                    "source_file": path.name,
                    "line_no": line_no,
                    "timestamp": event.get("timestamp", ""),
                }
            )
    return rows


def score_concept(text: str, concept: ReplayConcept) -> float:
    lower = norm(text)
    score = 0.0
    for term in concept.match_terms:
        term_norm = norm(term)
        if term_norm and term_norm in lower:
            score += 3.0 + min(2.0, len(term_norm.split()) * 0.25)
    for alias in concept.aliases:
        alias_norm = norm(alias)
        if alias_norm and alias_norm in lower:
            score += 2.0 + min(1.5, len(alias_norm.split()) * 0.2)
    for tag in concept.tags:
        tag_norm = norm(tag)
        if tag_norm and tag_norm in lower:
            score += 0.7
    return score


def classify_message(row: dict[str, Any]) -> list[tuple[ReplayConcept, float]]:
    scored = [(concept, score_concept(str(row["text"]), concept)) for concept in CONCEPTS]
    return [(concept, score) for concept, score in sorted(scored, key=lambda item: item[1], reverse=True) if score >= 2.0]


def clip_query(text: str, *, max_chars: int = 260) -> str:
    text = redact_text(text)
    text = text.strip("` ")
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return cut.rstrip(" ,.;:") + "..."


def typo_variant(text: str) -> str:
    replacements = [("context", "contex"), ("memory", "memry"), ("deterministic", "dterministic"), ("frontier", "frotnier")]
    lower = text.lower()
    for old, new in replacements:
        idx = lower.find(old)
        if idx >= 0:
            return text[:idx] + new + text[idx + len(old) :]
    words = text.split()
    if len(words) > 4:
        words[2] = words[2][:-1] if len(words[2]) > 4 else words[2]
    return " ".join(words)


def organic_variants(text: str, concept: ReplayConcept, rng: random.Random) -> list[tuple[str, str]]:
    base = clip_query(text)
    fragments = [
        base,
        f"Current-only context check: {base}",
        f"Agent needs the smallest safe packet for this real turn: {base}",
        f"Ignore stale/decoy notes and route this: {base}",
        f"bruh map this messy turn to the right memory: {base}",
        f"same thing as before but operationally: {rng.choice(concept.aliases)}?",
        f"{typo_variant(base)} -- current truth only",
    ]
    labels = ["raw", "current_only", "agent_packet", "stale_guard", "slang", "followup", "typo"]
    return [(label, query) for label, query in zip(labels, fragments) if query.strip()]


def item_record(concept: ReplayConcept, kind: str) -> dict[str, Any]:
    text = concept.current_text
    authority = "high"
    staleness = "current"
    safety_label = "normal"
    source_family = concept.family
    tags = list(concept.tags)
    aliases = list(concept.aliases)
    helper_query = concept.helper_query
    conflicts: list[str] = []
    if kind == "stale":
        text = concept.stale_text or f"Old stale note for {concept.key}."
        authority = "low"
        staleness = "stale"
        tags = [*tags, "stale"]
        aliases = []
        helper_query = ""
        conflicts = [f"rr_{concept.key}_current"]
    elif kind == "decoy":
        text = concept.decoy_text or f"Decoy claim for {concept.key}."
        authority = "decoy"
        staleness = "decoy"
        safety_label = "unsafe_decoy"
        source_family = "distractor"
        tags = [*tags, "decoy"]
        aliases = []
        helper_query = ""
        conflicts = [f"rr_{concept.key}_current"]
    else:
        if concept.stale_text:
            conflicts.append(f"rr_{concept.key}_stale")
        if concept.decoy_text:
            conflicts.append(f"rr_{concept.key}_decoy")
    return {
        "id": f"rr_{concept.key}_{kind}",
        "source_family": source_family,
        "authority": authority,
        "created_at": "2026-05-12" if kind == "current" else "2026-04-01",
        "valid_from": "2026-05-12" if kind == "current" else "2026-04-01",
        "valid_until": None if kind == "current" else "2026-05-11",
        "supersedes": [f"rr_{concept.key}_stale"] if kind == "current" and concept.stale_text else [],
        "tags": tags,
        "text": text,
        "provenance": {
            "artifact_path": f"real_replay/{concept.key}/{kind}.md",
            "record_key": f"rr_{concept.key}_{kind}",
            "generator": "generate_real_replay_packet_cases.py",
        },
        "staleness": staleness,
        "conflicts_with": conflicts,
        "safety_label": safety_label,
        "claim_type": "fact",
        "canonical_for": [concept.key] if kind == "current" else [],
        "exposure_policy": "frontier_ok" if kind == "current" else "contrastive_ok",
        "taint_labels": ["normal"],
        "aliases": aliases,
        "helper_query": helper_query,
        "guard_terms": [concept.guard],
        "negative_constraints": ["Reject stale, decoy, superseded, wrong-entity, or unsupported evidence."],
    }


def build_dataset(dataset: Path) -> None:
    records: list[dict[str, Any]] = []
    for concept in CONCEPTS:
        records.append(item_record(concept, "current"))
        if concept.stale_text:
            records.append(item_record(concept, "stale"))
        if concept.decoy_text:
            records.append(item_record(concept, "decoy"))
    corpus_path = dataset / "corpus" / "corpus_items.jsonl"
    corpus_path.parent.mkdir(parents=True, exist_ok=True)
    with corpus_path.open("w", encoding="utf-8", newline="\n") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    write_json(
        dataset / "metadata" / "dataset_manifest.json",
        {
            "dataset": "real_replay_packet_dataset",
            "items": len(records),
            "concepts": len(CONCEPTS),
            "raw_private_logs_committed": False,
        },
    )
    write_json(dataset / "eval" / "cases.json", {"cases": []})


def is_edge_query(query: str, variant_label: str) -> bool:
    lower = norm(query)
    return variant_label in {"slang", "followup", "typo"} or any(marker in lower for marker in SLANG_MARKERS) or len(query.split()) <= 5


def make_case(
    *,
    idx: int,
    source: dict[str, Any],
    concept: ReplayConcept,
    variant_label: str,
    query: str,
    dataset: Path,
) -> dict[str, Any]:
    forbidden = []
    if concept.stale_text:
        forbidden.append(f"rr_{concept.key}_stale")
    if concept.decoy_text:
        forbidden.append(f"rr_{concept.key}_decoy")
    return {
        "id": f"rr_{idx:04d}_{concept.key}_{variant_label}",
        "dataset": portable_dataset_path(dataset),
        "category": f"real_replay/{concept.key}",
        "edge_case": is_edge_query(query, variant_label),
        "query": query,
        "should_retrieve": True,
        "must_abstain": False,
        "required_source_ids": [f"rr_{concept.key}_current"],
        "forbidden_source_ids": forbidden,
        "max_evidence_items": 2,
        "source": {
            "kind": "codex_session_user_turn",
            "file": source.get("source_file"),
            "line_no": source.get("line_no"),
            "timestamp": source.get("timestamp"),
            "variation": variant_label,
            "raw_text_redacted": True,
        },
    }


def fallback_messages() -> list[dict[str, Any]]:
    rows = []
    for concept in CONCEPTS:
        rows.append(
            {
                "text": f"Realistic fallback turn about {concept.aliases[0]} and whether the agent should retrieve current context.",
                "source_file": "fallback",
                "line_no": 0,
                "timestamp": "",
            }
        )
    return rows


def generate_cases(
    *,
    sessions_root: Path,
    count: int,
    dataset: Path,
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rng = random.Random(seed)
    messages = extract_user_messages(sessions_root)
    matched: list[tuple[dict[str, Any], ReplayConcept, float]] = []
    for row in messages:
        concepts = classify_message(row)
        if concepts:
            concept, score = concepts[0]
            matched.append((row, concept, score))

    if not matched:
        for row in fallback_messages():
            concept, score = classify_message(row)[0]
            matched.append((row, concept, score))

    pool: list[tuple[dict[str, Any], ReplayConcept, str, str]] = []
    for row, concept, _score in matched:
        for label, query in organic_variants(str(row["text"]), concept, rng):
            pool.append((row, concept, label, query))

    rng.shuffle(pool)
    cases: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    attempts = 0
    while len(cases) < count and attempts < count * 20:
        attempts += 1
        row, concept, label, query = rng.choice(pool)
        key = (concept.key, norm(query))
        if key in seen and len(seen) < len(pool):
            continue
        seen.add(key)
        cases.append(make_case(idx=len(cases) + 1, source=row, concept=concept, variant_label=label, query=query, dataset=dataset))

    while len(cases) < count:
        row, concept, label, query = rng.choice(pool)
        repeated_query = f"{query} [replay fold {len(cases) + 1}]"
        cases.append(
            make_case(idx=len(cases) + 1, source=row, concept=concept, variant_label=label, query=repeated_query, dataset=dataset)
        )

    matched_counts: dict[str, int] = {}
    for _row, concept, _score in matched:
        matched_counts[concept.key] = matched_counts.get(concept.key, 0) + 1
    meta = {
        "sessions_root": str(sessions_root),
        "session_user_turns_seen": len(messages),
        "matched_user_turns": len(matched),
        "matched_concepts": dict(sorted(matched_counts.items())),
        "variation_bank": ["raw", "current_only", "agent_packet", "stale_guard", "slang", "followup", "typo"],
        "parameterized_variations": False,
        "raw_private_logs_committed": False,
    }
    return cases, meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate real Codex replay packet cases for D-ACCA variants.")
    parser.add_argument("--sessions-root", type=Path, default=DEFAULT_SESSIONS_ROOT)
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260512)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--cases-out", type=Path, default=DEFAULT_CASES)
    args = parser.parse_args(argv)

    dataset = args.dataset if args.dataset.is_absolute() else ROOT / args.dataset
    cases_out = args.cases_out if args.cases_out.is_absolute() else ROOT / args.cases_out
    build_dataset(dataset)
    cases, meta = generate_cases(sessions_root=args.sessions_root, count=args.count, dataset=dataset, seed=args.seed)
    edge_count = sum(1 for case in cases if case.get("edge_case"))
    payload = {
        "schema_version": "d_acca.real_replay_packet_cases.v0.1",
        "description": "Derived black-box packet cases from real Codex user turns with fixed organic variations.",
        "dataset": portable_dataset_path(dataset),
        "count": len(cases),
        "edge_cases": edge_count,
        "edge_ratio": round(edge_count / len(cases), 4) if cases else 0.0,
        "generation": meta,
        "cases": cases,
    }
    write_json(cases_out, payload)
    print(
        json.dumps(
            {
                "count": payload["count"],
                "edge_cases": payload["edge_cases"],
                "edge_ratio": payload["edge_ratio"],
                "matched_user_turns": meta["matched_user_turns"],
                "session_user_turns_seen": meta["session_user_turns_seen"],
                "dataset": payload["dataset"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
