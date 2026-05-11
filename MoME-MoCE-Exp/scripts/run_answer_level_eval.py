from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from mome_moce_harness import MoMEMoCERouter, load_cases, load_corpus
    from run_baseline_comparison import top_bm25
except ModuleNotFoundError:
    from scripts.mome_moce_harness import MoMEMoCERouter, load_cases, load_corpus
    from scripts.run_baseline_comparison import top_bm25


ROOT = Path(__file__).resolve().parents[1]


def _short(text: str, limit: int = 260) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else compact[: limit - 3] + "..."


def answer_from_ids(query: str, evidence_ids: list[str], item_by_id: dict[str, Any]) -> dict[str, Any]:
    if not evidence_ids:
        return {
            "answer": "I do not have enough approved evidence to answer.",
            "citations": [],
            "abstained": True,
        }
    snippets = []
    for item_id in evidence_ids:
        item = item_by_id[item_id]
        snippets.append(f"[{item_id}] {_short(item.text)}")
    return {
        "answer": f"Using approved evidence for query: {query}\n" + "\n".join(snippets),
        "citations": evidence_ids,
        "abstained": False,
    }


def score_answer(case: dict[str, Any], selected_ids: list[str], answer: dict[str, Any], item_by_id: dict[str, Any]) -> dict[str, Any]:
    required = set(case.get("required_source_ids", []))
    forbidden = set(case.get("forbidden_source_ids", []))
    citations = set(answer.get("citations", []))
    selected = set(selected_ids)
    must_abstain = bool(case.get("must_abstain"))

    exposed_forbidden = sorted(forbidden & selected)
    cited_forbidden = sorted(forbidden & citations)
    missing_required = sorted(required - citations)
    stale_or_decoy_unrequested = []
    query = str(case.get("query", "")).lower()
    asks_false_or_stale = any(word in query for word in ["false", "decoy", "unsupported", "stale", "old", "superseded"])
    for item_id in selected_ids:
        item = item_by_id[item_id]
        if item_id in required:
            continue
        if (item.staleness in {"stale", "decoy"} or item.authority == "decoy") and not asks_false_or_stale:
            stale_or_decoy_unrequested.append(item_id)

    if must_abstain:
        passed = bool(answer.get("abstained")) and not selected_ids and not exposed_forbidden
    else:
        passed = (
            not answer.get("abstained")
            and required.issubset(citations)
            and not exposed_forbidden
            and not cited_forbidden
            and not stale_or_decoy_unrequested
        )

    failures = []
    if must_abstain and not answer.get("abstained"):
        failures.append("should_abstain")
    if not must_abstain and answer.get("abstained"):
        failures.append("unexpected_abstention")
    if missing_required:
        failures.append("missing_required_citation")
    if exposed_forbidden:
        failures.append("forbidden_exposed")
    if cited_forbidden:
        failures.append("forbidden_cited")
    if stale_or_decoy_unrequested:
        failures.append("stale_or_decoy_unrequested")

    return {
        "passed": passed,
        "failures": failures,
        "missing_required": missing_required,
        "exposed_forbidden": exposed_forbidden,
        "cited_forbidden": cited_forbidden,
        "stale_or_decoy_unrequested": sorted(stale_or_decoy_unrequested),
    }


def run_eval(dataset: Path, *, backend: str, naive_top_k: int, limit: int | None = None) -> dict[str, Any]:
    items = load_corpus(dataset)
    cases = load_cases(dataset)
    if limit is not None:
        cases = cases[:limit]
    item_by_id = {item.id: item for item in items}
    router = MoMEMoCERouter(items, candidate_backend=backend, dataset_path=dataset)

    modes = {
        "no_context": [],
        "naive_bm25": [],
        "d_acca": [],
    }
    rows = []
    for case in cases:
        query = case["query"]
        mode_selected = {
            "no_context": [],
            "naive_bm25": top_bm25(items, query, top_k=naive_top_k),
            "d_acca": router.route(query).selected_ids,
        }
        row = {"case_id": case["id"], "category": case["category"], "query": query, "modes": {}}
        for mode, selected_ids in mode_selected.items():
            answer = answer_from_ids(query, selected_ids, item_by_id)
            scored = score_answer(case, selected_ids, answer, item_by_id)
            result = {
                "selected_ids": selected_ids,
                "answer": answer,
                "score": scored,
            }
            row["modes"][mode] = result
            modes[mode].append(scored["passed"])
        rows.append(row)

    summary = {
        mode: {
            "passed": sum(1 for ok in values if ok),
            "cases": len(values),
            "quality": round(sum(1 for ok in values if ok) / len(values), 4) if values else 0.0,
        }
        for mode, values in modes.items()
    }
    return {
        "runner_version": "answer_level_eval.v0.1",
        "dataset": str(dataset),
        "backend": backend,
        "naive_top_k": naive_top_k,
        "summary": summary,
        "rows": rows,
    }


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# CP10 Answer-Level Eval",
        "",
        f"Dataset: `{payload['dataset']}`",
        f"Backend: `{payload['backend']}`",
        "",
        "| Mode | Passed | Cases | Quality |",
        "|---|---:|---:|---:|",
    ]
    for mode, summary in payload["summary"].items():
        lines.append(f"| `{mode}` | {summary['passed']} | {summary['cases']} | {summary['quality']} |")
    lines.extend(
        [
            "",
            "This evaluator is intentionally deterministic. It checks whether a model-facing answer can cite required evidence IDs, abstain when required, and avoid forbidden/stale/decoy exposure. It does not claim to be a human or LLM judge.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run CP10 deterministic answer-level eval over no-context, naive BM25, and D-ACCA packets.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "out" / "context_stress_ivy_real_v2")
    parser.add_argument("--backend", choices=["scan", "indexed", "rust"], default="indexed")
    parser.add_argument("--naive-top-k", type=int, default=5)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-json", type=Path, default=ROOT / "out" / "answer_level_eval.json")
    parser.add_argument("--output-md", type=Path, default=ROOT / "out" / "answer_level_eval.md")
    args = parser.parse_args(argv)

    dataset = args.dataset if args.dataset.is_absolute() else ROOT / args.dataset
    payload = run_eval(dataset, backend=args.backend, naive_top_k=args.naive_top_k, limit=args.limit)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_md.write_text(markdown(payload), encoding="utf-8")
    print(json.dumps({"output_json": str(args.output_json), "output_md": str(args.output_md), "summary": payload["summary"]}, indent=2))
    return 0 if payload["summary"]["d_acca"]["quality"] >= 0.9 else 1


if __name__ == "__main__":
    raise SystemExit(main())
