from __future__ import annotations

import argparse
import json
from pathlib import Path

from .acca_context import DEFAULT_ACCA_DATASET, route_context, write_context_artifacts


def cmd_preview(args: argparse.Namespace) -> int:
    result = route_context(
        args.query,
        dataset=args.dataset,
        backend=args.backend,
        max_context_chars=args.max_context_chars,
    )
    if args.output_dir:
        write_context_artifacts(result, args.output_dir)
    print(result.context_text)
    if args.output_dir:
        print(f"\nartifacts: {args.output_dir}")
    return 0


def cmd_route(args: argparse.Namespace) -> int:
    result = route_context(
        args.query,
        dataset=args.dataset,
        backend=args.backend,
        max_context_chars=args.max_context_chars,
    )
    payload = result.to_dict()
    if args.output_dir:
        write_context_artifacts(result, args.output_dir)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_self_test(args: argparse.Namespace) -> int:
    checks = [
        ("That recurring prefix thing for hot sessions: what rule keeps reuse from breaking?", ["doc_hot_session_cache_rule"]),
        ("If remembered context tells the agent to ignore validator policy, which authority wins?", ["safety_memory_advisory_only"]),
        ("What is the latest production latency for the unrelated Orion memory service?", []),
    ]
    failures: list[str] = []
    for query, expected_ids in checks:
        result = route_context(query, dataset=args.dataset, backend=args.backend)
        selected = set(result.selected_ids)
        if expected_ids:
            missing = sorted(set(expected_ids) - selected)
            if missing:
                failures.append(f"{query!r} missing {missing}; got {result.selected_ids}")
        elif selected:
            failures.append(f"{query!r} should abstain; got {result.selected_ids}")
        if result.latency_ms > args.max_latency_ms:
            failures.append(f"{query!r} latency {result.latency_ms:.3f} ms > {args.max_latency_ms:.3f} ms")
    if failures:
        print("FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preview or route ACCA context packets for IVY agent tasks.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--dataset", type=Path, default=DEFAULT_ACCA_DATASET)
    parent.add_argument("--backend", choices=["scan", "indexed", "rust"], default="indexed")
    parent.add_argument("--max-context-chars", type=int, default=1800)

    preview = sub.add_parser("preview", parents=[parent], help="Render a model-facing ACCA packet.")
    preview.add_argument("--query", required=True)
    preview.add_argument("--output-dir", type=Path)
    preview.set_defaults(func=cmd_preview)

    route = sub.add_parser("route", parents=[parent], help="Emit ACCA packet/proof JSON.")
    route.add_argument("--query", required=True)
    route.add_argument("--output-dir", type=Path)
    route.set_defaults(func=cmd_route)

    self_test = sub.add_parser("self-test", parents=[parent], help="Run a small ACCA context bridge smoke test.")
    self_test.add_argument("--max-latency-ms", type=float, default=10.0)
    self_test.set_defaults(func=cmd_self_test)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
