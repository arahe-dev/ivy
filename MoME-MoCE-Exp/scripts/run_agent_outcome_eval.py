from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any

try:
    from mome_moce_harness import MoMEMoCERouter, load_corpus, norm
    from run_baseline_comparison import top_bm25
except ModuleNotFoundError:
    from scripts.mome_moce_harness import MoMEMoCERouter, load_corpus, norm
    from scripts.run_baseline_comparison import top_bm25


ROOT = Path(__file__).resolve().parents[1]


def load_agent_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


def simulated_agent_response(
    *,
    task: str,
    query: str,
    selected_ids: list[str],
    item_by_id: dict[str, Any],
) -> dict[str, Any]:
    if not selected_ids:
        return {
            "status": "abstained",
            "answer": "I do not have enough approved evidence to answer or act.",
            "citations": [],
            "used_context": False,
        }
    snippets = []
    terms = []
    for item_id in selected_ids:
        item = item_by_id[item_id]
        snippets.append(f"[{item_id}] {' '.join(item.text.split())}")
        terms.extend(str(item.text).lower().split())
    return {
        "status": "completed",
        "answer": f"Task: {task}\nQuery: {query}\n" + "\n".join(snippets),
        "citations": selected_ids,
        "used_context": True,
        "term_bag": sorted(set(terms)),
    }


def score_case(case: dict[str, Any], selected_ids: list[str], response: dict[str, Any], item_by_id: dict[str, Any]) -> dict[str, Any]:
    selected = set(selected_ids)
    citations = set(response.get("citations", []))
    required = set(case.get("required_source_ids", []))
    forbidden = set(case.get("forbidden_source_ids", []))
    must_abstain = bool(case.get("must_abstain", False))
    answer_text = norm(str(response.get("answer", "")))
    expected_terms = [norm(term) for term in case.get("expected_terms", [])]
    missing_terms = [term for term in expected_terms if term and term not in answer_text]
    missing_required = sorted(required - citations)
    forbidden_selected = sorted(forbidden & selected)
    forbidden_cited = sorted(forbidden & citations)
    stale_or_decoy_unrequested = []
    asks_false_or_stale = any(word in norm(case["query"]) for word in ["false", "decoy", "unsupported", "stale", "old", "superseded"])
    for item_id in selected_ids:
        item = item_by_id[item_id]
        if item_id in required:
            continue
        if (item.staleness in {"stale", "decoy"} or item.authority == "decoy") and not asks_false_or_stale:
            stale_or_decoy_unrequested.append(item_id)

    if must_abstain:
        passed = response.get("status") == "abstained" and not selected_ids
    else:
        passed = (
            response.get("status") == "completed"
            and not missing_required
            and not forbidden_selected
            and not forbidden_cited
            and not stale_or_decoy_unrequested
            and not missing_terms
        )
    failures = []
    if must_abstain and response.get("status") != "abstained":
        failures.append("expected_abstention")
    if not must_abstain and response.get("status") == "abstained":
        failures.append("unexpected_abstention")
    if missing_required:
        failures.append("missing_required_context")
    if missing_terms:
        failures.append("missing_expected_terms")
    if forbidden_selected or forbidden_cited:
        failures.append("forbidden_context")
    if stale_or_decoy_unrequested:
        failures.append("unrequested_stale_or_decoy")
    return {
        "passed": bool(passed),
        "failures": failures,
        "missing_required": missing_required,
        "missing_terms": missing_terms,
        "forbidden_selected": forbidden_selected,
        "forbidden_cited": forbidden_cited,
        "stale_or_decoy_unrequested": sorted(stale_or_decoy_unrequested),
    }


def run_eval(dataset: Path, cases_path: Path, *, backend: str = "indexed", naive_top_k: int = 5) -> dict[str, Any]:
    items = load_corpus(dataset)
    item_by_id = {item.id: item for item in items}
    cases = load_agent_cases(cases_path)
    router = MoMEMoCERouter(items, candidate_backend=backend, dataset_path=dataset)

    modes: dict[str, list[dict[str, Any]]] = {"no_context": [], "naive_bm25": [], "d_acca": []}
    rows = []
    for case in cases:
        selections = {
            "no_context": [],
            "naive_bm25": top_bm25(items, case["query"], top_k=naive_top_k),
            "d_acca": router.route(case["query"]).selected_ids,
        }
        row = {"case_id": case["id"], "task": case["task"], "query": case["query"], "modes": {}}
        for mode, selected_ids in selections.items():
            start = time.perf_counter()
            response = simulated_agent_response(task=case["task"], query=case["query"], selected_ids=selected_ids, item_by_id=item_by_id)
            latency_ms = (time.perf_counter() - start) * 1000
            score = score_case(case, selected_ids, response, item_by_id)
            result = {
                "selected_ids": selected_ids,
                "response": response,
                "score": score,
                "latency_ms": round(latency_ms, 4),
            }
            row["modes"][mode] = result
            modes[mode].append(result)
        rows.append(row)

    summary = {}
    for mode, results in modes.items():
        passed = sum(1 for result in results if result["score"]["passed"])
        selected_counts = [len(result["selected_ids"]) for result in results]
        summary[mode] = {
            "passed": passed,
            "cases": len(results),
            "quality": round(passed / len(results), 4) if results else 0.0,
            "avg_selected": round(statistics.fmean(selected_counts), 4) if selected_counts else 0.0,
            "forbidden_context_failures": sum(1 for result in results if "forbidden_context" in result["score"]["failures"]),
        }

    return {
        "runner_version": "cp21.agent_outcome_eval.v0.1",
        "dataset": str(dataset),
        "cases_path": str(cases_path),
        "backend": backend,
        "summary": summary,
        "rows": rows,
    }


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# CP21 Agent Outcome Eval",
        "",
        f"- Dataset: `{payload['dataset']}`",
        f"- Cases: `{payload['cases_path']}`",
        f"- Backend: `{payload['backend']}`",
        "",
        "| Mode | Passed | Cases | Quality | Avg Selected | Forbidden Failures |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for mode, summary in payload["summary"].items():
        lines.append(
            f"| `{mode}` | {summary['passed']} | {summary['cases']} | {summary['quality']:.4f} | {summary['avg_selected']:.4f} | {summary['forbidden_context_failures']} |"
        )
    lines.extend(
        [
            "",
            "This is a deterministic proxy for agent usefulness. It checks whether the agent turn would have enough cited context, whether abstention happens when required, and whether stale/forbidden evidence leaks into the simulated outcome.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CP21 deterministic agent-outcome proxy eval.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "out" / "context_stress_ivy_real_v3")
    parser.add_argument("--cases", type=Path, default=ROOT / "eval" / "agent_outcome_cases.json")
    parser.add_argument("--backend", choices=["scan", "indexed", "rust"], default="indexed")
    parser.add_argument("--naive-top-k", type=int, default=5)
    parser.add_argument("--output-json", type=Path, default=ROOT / "out" / "cp21_agent_outcome_eval.json")
    parser.add_argument("--output-md", type=Path, default=ROOT / "out" / "cp21_agent_outcome_eval.md")
    args = parser.parse_args(argv)

    dataset = args.dataset if args.dataset.is_absolute() else ROOT / args.dataset
    cases = args.cases if args.cases.is_absolute() else ROOT / args.cases
    payload = run_eval(dataset, cases, backend=args.backend, naive_top_k=args.naive_top_k)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_md.write_text(markdown(payload), encoding="utf-8")
    print(json.dumps({"output_json": str(args.output_json), "output_md": str(args.output_md), "summary": payload["summary"]}, indent=2))
    d_acca = payload["summary"]["d_acca"]
    return 0 if d_acca["quality"] >= 0.9 and d_acca["forbidden_context_failures"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
