from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from mome_moce_harness import (
        MoMEMoCERouter,
        RouteResult,
        load_corpus,
        validate_route_artifacts,
        write_artifact_pair,
    )
except ModuleNotFoundError:
    from scripts.mome_moce_harness import (
        MoMEMoCERouter,
        RouteResult,
        load_corpus,
        validate_route_artifacts,
        write_artifact_pair,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "eval" / "librarian_harness_cases.json"
DEFAULT_OUT = ROOT / "out" / "librarian_advisor_harness"
DEFAULT_OPENCODE_GO_BASE_URL = "http://127.0.0.1:14531/v1"
DEFAULT_OPENCODE_GO_MODEL = "deepseek-v4-flash"
DEFAULT_MODEL_MAX_OUTPUT_TOKENS = 3000
SPEC_DD_ACCEPTED_QUERY_LIMIT = 1
VALID_ESCALATION_MODES = {"hot_path", "parallel_advisory", "blocking_escalation"}


CATALOG_ENTITY_ALIASES: dict[str, list[str]] = {
    "recall": ["recall", "recall cloud", "hosted sync", "recall board"],
    "signal": ["signal"],
    "nebula": ["nebula"],
    "sandbox": ["sandbox", "sandbox_workspace", "poke around", "write wherever", "write anywhere", "permissions"],
    "hot-session": ["hot-session", "hot session", "cache_prompt", "static prefix", "prefix footgun", "cache footgun"],
    "ivy": ["ivy"],
    "qwen": ["qwen"],
    "mome": ["mome"],
    "moce": ["moce"],
    "acca": ["acca"],
}

CATALOG_ENTITY_DISPLAY: dict[str, str] = {
    "recall": "Recall Cloud",
    "signal": "Signal",
    "nebula": "Nebula",
    "sandbox": "sandbox_workspace agent tool sandbox",
    "hot-session": "hot-session cache reuse static prefix",
    "ivy": "IVY",
    "qwen": "Qwen",
    "mome": "MoME",
    "moce": "MoCE",
    "acca": "ACCA",
}

PHRASE_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "for",
    "from",
    "how",
    "not",
    "or",
    "the",
    "this",
    "was",
    "what",
    "where",
    "with",
}


@dataclass(slots=True)
class LibrarianAdvice:
    strategy: str
    escalation_mode: str
    intent_summary: str
    queries: list[str]
    entity_terms: list[str]
    negative_constraints: list[str]
    side_tracks: list[str]
    rationale: str
    latency_ms: float


@dataclass(slots=True)
class ModelAdvisorConfig:
    model: str = DEFAULT_OPENCODE_GO_MODEL
    base_url: str = DEFAULT_OPENCODE_GO_BASE_URL
    timeout_seconds: float = 30.0
    max_output_tokens: int = DEFAULT_MODEL_MAX_OUTPUT_TOKENS
    retries: int = 1
    catalog_limit: int = 18
    catalog_text_chars: int = 160
    use_tool_call: bool = False
    api_key_env: str = "OPENCODE_GO_PROXY_KEY"
    fallback: str = "rule"


@dataclass(slots=True)
class DraftQuery:
    head: str
    query: str
    priority: float


def resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return (ROOT / path).resolve()


def read_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases", payload if isinstance(payload, list) else [])
    if not isinstance(cases, list):
        raise ValueError("librarian cases must be a list or an object with a cases list")
    return [dict(case) for case in cases]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def norm_text(value: str) -> str:
    return " ".join(str(value).lower().split())


def unique(values: list[str], *, limit: int | None = None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = str(value).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
        if limit is not None and len(out) >= limit:
            break
    return out


def coerce_str_list(value: Any, *, limit: int = 6, lowercase: bool = False) -> list[str]:
    if isinstance(value, list):
        raw_values = value
    elif isinstance(value, str) and value.strip():
        raw_values = [value]
    else:
        raw_values = []
    normalized = []
    for item in raw_values:
        text = str(item).strip()
        if not text:
            continue
        normalized.append(text.lower() if lowercase else text)
    return unique(normalized, limit=limit)


def fixture_advice(case: dict[str, Any]) -> LibrarianAdvice:
    started = time.perf_counter()
    payload = dict(case.get("librarian") or {})
    queries = [str(item) for item in payload.get("queries", []) if str(item).strip()]
    if not queries:
        queries = [str(case["query"])]
    elapsed = (time.perf_counter() - started) * 1000
    return LibrarianAdvice(
        strategy="fixture",
        escalation_mode=str(payload.get("escalation_mode") or payload.get("mode") or "parallel_advisory"),
        intent_summary=str(payload.get("intent_summary") or payload.get("intent") or case["query"]),
        queries=unique(queries),
        entity_terms=unique([str(item).lower() for item in payload.get("entity_terms", [])]),
        negative_constraints=unique([str(item) for item in payload.get("negative_constraints", [])]),
        side_tracks=unique([str(item) for item in payload.get("side_tracks", [])]),
        rationale=str(payload.get("rationale") or "Fixture advice simulates a sub-frontier librarian output."),
        latency_ms=round(elapsed, 3),
    )


def strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = strip_json_fence(text)
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise
        payload = json.loads(stripped[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("model librarian output must be a JSON object")
    return payload


def extract_response_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    chunks: list[str] = []
    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            arguments = item.get("arguments")
            if item.get("type") == "function_call" and isinstance(arguments, str) and arguments.strip():
                chunks.append(arguments)
            content = item.get("content")
            if isinstance(content, str):
                chunks.append(content)
            elif isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    for key in ("text", "output_text", "content"):
                        value = part.get(key)
                        if isinstance(value, str) and value.strip():
                            chunks.append(value)
                            break

    choices = payload.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    chunks.append(content)
                tool_calls = message.get("tool_calls")
                if isinstance(tool_calls, list):
                    for tool_call in tool_calls:
                        arguments = (
                            tool_call.get("function", {}).get("arguments")
                            if isinstance(tool_call, dict) and isinstance(tool_call.get("function"), dict)
                            else None
                        )
                        if isinstance(arguments, str) and arguments.strip():
                            chunks.append(arguments)
            text = choice.get("text")
            if isinstance(text, str) and text.strip():
                chunks.append(text)

    text = "\n".join(chunks).strip()
    if not text:
        raise ValueError("model response did not contain assistant text")
    return text


def parse_model_librarian_payload(payload: dict[str, Any], case: dict[str, Any], latency_ms: float, strategy: str) -> LibrarianAdvice:
    query = str(case["query"])
    mode = str(payload.get("escalation_mode") or "parallel_advisory").strip()
    if mode not in VALID_ESCALATION_MODES:
        mode = "parallel_advisory"
    queries = [query for query in coerce_str_list(payload.get("queries"), limit=4) if is_local_catalog_query(query)]
    if not queries:
        queries = rule_advice(case).queries
    advice = LibrarianAdvice(
        strategy=strategy,
        escalation_mode=mode,
        intent_summary=str(payload.get("intent_summary") or payload.get("intent") or query).strip(),
        queries=queries,
        entity_terms=normalize_model_entity_terms(coerce_str_list(payload.get("entity_terms"), limit=6, lowercase=True)),
        negative_constraints=coerce_str_list(payload.get("negative_constraints"), limit=6),
        side_tracks=coerce_str_list(payload.get("side_tracks"), limit=6),
        rationale=str(payload.get("rationale") or "Model librarian emitted structured query advice.").strip(),
        latency_ms=round(latency_ms, 3),
    )
    return apply_model_advice_guards(case, advice)


def normalize_model_entity_terms(terms: list[str]) -> list[str]:
    normalized: list[str] = []
    canonical_map = [
        ("recall", "recall"),
        ("signal", "signal"),
        ("nebula", "nebula"),
        ("hot-session", "hot-session"),
        ("hot session", "hot-session"),
        ("sandbox", "sandbox"),
        ("sandbox_workspace", "sandbox"),
        ("qwen", "qwen"),
        ("mome", "mome"),
        ("moce", "moce"),
        ("acca", "acca"),
        ("ivy", "ivy"),
    ]
    generic = {"agent", "agents", "tool", "tools", "policy", "phase", "current", "latest", "record"}
    for term in terms:
        lower = norm_text(term)
        matched = False
        for needle, canonical in canonical_map:
            if needle in lower:
                normalized.append(canonical)
                matched = True
                break
        if matched:
            continue
        if len(lower.split()) == 1 and lower not in generic:
            normalized.append(lower)
    normalized = unique(normalized, limit=6)
    if len(normalized) > 1 and "ivy" in normalized:
        normalized = [term for term in normalized if term != "ivy"]
    return normalized


def apply_model_advice_guards(case: dict[str, Any], advice: LibrarianAdvice) -> LibrarianAdvice:
    blob = norm_text(
        " ".join(
            [
                str(case.get("query", "")),
                *advice.queries,
                *advice.negative_constraints,
                *advice.side_tracks,
            ]
        )
    )
    risk_markers = {
        "latest",
        "current",
        "now",
        "right now",
        "price",
        "pricing",
        "charging",
        "ga",
        "public",
        "release",
        "safety",
        "sandbox",
        "secret",
        "private",
        "stale",
        "conflict",
        "contradict",
        "unsupported",
        "abstain",
    }
    if any(marker in blob for marker in risk_markers):
        advice.escalation_mode = "blocking_escalation"

    if not advice.entity_terms:
        inferred = []
        for entity in ["recall", "signal", "nebula", "ivy", "qwen", "mome", "moce", "acca", "sandbox", "hot-session"]:
            if entity in blob:
                inferred.append(entity)
        advice.entity_terms = unique(inferred, limit=6)
    return advice


def is_local_catalog_query(query: str) -> bool:
    lower = norm_text(query)
    forbidden_patterns = [
        "select ",
        " where ",
        " order by ",
        "pricing_api",
        "recent_transactions",
        "transaction logs",
        "http://",
        "https://",
        "api endpoint",
        "external api",
        "database",
        "stale",
        "draft",
        "decoy",
        "reject",
        "false claim",
        "wrong claim",
    ]
    return not any(pattern in lower for pattern in forbidden_patterns)


def opencode_go_proxy_token(api_key_env: str) -> str | None:
    value = os.environ.get(api_key_env, "").strip()
    if value:
        return value
    codex_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    token_path = codex_home / "tmp" / "opencode-go-proxy.token"
    try:
        token = token_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return token or None


def call_opencode_go_responses(
    prompt: str,
    *,
    config: ModelAdvisorConfig,
) -> dict[str, Any]:
    url = config.base_url.rstrip("/") + "/responses"
    request_payload = {
        "model": config.model,
        "instructions": (
            "You are the D-ACCA librarian advisor. Return only valid JSON. "
            "Do not think step by step. Do not emit markdown or prose. "
            "Do not select evidence IDs. D-ACCA will reroute your query bundle and enforce admission."
        ),
        "input": prompt,
        "temperature": 0,
        "max_output_tokens": config.max_output_tokens,
        "store": False,
    }
    if config.use_tool_call:
        request_payload["tools"] = [
            {
                "type": "function",
                "name": "librarian_advice",
                "description": "Emit structured D-ACCA librarian routing advice.",
                "parameters": librarian_advice_schema(),
            }
        ]
        request_payload["tool_choice"] = {"type": "function", "function": {"name": "librarian_advice"}}
    headers = {"Content-Type": "application/json"}
    token = opencode_go_proxy_token(config.api_key_env)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        url,
        data=json.dumps(request_payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenCode Go proxy HTTP {error.code}: {body[:600]}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"OpenCode Go proxy request failed: {error.reason}") from error


def librarian_advice_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "escalation_mode": {"type": "string", "enum": sorted(VALID_ESCALATION_MODES)},
            "intent_summary": {"type": "string"},
            "queries": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 4},
            "entity_terms": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
            "negative_constraints": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
            "side_tracks": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
            "rationale": {"type": "string"},
        },
        "required": [
            "escalation_mode",
            "intent_summary",
            "queries",
            "entity_terms",
            "negative_constraints",
            "side_tracks",
            "rationale",
        ],
    }


def catalog_cards(router: MoMEMoCERouter, *, limit: int, text_chars: int) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for item in router.items:
        raw = item.raw
        if item.id.startswith("filler_") or "_support_" in item.id or "support" in item.tags:
            continue
        text = str(raw.get("text", "")).replace("\n", " ").strip()
        cards.append(
            {
                "id": item.id,
                "tags": item.tags[:6],
                "source_family": item.source_family,
                "authority": item.authority,
                "staleness": item.staleness,
                "conflicts_with": item.conflicts_with[:4],
                "text": text[:text_chars],
            }
        )
        if len(cards) >= limit:
            break
    return cards


def model_librarian_prompt(
    case: dict[str, Any],
    *,
    router: MoMEMoCERouter | None = None,
    config: ModelAdvisorConfig | None = None,
    retry: bool = False,
) -> str:
    case_view = {
        "id": str(case.get("id", "")),
        "query": str(case["query"]),
        "category": str(case.get("category", "")),
    }
    cfg = config or ModelAdvisorConfig()
    cards = catalog_cards(router, limit=cfg.catalog_limit, text_chars=cfg.catalog_text_chars) if router else []
    return "\n".join(
        [
            "Retry after invalid/empty output. Keep JSON compact." if retry else "",
            "D-ACCA librarian task. Return one JSON object only.",
            "Do not answer the user. Do not use SQL, APIs, web searches, or evidence IDs.",
            "Queries must be natural-language keyword searches over the local catalog cards.",
            "Do not put stale/draft/decoy/reject terms in queries; put those only in negative_constraints.",
            "Use catalog cards only to infer canonical terms and target entities.",
            "Return 1-4 D-ACCA search queries. Prefer exact product/policy/workflow terms from the catalog.",
            "If the target entity seems absent from catalog, query that exact entity plus authoritative/current/record terms and add an abstention constraint.",
            "entity_terms must contain only target entities that admitted evidence must mention.",
            "Escalation must be exactly one of: hot_path, parallel_advisory, blocking_escalation.",
            "Use blocking_escalation for current/latest, stale/current conflict, safety/private, contradiction, or unsupported-answer risk.",
            "JSON fields: escalation_mode, intent_summary, queries, entity_terms, negative_constraints, side_tracks, rationale.",
            "Keep each string short; no explanations outside JSON.",
            f"Case: {json.dumps(case_view, ensure_ascii=False, separators=(',', ':'))}",
            f"Catalog cards: {json.dumps(cards, ensure_ascii=False, separators=(',', ':'))}",
        ]
    )


def model_opencode_go_advice(
    case: dict[str, Any],
    config: ModelAdvisorConfig,
    *,
    router: MoMEMoCERouter | None = None,
) -> LibrarianAdvice:
    started = time.perf_counter()
    strategy = f"model-opencode-go:{config.model}"
    last_error: Exception | None = None
    try:
        for attempt in range(max(0, config.retries) + 1):
            response_payload = call_opencode_go_responses(
                model_librarian_prompt(case, router=router, config=config, retry=attempt > 0),
                config=config,
            )
            try:
                text = extract_response_text(response_payload)
                model_payload = extract_json_object(text)
                elapsed = (time.perf_counter() - started) * 1000
                advice = parse_model_librarian_payload(model_payload, case, elapsed, strategy)
                if attempt:
                    advice.rationale = f"Model librarian succeeded after {attempt} retry. {advice.rationale}"
                return advice
            except Exception as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise ValueError("model librarian did not produce advice")
    except Exception as exc:
        if config.fallback == "error":
            raise
        fallback = rule_advice(case)
        fallback.strategy = f"{strategy}:fallback_rule"
        fallback.rationale = (
            f"Model librarian failed with {type(exc).__name__}; deterministic rule librarian was used. "
            f"Failure detail: {str(exc)[:240]}"
        )
        fallback.latency_ms = round((time.perf_counter() - started) * 1000, 3)
        return fallback


def wait_for_proxy_health(base_url: str, timeout_seconds: float = 8.0) -> None:
    health_url = base_url.rstrip("/")
    if health_url.endswith("/v1"):
        health_url = health_url[:-3]
    health_url += "/health"
    deadline = time.perf_counter() + timeout_seconds
    last_error: Exception | None = None
    while time.perf_counter() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=1.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("ok"):
                return
        except Exception as exc:
            last_error = exc
        time.sleep(0.2)
    detail = f": {last_error}" if last_error else ""
    raise RuntimeError(f"OpenCode Go proxy did not become healthy at {health_url}{detail}")


def start_opencode_go_proxy(model: str, base_url: str) -> None:
    command = ["codex-go", "proxy", "start", "--model", model, "--json"]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=30)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"codex-go proxy start failed: {detail[:800]}")
    wait_for_proxy_health(base_url)


def rule_advice(case: dict[str, Any]) -> LibrarianAdvice:
    started = time.perf_counter()
    query = str(case["query"])
    lower = norm_text(query)
    queries = [query]
    negative: list[str] = []
    side_tracks: list[str] = []
    entity_terms: list[str] = []
    reasons: list[str] = []
    escalation = "hot_path"

    for entity in ["recall", "signal", "nebula", "ivy", "qwen", "mome", "moce", "acca"]:
        if entity in lower:
            entity_terms.append(entity)

    if any(term in lower for term in ["latest", "current", "now", "right now", "price", "pricing", "charge", "charging", "production price"]):
        queries.append(f"current authoritative production pricing evidence for {query}")
        negative.append("Reject stale pricing drafts and identity notes that do not state a price.")
        side_tracks.append("Check whether answerability should abstain when no current price record exists.")
        reasons.append("freshness-sensitive pricing query")
        escalation = "blocking_escalation"

    if any(term in lower for term in ["ga", "release", "status", "production release"]):
        queries.append(f"current production release status GA beta evidence for {query}")
        negative.append("Reject stale GA claims if newer release status exists.")
        side_tracks.append("Look for stale/current release-status conflicts.")
        reasons.append("freshness-sensitive release query")
        escalation = "blocking_escalation"

    if any(term in lower for term in ["safety", "sandbox", "secret", "private", "shell", "network", "delete"]):
        queries.append(f"current safety policy sandbox permission evidence for {query}")
        negative.append("Do not admit secret-like or forbidden evidence into packet text.")
        side_tracks.append("Audit forbidden-hit and exposure-policy behavior.")
        reasons.append("safety-sensitive query")
        escalation = "blocking_escalation"

    if any(term in lower for term in ["stale", "conflict", "contradict", "supersede"]):
        queries.append(f"authority conflict supersession evidence for {query}")
        negative.append("Lower-authority stale evidence must not override current evidence.")
        side_tracks.append("Inspect conflict pairs in route proofs.")
        reasons.append("conflict-sensitive query")
        escalation = "blocking_escalation"

    if any(term in lower for term in ["what next", "what should", "how to", "why did", "vague"]):
        queries.append(f"developer intent evidence needs for {query}")
        side_tracks.append("Generate missing evidence questions for the next turn.")
        reasons.append("vague or planning-style query")
        if escalation == "hot_path":
            escalation = "parallel_advisory"

    elapsed = (time.perf_counter() - started) * 1000
    return LibrarianAdvice(
        strategy="rule",
        escalation_mode=escalation,
        intent_summary="; ".join(reasons) if reasons else "clear direct lookup",
        queries=unique(queries, limit=4),
        entity_terms=unique(entity_terms),
        negative_constraints=unique(negative),
        side_tracks=unique(side_tracks),
        rationale="Rule librarian compiled query variants from task risk markers.",
        latency_ms=round(elapsed, 3),
    )


def meaningful_query_phrases(query: str) -> list[str]:
    tokens = [
        token
        for token in norm_text(query.replace("-", " ")).split()
        if len(token) > 2 and token not in PHRASE_STOPWORDS
    ]
    phrases: list[str] = []
    for size in (3, 2):
        for idx in range(0, max(0, len(tokens) - size + 1)):
            phrase = " ".join(tokens[idx : idx + size])
            if phrase:
                phrases.append(phrase)
    return unique(phrases, limit=24)


def catalog_guard_terms_for_blob(blob: str) -> list[str]:
    lower = norm_text(blob.replace("_", " ").replace("-", " "))
    out: list[str] = []
    for guard, aliases in CATALOG_ENTITY_ALIASES.items():
        for alias in aliases:
            if norm_text(alias.replace("-", " ")) in lower:
                out.append(guard)
                break
    return unique(out)


def infer_catalog_guard_terms(router: MoMEMoCERouter | None, query: str) -> list[str]:
    lower = norm_text(query.replace("-", " "))
    out = catalog_guard_terms_for_blob(lower)
    if router is None or out:
        return out

    phrases = meaningful_query_phrases(query)
    for item in router.items:
        search = norm_text(
            " ".join(
                [
                    item.id,
                    item.search_text,
                    " ".join(item.tags),
                    json.dumps(item.provenance, sort_keys=True),
                ]
            ).replace("_", " ")
        )
        if any(phrase in search for phrase in phrases):
            out.extend(catalog_guard_terms_for_blob(search))
    return unique(out, limit=6)


def dd_rule_advice(case: dict[str, Any], router: MoMEMoCERouter | None) -> LibrarianAdvice:
    started = time.perf_counter()
    base = rule_advice(case)
    query = str(case["query"])
    lower = norm_text(query)
    guards = infer_catalog_guard_terms(router, query)
    queries = list(base.queries)
    negative = list(base.negative_constraints)
    side_tracks = list(base.side_tracks)
    reasons = [] if base.intent_summary == "clear direct lookup" else [base.intent_summary]
    escalation = base.escalation_mode

    pricing_like = any(
        term in lower
        for term in ["latest", "current", "now", "right now", "price", "pricing", "charge", "charging", "cost"]
    )
    release_like = any(term in lower for term in ["ga", "public", "release", "status", "beta"])
    safety_like = any(
        term in lower
        for term in ["safety", "sandbox", "secret", "private", "shell", "network", "delete", "poke around", "write wherever"]
    )
    hot_cache_like = "hot-session" in guards or (
        "cache" in lower and any(term in lower for term in ["hot", "prefix", "footgun", "static"])
    )

    if pricing_like:
        target_guards = [guard for guard in guards if guard not in {"sandbox", "hot-session", "ivy", "mome", "moce", "acca"}]
        if not target_guards and "hosted sync" in lower:
            target_guards = ["recall"]
        for guard in target_guards or guards:
            display = CATALOG_ENTITY_DISPLAY.get(guard, guard)
            queries.append(f"{display} current pricing")
            queries.append(f"{display} production price current")
        negative.append("Reject stale pricing drafts and identity notes that do not state a price.")
        side_tracks.append("Abstain when the target entity has no authoritative current price record.")
        reasons.append("catalog-aware freshness pricing expansion")
        escalation = "blocking_escalation"

    if release_like and "signal" in guards:
        queries.append("Signal current release status production status internal beta public GA")
        negative.append("Reject stale GA claims if a newer release status exists.")
        side_tracks.append("Inspect stale/current release-status conflicts.")
        reasons.append("catalog-aware release-status expansion")
        escalation = "blocking_escalation"

    if safety_like or "sandbox" in guards:
        queries.append("sandbox_workspace read write sandbox_workspace/out agent tool sandbox paths")
        queries.append("Phase 1 agent tools no shell no network no delete")
        negative.append("Reject stale write-anywhere notes.")
        side_tracks.append("Audit safety-policy exposure before admitting evidence.")
        reasons.append("catalog-aware sandbox safety expansion")
        escalation = "blocking_escalation"
        if "sandbox" not in guards:
            guards.append("sandbox")

    if hot_cache_like:
        queries.append(
            "hot-session cache reuse static prefix byte-identical timestamps volatile data before prefix destroy cache shape"
        )
        negative.append("Reject timestamp-is-ok decoys and stale prompt_ms threshold notes.")
        side_tracks.append("Check whether the hot-session rule should become durable runbook memory.")
        reasons.append("catalog-aware hot-cache expansion")
        if escalation == "hot_path":
            escalation = "parallel_advisory"
        if "hot-session" not in guards:
            guards.append("hot-session")

    sanitized_queries = [candidate for candidate in queries if is_local_catalog_query(candidate)]
    elapsed = (time.perf_counter() - started) * 1000
    return LibrarianAdvice(
        strategy="dd-rule",
        escalation_mode=escalation,
        intent_summary="; ".join(unique(reasons)) if reasons else base.intent_summary,
        queries=unique(sanitized_queries, limit=4),
        entity_terms=unique(normalize_model_entity_terms(base.entity_terms + guards), limit=6),
        negative_constraints=unique(negative, limit=6),
        side_tracks=unique(side_tracks, limit=6),
        rationale="DD-rule compiled deterministic catalog advice distilled from DeepSeek librarian runs.",
        latency_ms=round(elapsed, 3),
    )


def speculative_draft_queries(case: dict[str, Any], router: MoMEMoCERouter | None) -> tuple[list[DraftQuery], list[str], str]:
    query = str(case["query"])
    lower = norm_text(query)
    guards = infer_catalog_guard_terms(router, query)
    draft: list[DraftQuery] = [DraftQuery("original", query, 0.25)]

    dd = dd_rule_advice(case, router)
    for idx, candidate in enumerate(dd.queries):
        draft.append(DraftQuery("dd_rule", candidate, 0.9 - idx * 0.05))

    pricing_like = any(
        term in lower
        for term in ["latest", "current", "now", "right now", "price", "pricing", "charge", "charging", "cost"]
    )
    release_like = any(term in lower for term in ["ga", "public", "release", "status", "beta"])
    safety_like = any(
        term in lower
        for term in ["safety", "sandbox", "secret", "private", "shell", "network", "delete", "poke around", "write wherever"]
    )
    hot_cache_like = "hot-session" in guards or (
        "cache" in lower and any(term in lower for term in ["hot", "prefix", "footgun", "static"])
    )

    for guard in guards:
        display = CATALOG_ENTITY_DISPLAY.get(guard, guard)
        draft.append(DraftQuery("entity_head", f"{display} authoritative current record", 0.75))
        if pricing_like:
            draft.append(DraftQuery("pricing_head", f"{display} current pricing production price", 0.95))
        if release_like:
            draft.append(DraftQuery("release_head", f"{display} current release status production status public GA", 0.95))

    if safety_like or "sandbox" in guards:
        draft.extend(
            [
                DraftQuery("safety_head", "sandbox_workspace read write sandbox_workspace/out agent tool sandbox paths", 0.98),
                DraftQuery("safety_head", "Phase 1 agent tools no shell no network no delete", 0.72),
            ]
        )
    if hot_cache_like:
        draft.append(
            DraftQuery(
                "cache_head",
                "hot-session cache reuse static prefix byte-identical timestamps volatile data before prefix destroy cache shape",
                0.98,
            )
        )

    if router is not None:
        phrases = meaningful_query_phrases(query)
        for item in router.items:
            search = norm_text(" ".join([item.id, item.search_text, " ".join(item.tags)]).replace("_", " "))
            if any(phrase in search for phrase in phrases):
                tag_query = " ".join(unique(item.tags + [item.source_family, item.staleness], limit=8))
                if tag_query:
                    draft.append(DraftQuery("corpus_phrase_head", tag_query, 0.62))

    mode = dd.escalation_mode
    return sorted(draft, key=lambda item: item.priority, reverse=True), unique(guards, limit=6), mode


def verifier_selected_ids(router: MoMEMoCERouter, result: RouteResult, entity_terms: list[str]) -> list[str]:
    selected: list[str] = []
    for item_id in result.selected_ids:
        item = router.items_by_id.get(item_id)
        if item is None:
            continue
        if entity_terms and not item_matches_intent(router, item_id, entity_terms):
            continue
        if item.authority == "decoy":
            continue
        if item.staleness == "stale":
            continue
        selected.append(item_id)
    return selected


def spec_dd_advice(case: dict[str, Any], router: MoMEMoCERouter | None) -> LibrarianAdvice:
    started = time.perf_counter()
    if router is None:
        fallback = dd_rule_advice(case, router)
        fallback.strategy = "spec-dd:fallback_dd_rule"
        return fallback

    draft, guards, mode = speculative_draft_queries(case, router)
    accepted: list[DraftQuery] = []
    accepted_seen: set[str] = set()
    rejected_count = 0
    for candidate in draft:
        if not is_local_catalog_query(candidate.query):
            rejected_count += 1
            continue
        result = router.route(candidate.query)
        selected = verifier_selected_ids(router, result, normalize_model_entity_terms(guards))
        if selected or (not accepted and result.decision == "no_context_needed" and guards):
            normalized_query = candidate.query.strip()
            if normalized_query and normalized_query not in accepted_seen:
                accepted.append(candidate)
                accepted_seen.add(normalized_query)
        else:
            rejected_count += 1
        if len(accepted) >= SPEC_DD_ACCEPTED_QUERY_LIMIT:
            break

    if not accepted:
        fallback = dd_rule_advice(case, router)
        fallback.strategy = "spec-dd:fallback_dd_rule"
        fallback.latency_ms = round((time.perf_counter() - started) * 1000, 3)
        return fallback

    head_counts: dict[str, int] = {}
    for candidate in accepted:
        head_counts[candidate.head] = head_counts.get(candidate.head, 0) + 1
    elapsed = (time.perf_counter() - started) * 1000
    return LibrarianAdvice(
        strategy="spec-dd",
        escalation_mode=mode,
        intent_summary="speculative deterministic draft verified by D-ACCA",
        queries=[candidate.query for candidate in accepted],
        entity_terms=normalize_model_entity_terms(guards),
        negative_constraints=dd_rule_advice(case, router).negative_constraints,
        side_tracks=[
            "Draft heads: " + ", ".join(f"{head}={count}" for head, count in sorted(head_counts.items())),
            f"Accepted draft query limit: {SPEC_DD_ACCEPTED_QUERY_LIMIT}",
            f"Rejected draft heads during verifier pass: {rejected_count}",
        ],
        rationale="Spec-DD mimics speculative decoding/MTP: deterministic multi-head draft, D-ACCA verifier acceptance.",
        latency_ms=round(elapsed, 3),
    )


def spec_dd_lazy_advice(case: dict[str, Any], router: MoMEMoCERouter | None) -> LibrarianAdvice:
    started = time.perf_counter()
    draft, guards, mode = speculative_draft_queries(case, router)
    accepted = next((candidate for candidate in draft if is_local_catalog_query(candidate.query)), None)
    if accepted is None:
        fallback = dd_rule_advice(case, router)
        fallback.strategy = "spec-dd-lazy:fallback_dd_rule"
        fallback.latency_ms = round((time.perf_counter() - started) * 1000, 3)
        return fallback

    elapsed = (time.perf_counter() - started) * 1000
    return LibrarianAdvice(
        strategy="spec-dd-lazy",
        escalation_mode=mode,
        intent_summary="lazy speculative deterministic draft; final D-ACCA route is the verifier",
        queries=[accepted.query],
        entity_terms=normalize_model_entity_terms(guards),
        negative_constraints=dd_rule_advice(case, router).negative_constraints,
        side_tracks=[
            f"Accepted draft head without internal route: {accepted.head}",
            "Verifier is deferred to the final D-ACCA bundle route.",
        ],
        rationale="Spec-DD-lazy mimics speculative draft-first execution without the pre-route verifier pass.",
        latency_ms=round(elapsed, 3),
    )


def build_advice(
    case: dict[str, Any],
    strategy: str,
    *,
    model_config: ModelAdvisorConfig | None = None,
    router: MoMEMoCERouter | None = None,
) -> LibrarianAdvice:
    if strategy == "fixture":
        return fixture_advice(case)
    if strategy == "rule":
        return rule_advice(case)
    if strategy == "dd-rule":
        return dd_rule_advice(case, router)
    if strategy == "spec-dd":
        return spec_dd_advice(case, router)
    if strategy == "spec-dd-lazy":
        return spec_dd_lazy_advice(case, router)
    if strategy == "model-opencode-go":
        return model_opencode_go_advice(case, model_config or ModelAdvisorConfig(), router=router)
    raise ValueError(f"unsupported librarian strategy: {strategy}")


def score_selection(case: dict[str, Any], selected_ids: list[str], decision: str, latency_ms: float) -> dict[str, Any]:
    selected = set(selected_ids)
    required = set(str(item) for item in case.get("required_source_ids", case.get("expected_required_ids", [])))
    forbidden = set(str(item) for item in case.get("forbidden_source_ids", case.get("forbidden_ids", [])))
    must_abstain = bool(case.get("must_abstain", False))
    should_retrieve = bool(case.get("should_retrieve", not must_abstain))
    max_items = int(case.get("max_evidence_items", max(len(required), 1) if required else 0))

    required_hits = sorted(required & selected)
    missing_required = sorted(required - selected)
    hit_forbidden = sorted(forbidden & selected)
    extra_selected = sorted(selected - required)
    compactness_pass = len(selected) <= max_items if max_items else len(selected) == 0

    if not should_retrieve:
        passed = not selected and decision == "no_context_needed"
    elif must_abstain:
        passed = not selected or decision in {"no_context_needed", "searched_no_authoritative_evidence"}
    elif required:
        passed = not missing_required and not hit_forbidden
    else:
        passed = not hit_forbidden
    passed = bool(passed and compactness_pass)

    recall = len(required_hits) / len(required) if required else (1.0 if not selected else 0.0)
    precision = len(required_hits) / len(selected) if selected else (1.0 if not required else 0.0)
    return {
        "passed": passed,
        "decision": decision,
        "selected_ids": selected_ids,
        "required_source_ids": sorted(required),
        "forbidden_source_ids": sorted(forbidden),
        "required_hits": required_hits,
        "missing_required": missing_required,
        "hit_forbidden": hit_forbidden,
        "extra_selected": extra_selected,
        "evidence_recall": round(recall, 4),
        "evidence_precision": round(precision, 4),
        "compactness_pass": compactness_pass,
        "latency_ms": round(latency_ms, 3),
        "max_evidence_items": max_items,
    }


def route_once(
    router: MoMEMoCERouter,
    query: str,
    *,
    case_id: str,
    artifact_dir: Path | None,
) -> tuple[RouteResult, list[str], dict[str, Any] | None]:
    result = router.route(query)
    result.route_proof["case_id"] = case_id
    result.frontier_packet["case_id"] = case_id
    errors = validate_route_artifacts(result, set(router.items_by_id), case_id=case_id)
    artifact_entry = write_artifact_pair(artifact_dir, case_id=case_id, result=result) if artifact_dir else None
    return result, errors, artifact_entry


def route_librarian_bundle(
    router: MoMEMoCERouter,
    advice: LibrarianAdvice,
    *,
    case_id: str,
    artifact_dir: Path | None,
    max_union_items: int,
) -> dict[str, Any]:
    selected: list[str] = []
    selected_seen: set[str] = set()
    route_rows: list[dict[str, Any]] = []
    artifact_errors: list[dict[str, Any]] = []
    artifact_entries: list[dict[str, Any]] = []
    intent_guard_rejections: list[dict[str, Any]] = []
    total_latency = advice.latency_ms
    final_decision = "no_context_needed"

    for idx, query in enumerate(advice.queries, start=1):
        route_id = f"{case_id}__librarian_{idx:02d}"
        result, errors, entry = route_once(router, query, case_id=route_id, artifact_dir=artifact_dir)
        total_latency += result.latency_ms
        if errors:
            artifact_errors.append({"case_id": route_id, "errors": errors})
        if entry:
            artifact_entries.append(entry)
        if result.selected_ids:
            final_decision = result.decision
        for item_id in result.selected_ids:
            if advice.entity_terms and not item_matches_intent(router, item_id, advice.entity_terms):
                intent_guard_rejections.append(
                    {
                        "item_id": item_id,
                        "query": query,
                        "required_entity_terms": advice.entity_terms,
                        "reason": "selected evidence did not match librarian intent entity terms",
                    }
                )
                continue
            if item_id not in selected_seen and len(selected) < max_union_items:
                selected_seen.add(item_id)
                selected.append(item_id)
        route_rows.append(
            {
                "query": query,
                "decision": result.decision,
                "selected_ids": result.selected_ids,
                "confidence": round(result.confidence, 4),
                "latency_ms": round(result.latency_ms, 3),
            }
        )

    return {
        "selected_ids": selected,
        "decision": final_decision if selected else "no_context_needed",
        "latency_ms": round(total_latency, 3),
        "routes": route_rows,
        "artifact_errors": artifact_errors,
        "artifact_entries": artifact_entries,
        "intent_guard_rejections": intent_guard_rejections,
    }


def item_matches_intent(router: MoMEMoCERouter, item_id: str, entity_terms: list[str]) -> bool:
    item = router.items_by_id.get(item_id)
    if item is None:
        return False
    raw = item.raw
    blob = norm_text(
        " ".join(
            [
                item.id,
                str(raw.get("text", "")),
                " ".join(str(tag) for tag in raw.get("tags", [])),
                json.dumps(raw.get("provenance", {}), sort_keys=True),
            ]
        )
    )
    return all(term.lower() in blob for term in entity_terms)


def router_for_dataset(
    cache: dict[Path, MoMEMoCERouter],
    dataset: Path,
    *,
    top_k: int,
    candidate_backend: str,
) -> MoMEMoCERouter:
    dataset = resolve_path(dataset)
    if dataset not in cache:
        cache[dataset] = MoMEMoCERouter(
            load_corpus(dataset),
            top_k=top_k,
            candidate_backend=candidate_backend,
            dataset_path=dataset,
        )
    return cache[dataset]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    direct = [row["direct_score"] for row in rows]
    librarian = [row["librarian_score"] for row in rows]
    direct_latency = [float(row["direct_score"]["latency_ms"]) for row in rows]
    librarian_latency = [float(row["librarian_score"]["latency_ms"]) for row in rows]
    helped = [row for row in rows if not row["direct_score"]["passed"] and row["librarian_score"]["passed"]]
    harmed = [row for row in rows if row["direct_score"]["passed"] and not row["librarian_score"]["passed"]]
    block_count = sum(1 for row in rows if row["advice"]["escalation_mode"] == "blocking_escalation")
    return {
        "cases": len(rows),
        "direct_passed": sum(1 for row in direct if row["passed"]),
        "librarian_passed": sum(1 for row in librarian if row["passed"]),
        "direct_quality": round(sum(1 for row in direct if row["passed"]) / len(rows), 4) if rows else 0.0,
        "librarian_quality": round(sum(1 for row in librarian if row["passed"]) / len(rows), 4) if rows else 0.0,
        "librarian_helped_cases": [row["case_id"] for row in helped],
        "librarian_harmed_cases": [row["case_id"] for row in harmed],
        "blocking_escalations": block_count,
        "direct_latency_ms_mean": round(statistics.fmean(direct_latency), 3) if direct_latency else 0.0,
        "librarian_latency_ms_mean": round(statistics.fmean(librarian_latency), 3) if librarian_latency else 0.0,
        "latency_delta_ms_mean": round(
            statistics.fmean([b - a for a, b in zip(direct_latency, librarian_latency)]), 3
        )
        if rows
        else 0.0,
        "forbidden_hits": {
            "direct": sum(len(row["hit_forbidden"]) for row in direct),
            "librarian": sum(len(row["hit_forbidden"]) for row in librarian),
        },
    }


def markdown_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    rows = [
        "# D-ACCA Librarian Advisor Harness",
        "",
        f"Created: {payload['created_at']}",
        "",
        "## Summary",
        "",
        "| metric | value |",
        "|---|---:|",
        f"| cases | {summary['cases']} |",
        f"| direct quality | {summary['direct_quality']:.4f} |",
        f"| librarian quality | {summary['librarian_quality']:.4f} |",
        f"| helped cases | {len(summary['librarian_helped_cases'])} |",
        f"| harmed cases | {len(summary['librarian_harmed_cases'])} |",
        f"| blocking escalations | {summary['blocking_escalations']} |",
        f"| direct mean latency ms | {summary['direct_latency_ms_mean']:.3f} |",
        f"| librarian mean latency ms | {summary['librarian_latency_ms_mean']:.3f} |",
        f"| mean latency delta ms | {summary['latency_delta_ms_mean']:.3f} |",
        "",
        "## Cases",
        "",
        "| case | mode | direct pass | librarian pass | direct selected | librarian selected |",
        "|---|---|---:|---:|---|---|",
    ]
    for row in payload["results"]:
        rows.append(
            "| {case} | {mode} | {direct} | {lib} | `{direct_ids}` | `{lib_ids}` |".format(
                case=row["case_id"],
                mode=row["advice"]["escalation_mode"],
                direct=row["direct_score"]["passed"],
                lib=row["librarian_score"]["passed"],
                direct_ids=", ".join(row["direct_score"]["selected_ids"]),
                lib_ids=", ".join(row["librarian_score"]["selected_ids"]),
            )
        )
    return "\n".join(rows) + "\n"


def run_harness(
    *,
    cases_path: Path,
    out_dir: Path,
    default_dataset: Path,
    strategy: str,
    candidate_backend: str,
    top_k: int,
    max_union_items: int,
    limit: int | None,
    write_artifacts: bool,
    model_config: ModelAdvisorConfig | None = None,
) -> dict[str, Any]:
    cases = read_cases(cases_path)
    if limit is not None:
        cases = cases[:limit]
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir = out_dir / "routing_artifacts" if write_artifacts else None
    routers: dict[Path, MoMEMoCERouter] = {}
    results: list[dict[str, Any]] = []

    for case in cases:
        case_id = str(case["id"])
        dataset = resolve_path(Path(str(case.get("dataset") or default_dataset)))
        router = router_for_dataset(routers, dataset, top_k=top_k, candidate_backend=candidate_backend)
        direct, direct_errors, direct_artifact = route_once(
            router,
            str(case["query"]),
            case_id=f"{case_id}__direct",
            artifact_dir=artifact_dir,
        )
        advice = build_advice(case, strategy, model_config=model_config, router=router)
        librarian = route_librarian_bundle(
            router,
            advice,
            case_id=case_id,
            artifact_dir=artifact_dir,
            max_union_items=max_union_items,
        )
        direct_score = score_selection(case, direct.selected_ids, direct.decision, direct.latency_ms)
        librarian_score = score_selection(
            case,
            librarian["selected_ids"],
            librarian["decision"],
            librarian["latency_ms"],
        )
        results.append(
            {
                "case_id": case_id,
                "dataset": str(dataset),
                "category": str(case.get("category", "")),
                "query": str(case["query"]),
                "advice": {
                    "strategy": advice.strategy,
                    "escalation_mode": advice.escalation_mode,
                    "intent_summary": advice.intent_summary,
                    "queries": advice.queries,
                    "entity_terms": advice.entity_terms,
                    "negative_constraints": advice.negative_constraints,
                    "side_tracks": advice.side_tracks,
                    "rationale": advice.rationale,
                    "latency_ms": advice.latency_ms,
                },
                "direct_score": direct_score,
                "librarian_score": librarian_score,
                "direct_route": {
                    "decision": direct.decision,
                    "confidence": round(direct.confidence, 4),
                    "artifact_errors": direct_errors,
                    "artifact_entry": direct_artifact,
                },
                "librarian_routes": librarian["routes"],
                "librarian_intent_guard_rejections": librarian["intent_guard_rejections"],
                "librarian_artifact_errors": librarian["artifact_errors"],
                "librarian_artifact_entries": librarian["artifact_entries"],
            }
        )

    payload = {
        "runner_version": "d_acca.librarian_advisor_harness.v0.1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "cases_path": str(cases_path),
        "default_dataset": str(resolve_path(default_dataset)),
        "strategy": strategy,
        "model_advisor": {
            "model": model_config.model,
            "base_url": model_config.base_url,
            "timeout_seconds": model_config.timeout_seconds,
            "max_output_tokens": model_config.max_output_tokens,
            "retries": model_config.retries,
            "catalog_limit": model_config.catalog_limit,
            "catalog_text_chars": model_config.catalog_text_chars,
            "use_tool_call": model_config.use_tool_call,
            "fallback": model_config.fallback,
        }
        if model_config and strategy == "model-opencode-go"
        else None,
        "candidate_backend": candidate_backend,
        "top_k": top_k,
        "max_union_items": max_union_items,
        "summary": summarize(results),
        "results": results,
    }
    write_json(out_dir / "librarian_harness_results.json", payload)
    write_json(out_dir / "librarian_harness_summary.json", payload["summary"])
    write_text(out_dir / "librarian_harness_report.md", markdown_report(payload))
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate a librarian advisor around deterministic D-ACCA routing.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--dataset", type=Path, default=Path("out/context_stress_ivy_real_v2"))
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--strategy",
        choices=["fixture", "rule", "dd-rule", "spec-dd", "spec-dd-lazy", "model-opencode-go"],
        default="fixture",
    )
    parser.add_argument("--candidate-backend", choices=["scan", "indexed", "rust"], default="indexed")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-union-items", type=int, default=3)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-artifacts", action="store_true")
    parser.add_argument("--model", default=DEFAULT_OPENCODE_GO_MODEL)
    parser.add_argument("--opencode-go-base-url", default=DEFAULT_OPENCODE_GO_BASE_URL)
    parser.add_argument("--model-timeout-seconds", type=float, default=30.0)
    parser.add_argument("--model-max-output-tokens", type=int, default=DEFAULT_MODEL_MAX_OUTPUT_TOKENS)
    parser.add_argument("--model-retries", type=int, default=1)
    parser.add_argument("--model-catalog-limit", type=int, default=18)
    parser.add_argument("--model-catalog-text-chars", type=int, default=160)
    parser.add_argument("--model-tool-call", action="store_true")
    parser.add_argument("--model-fallback", choices=["rule", "error"], default="rule")
    parser.add_argument("--start-proxy", action="store_true")
    args = parser.parse_args(argv)

    model_config = None
    if args.strategy == "model-opencode-go":
        model_config = ModelAdvisorConfig(
            model=args.model,
            base_url=args.opencode_go_base_url,
            timeout_seconds=args.model_timeout_seconds,
            max_output_tokens=args.model_max_output_tokens,
            retries=args.model_retries,
            catalog_limit=args.model_catalog_limit,
            catalog_text_chars=args.model_catalog_text_chars,
            use_tool_call=args.model_tool_call,
            fallback=args.model_fallback,
        )
        if args.start_proxy:
            start_opencode_go_proxy(model_config.model, model_config.base_url)

    payload = run_harness(
        cases_path=resolve_path(args.cases),
        out_dir=resolve_path(args.out),
        default_dataset=args.dataset,
        strategy=args.strategy,
        candidate_backend=args.candidate_backend,
        top_k=args.top_k,
        max_union_items=args.max_union_items,
        limit=args.limit,
        write_artifacts=not args.no_artifacts,
        model_config=model_config,
    )
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
