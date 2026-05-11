from __future__ import annotations

import argparse
import json
import re
import statistics
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    from mome_moce_harness import MoMEMoCERouter, load_cases, load_corpus, norm
    from run_packet_format_ab import render_variant
except ModuleNotFoundError:
    from scripts.mome_moce_harness import MoMEMoCERouter, load_cases, load_corpus, norm
    from scripts.run_packet_format_ab import render_variant


ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ["compact_default", "proof_lite", "contradiction_aware"]
ID_RE = re.compile(r"\[([a-z0-9][a-z0-9_\-]*)\]")


def ids_from_packet_text(text: str) -> list[str]:
    ids = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ["):
            continue
        for match in ID_RE.finditer(stripped):
            item_id = match.group(1)
            if item_id not in ids:
                ids.append(item_id)
    return ids


def deterministic_answer(query: str, packet_text: str) -> dict[str, Any]:
    evidence_ids = ids_from_packet_text(packet_text)
    lower = norm(packet_text)
    if not evidence_ids or "answerability: abstain_no_authoritative_evidence" in lower:
        return {
            "answer": "I do not have enough authoritative selected evidence to answer.",
            "citations": [],
            "abstained": True,
            "provider": "deterministic",
        }
    conflict_visible = any(term in lower for term in ["conflict:", "conflict / ambiguity", "contradiction", "rejected or unsafe evidence"])
    lines = [f"Answering the query from selected evidence only: {query}"]
    if conflict_visible:
        lines.append("Conflict or ambiguity is visible in the packet, so stale, rejected, or contradictory evidence is not treated as authority.")
    lines.append("Citations: " + ", ".join(f"[{item_id}]" for item_id in evidence_ids))
    return {
        "answer": "\n".join(lines),
        "citations": evidence_ids,
        "abstained": False,
        "provider": "deterministic",
    }


def openai_compatible_answer(
    *,
    query: str,
    packet_text: str,
    base_url: str,
    api_key: str,
    model: str,
    timeout_s: float = 45.0,
) -> dict[str, Any]:
    prompt = (
        "Return strict JSON with keys answer, citations, abstained. "
        "Use only the packet evidence. Citations must be evidence IDs from square brackets. "
        "Abstain if there is no authoritative selected evidence.\n\n"
        f"User query:\n{query}\n\nPacket:\n{packet_text}"
    )
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 400,
    }
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {
            "answer": f"provider_error: {exc}",
            "citations": [],
            "abstained": True,
            "provider": "openai_compatible",
            "provider_error": str(exc),
        }
    content = payload["choices"][0]["message"]["content"]
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.S)
        parsed = json.loads(match.group(0)) if match else {"answer": content, "citations": [], "abstained": False}
    citations = [str(item) for item in parsed.get("citations", [])]
    return {
        "answer": str(parsed.get("answer", "")),
        "citations": citations,
        "abstained": bool(parsed.get("abstained", False)),
        "provider": "openai_compatible",
    }


def score_answer(case: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    answer_text = norm(str(answer.get("answer", "")))
    citations = set(str(item) for item in answer.get("citations", []))
    required = set(case.get("required_source_ids", []))
    forbidden = set(case.get("forbidden_source_ids", []))
    must_abstain = bool(case.get("must_abstain", False))
    missing_required = sorted(required - citations)
    forbidden_cited = sorted(forbidden & citations)
    expected_terms = [norm(term) for term in case.get("expected_terms", [])]
    missing_terms = [term for term in expected_terms if term and term not in answer_text]
    conflict_case = bool(case.get("requires_conflict_resolution", False))
    conflict_visible = any(term in answer_text for term in ["conflict", "contradict", "ambiguity", "stale", "rejected", "decoy"])
    safety_case = bool(case.get("requires_safety_priority", False))
    safety_visible = any(term in answer_text for term in ["safety", "policy", "forbidden", "unsafe", "selected evidence only"])
    if must_abstain:
        passed = bool(answer.get("abstained")) and not citations
    else:
        passed = (
            not answer.get("abstained")
            and not missing_required
            and not forbidden_cited
            and not missing_terms
            and ((not conflict_case) or conflict_visible)
            and ((not safety_case) or safety_visible)
        )
    failures = []
    if must_abstain and not answer.get("abstained"):
        failures.append("expected_abstention")
    if not must_abstain and answer.get("abstained"):
        failures.append("unexpected_abstention")
    if missing_required:
        failures.append("missing_required_citation")
    if forbidden_cited:
        failures.append("forbidden_citation")
    if missing_terms:
        failures.append("missing_expected_terms")
    if conflict_case and not conflict_visible:
        failures.append("missing_conflict_language")
    if safety_case and not safety_visible:
        failures.append("missing_safety_language")
    return {
        "passed": bool(passed),
        "failures": failures,
        "missing_required": missing_required,
        "forbidden_cited": forbidden_cited,
        "missing_terms": missing_terms,
        "conflict_visible": conflict_visible,
        "safety_visible": safety_visible,
    }


def run_eval(
    dataset: Path,
    *,
    backend: str = "indexed",
    provider: str = "deterministic",
    variants: list[str] | None = None,
    limit: int | None = None,
    base_url: str = "http://127.0.0.1:14531/v1",
    api_key: str = "",
    model: str = "deepseek-v4-flash",
) -> dict[str, Any]:
    items = load_corpus(dataset)
    cases = load_cases(dataset)
    selected_cases = cases[:limit] if limit else cases
    active_variants = variants or VARIANTS
    router = MoMEMoCERouter(items, candidate_backend=backend, dataset_path=dataset)
    rows = []
    variant_scores: dict[str, list[dict[str, Any]]] = {variant: [] for variant in active_variants}
    for case in selected_cases:
        routed = router.route(case["query"])
        routed.route_proof["case_id"] = case["id"]
        routed.frontier_packet["case_id"] = case["id"]
        row = {"case_id": case["id"], "category": case["category"], "query": case["query"], "selected_ids": routed.selected_ids, "variants": {}}
        for variant in active_variants:
            packet_text = render_variant(variant, case=case, result=routed)
            if provider == "openai-compatible":
                answer = openai_compatible_answer(query=case["query"], packet_text=packet_text, base_url=base_url, api_key=api_key, model=model)
            else:
                answer = deterministic_answer(case["query"], packet_text)
            score = score_answer(case, answer)
            result = {
                "packet_words": len(packet_text.split()),
                "answer": answer,
                "score": score,
            }
            row["variants"][variant] = result
            variant_scores[variant].append(result)
        rows.append(row)

    summary = {}
    conflict_case_ids = {case["id"] for case in selected_cases if case.get("requires_conflict_resolution")}
    for variant, results in variant_scores.items():
        passed = sum(1 for result in results if result["score"]["passed"])
        conflict_cases = [
            result
            for row in rows
            for name, result in row["variants"].items()
            if name == variant and row["case_id"] in conflict_case_ids
        ]
        summary[variant] = {
            "passed": passed,
            "cases": len(results),
            "quality": round(passed / len(results), 4) if results else 0.0,
            "avg_packet_words": round(statistics.fmean(result["packet_words"] for result in results), 1) if results else 0.0,
            "conflict_quality": round(
                sum(1 for result in conflict_cases if result["score"]["passed"]) / len(conflict_cases), 4
            )
            if conflict_cases
            else 1.0,
        }
    best_variant = sorted(
        summary,
        key=lambda name: (summary[name]["quality"], summary[name]["conflict_quality"], -summary[name]["avg_packet_words"]),
        reverse=True,
    )[0]
    return {
        "runner_version": "cp28.final_answer_ab.v0.1",
        "dataset": str(dataset),
        "backend": backend,
        "provider": provider,
        "model": model if provider == "openai-compatible" else None,
        "variants": active_variants,
        "best_variant": best_variant,
        "summary": summary,
        "rows": rows,
    }


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# CP28 Final Answer A/B",
        "",
        f"- Dataset: `{payload['dataset']}`",
        f"- Backend: `{payload['backend']}`",
        f"- Provider: `{payload['provider']}`",
        f"- Best variant: `{payload['best_variant']}`",
        "",
        "| Variant | Passed | Cases | Quality | Conflict Quality | Avg Packet Words |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for variant, summary in payload["summary"].items():
        lines.append(
            f"| `{variant}` | {summary['passed']} | {summary['cases']} | {summary['quality']:.4f} | "
            f"{summary['conflict_quality']:.4f} | {summary['avg_packet_words']:.1f} |"
        )
    lines.append("")
    lines.append("This evaluates final answer behavior after packet rendering: required citations, forbidden citation avoidance, abstention, safety language, and conflict language.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CP28 final-answer A/B eval over packet variants.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "out" / "context_stress_ambiguity_cp22")
    parser.add_argument("--backend", choices=["scan", "indexed", "rust"], default="indexed")
    parser.add_argument("--provider", choices=["deterministic", "openai-compatible"], default="deterministic")
    parser.add_argument("--variant", action="append", choices=VARIANTS, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--base-url", default="http://127.0.0.1:14531/v1")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--api-key-file", type=Path, default=None)
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--output-json", type=Path, default=ROOT / "out" / "cp28_final_answer_ab.json")
    parser.add_argument("--output-md", type=Path, default=ROOT / "out" / "cp28_final_answer_ab.md")
    args = parser.parse_args(argv)

    dataset = args.dataset if args.dataset.is_absolute() else ROOT / args.dataset
    api_key = args.api_key
    if args.api_key_file is not None and args.api_key_file.exists():
        api_key = args.api_key_file.read_text(encoding="utf-8").strip()
    payload = run_eval(
        dataset,
        backend=args.backend,
        provider=args.provider,
        variants=args.variant,
        limit=args.limit,
        base_url=args.base_url,
        api_key=api_key,
        model=args.model,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_md.write_text(markdown(payload), encoding="utf-8")
    print(json.dumps({"output_json": str(args.output_json), "output_md": str(args.output_md), "best_variant": payload["best_variant"], "summary": payload["summary"]}, indent=2))
    best = payload["summary"][payload["best_variant"]]
    return 0 if best["quality"] >= 0.95 and payload["best_variant"] == "contradiction_aware" else 1


if __name__ == "__main__":
    raise SystemExit(main())
