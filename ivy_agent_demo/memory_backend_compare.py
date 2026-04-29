from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from . import memory_backend
from .memory_backend import MemoryBackendResult, get_backend


DEFAULT_OUTPUT_ROOT = Path("C:/ivy/runs/memory_backend_compare")


@dataclass
class CompareCase:
    id: str
    category: str
    query: str
    expected_terms: list[str]


def load_cases(path: Path, category: str | None = None) -> list[CompareCase]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    cases = data.get("cases", data)
    if not isinstance(cases, list):
        raise ValueError("cases must be a list")
    out = []
    for case in cases:
        query = case.get("query") or case.get("task") or ""
        if "id" not in case:
            raise ValueError(f"case missing id")
        if category and case.get("category") != category:
            continue
        
        expected = case.get("expected_packet_terms") or case.get("expected_success_terms") or []
        
        out.append(
            CompareCase(
                id=case["id"],
                category=case.get("category", "unknown"),
                query=query,
                expected_terms=expected,
            )
        )
    return out


def build_packet_advisory(
    query: str, backend_name: str, policy: str | None, max_chars: int = 800
) -> MemoryBackendResult:
    backend = get_backend(backend_name)
    if backend_name == "ivy_native":
        result = backend.build_packet(query, policy, max_chars)
    else:
        result = backend.build_packet(query, policy, max_chars)
    return result


def evaluate_result(
    result: MemoryBackendResult, expected_terms: list[str]
) -> dict[str, Any]:
    packet_lower = result.packet_text.lower()
    terms_hit = sum(1 for term in expected_terms if term.lower() in packet_lower)
    
    overclaim = False
    if result.error and "guaranteed" in result.error.lower():
        overclaim = True
    if result.packet_text and "guaranteed" in result.packet_text.lower():
        if not result.provenance_present:
            overclaim = True
    
    return {
        "backend_available": result.available,
        "packet_term_hit": terms_hit >= len(expected_terms) if expected_terms else True,
        "provenance_present": result.provenance_present,
        "packet_chars": len(result.packet_text),
        "latency_ms": result.latency_ms,
        "empty_packet": result.empty,
        "overclaim_risk": overclaim,
        "evidence_count": result.evidence_count,
        "error_message": result.error,
    }


def write_outputs(
    out_dir: Path,
    config: dict[str, Any],
    results: list[dict[str, Any]],
    summary: dict[str, Any],
    comparison: dict[str, Any] | None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "backend_compare_config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )
    payload = {"config": config, "summary": summary, "results": results, "comparison": comparison}
    (out_dir / "backend_compare_results.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    
    fields = [
        "case_id", "query", "backend", "backend_available", "packet_term_hit",
        "provenance_present", "packet_chars", "latency_ms", "empty_packet",
        "overclaim_risk", "evidence_count", "error_message"
    ]
    with (out_dir / "backend_compare_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k) for k in fields})
    
    write_report(out_dir / "backend_compare_report.md", results, summary, comparison)


def write_report(
    path: Path,
    results: list[dict[str, Any]],
    summary: dict[str, Any],
    comparison: dict[str, Any] | None,
) -> None:
    lines = ["# Memory Backend Comparison", "", "## Summary", ""]
    for key, value in summary.items():
        lines.append(f"- {key}: `{value}`")
    
    by_backend: dict[str, list[dict]] = {}
    for r in results:
        b = r.get("backend", "unknown")
        if b not in by_backend:
            by_backend[b] = []
        by_backend[b].append(r)
    
    lines.extend(["", "## By Backend", ""])
    lines.append("| backend | available | term_hit | avg_latency | empty |")
    lines.append("|---|---|---|---|---|")
    for backend, items in sorted(by_backend.items()):
        available = sum(1 for i in items if i.get("backend_available"))
        term_hit = sum(1 for i in items if i.get("packet_term_hit"))
        avg_latency = sum(i.get("latency_ms", 0) for i in items) / max(1, len(items))
        empty = sum(1 for i in items if i.get("empty_packet"))
        lines.append(f"| {backend} | {available}/{len(items)} | {term_hit} | {avg_latency:.1f}ms | {empty} |")
    
    if comparison and comparison.get("available"):
        lines.extend(["", "## Comparison", ""])
        for key, delta in comparison.get("metric_deltas", {}).items():
            lines.append(f"- {key}: `{delta}`")
    
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_history(root: Path, row: dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    jsonl = root / "history.jsonl"
    with jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    csv_path = root / "history.csv"
    fields = ["run_id", "case_count", "backend_count", "ivy_native_success_rate", "mem0_success_rate"]
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k) for k in fields})


def load_history(root: Path) -> list[dict[str, Any]]:
    path = root / "history.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def compare_latest(root: Path, summary: dict[str, Any]) -> dict[str, Any]:
    history = load_history(root)
    if not history:
        return {"available": False, "message": "no previous run available"}
    prev = history[-1]
    return {
        "available": True,
        "previous_run_id": prev.get("run_id"),
        "metric_deltas": {
            "case_count": summary.get("total_cases", 0) - prev.get("case_count", 0),
        },
    }


def run_self_test() -> int:
    from tempfile import TemporaryDirectory
    
    with TemporaryDirectory() as td:
        root = Path(td)
        cases = [
            {"id": "test1", "query": "test query", "expected_packet_terms": []},
            {"id": "test2", "query": "qwen benchmark", "expected_packet_terms": ["qwen"]},
        ]
        cases_path = root / "cases.json"
        cases_path.write_text(json.dumps({"cases": cases}), encoding="utf-8")
        
        test_cases = load_cases(cases_path)
        if len(test_cases) != 2:
            print("FAIL: case load")
            return 1
        
        native = memory_backend.IvyNativeMemoryBackend()
        if not native.is_available():
            print("FAIL: IVY-native should be available")
            return 1
        
        native_result = native.build_packet("test query", None, 200)
        if not native_result.available:
            print("FAIL: IVY-native build_packet")
            return 1
        
        mem0_backend = memory_backend.Mem0MemoryBackend()
        if mem0_backend.is_available():
            print("INFO: Mem0 is available (unexpected but OK)")
        else:
            print("INFO: Mem0 unavailable as expected")
        
        backends = ["ivy_native"]
        policy = None
        results = []
        for case in test_cases:
            for backend in backends:
                result = build_packet_advisory(case.query, backend, policy)
                eval_result = evaluate_result(result, case.expected_terms)
                row = {
                    "case_id": case.id,
                    "query": case.query,
                    "backend": backend,
                    **eval_result,
                }
                results.append(row)
        
        if not results:
            print("FAIL: no results")
            return 1
        
        summary = {"total_cases": len(results), "backends_tested": len(backends)}
        out_dir = root / "compare"
        write_outputs(out_dir, {"backends": backends}, results, summary, None)
        
        if not (out_dir / "backend_compare_report.md").exists():
            print("FAIL: report not written")
            return 1
    
    print("PASS")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare memory backends.")
    parser.add_argument("--cases", default=None)
    parser.add_argument("--backends", nargs="+", default=["ivy_native", "mem0"])
    parser.add_argument("--policy", default=None)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-chars", type=int, default=800)
    parser.add_argument("--compare-latest", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    
    if args.self_test:
        raise SystemExit(run_self_test())
    
    cases_path = Path(args.cases) if args.cases else None
    if cases_path and not cases_path.exists():
        raise SystemExit(f"Cases file not found: {cases_path}")
    
    if cases_path is None and not args.self_test:
        raise SystemExit("--cases is required unless --self-test is used")
    
    if cases_path is None:
        test_cases = []
    else:
        test_cases = load_cases(cases_path)
    raw_tokens = []
    for token in args.backends:
        raw_tokens.extend(token.split(","))
    backends = []
    for token in raw_tokens:
        for name in token.split():
            if name:
                backends.append(name)
    if not backends:
        raise SystemExit("No backends specified. Use --backends ivy_native mem0")
    seen = set()
    ordered = []
    for name in backends:
        if name not in seen:
            ordered.append(name)
            seen.add(name)
    backends = ordered
    supported = {"ivy_native", "mem0"}
    unknown = [b for b in backends if b not in supported]
    if unknown:
        raise SystemExit(f"Unknown backend(s): {', '.join(unknown)}. Supported: {', '.join(sorted(supported))}")
    
    config = {
        "run_id": datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
        "cases_path": str(cases_path),
        "backends": backends,
        "policy": args.policy,
        "top_k": args.top_k,
        "max_chars": args.max_chars,
        "dry_run": args.dry_run,
    }
    
    root = Path(args.output_root)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    out_dir = root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    
    results: list[dict[str, Any]] = []
    
    for case in test_cases:
        for backend in backends:
            if args.dry_run:
                result = MemoryBackendResult(
                    packet_text="[dry-run]" if backend == "ivy_native" else "[dry-run mem0]",
                    empty=False,
                    backend=backend,
                    available=backend == "ivy_native",
                    provenance_present=True,
                    evidence_count=1,
                    latency_ms=10.0,
                    error=None,
                )
            else:
                result = build_packet_advisory(
                    case.query, backend, args.policy, args.max_chars
                )
            
            eval_result = evaluate_result(result, case.expected_terms)
            row = {
                "case_id": case.id,
                "query": case.query,
                "backend": backend,
                **eval_result,
            }
            results.append(row)
    
    summary = {
        "total_cases": len(results),
        "backends_tested": len(backends),
    }
    for backend in backends:
        backend_results = [r for r in results if r.get("backend") == backend]
        if backend_results:
            term_hits = sum(1 for r in backend_results if r.get("packet_term_hit"))
            avg_latency = sum(r.get("latency_ms", 0) for r in backend_results) / len(backend_results)
            empty = sum(1 for r in backend_results if r.get("empty_packet"))
            available = sum(1 for r in backend_results if r.get("backend_available"))
            summary[f"{backend}_available"] = available
            summary[f"{backend}_term_hit_rate"] = round(term_hits / len(backend_results), 4)
            summary[f"{backend}_avg_latency_ms"] = round(avg_latency, 1)
            summary[f"{backend}_empty_count"] = empty
    
    comparison = compare_latest(root, summary) if args.compare_latest else None
    write_outputs(out_dir, config, results, summary, comparison)
    append_history(root, {**config, **{k: v for k, v in summary.items() if not isinstance(v, dict)}})
    
    print(f"backend compare run: {out_dir}")
    print(f"total_cases: {summary['total_cases']}")
    for backend in backends:
        rate = summary.get(f"{backend}_term_hit_rate", 0)
        print(f"{backend} term_hit_rate: {rate}")


if __name__ == "__main__":
    main()
