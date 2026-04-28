from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


RUN_ROOT = Path("C:/ivy/runs")
AUTORESEARCH_ROOT = RUN_ROOT / "autoresearch"
SNAPSHOT_ROOT = AUTORESEARCH_ROOT / "metrics_snapshots"


@dataclass
class MetricSnapshot:
    label: str
    source_paths: dict[str, str]
    metrics: dict[str, Any]


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def latest_run_dir(root: Path) -> Path | None:
    if not root.exists():
        return None
    dirs = [p for p in root.iterdir() if p.is_dir()]
    if not dirs:
        return None
    return max(dirs, key=lambda p: p.stat().st_mtime)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_memory_packet_sweep(run_dir: Path) -> dict[str, Any]:
    result_path = run_dir / "sweep_results.json"
    if not result_path.exists():
        return {}
    payload = load_json(result_path)
    summary = payload.get("summary", {})
    return {
        "packet_term_hit_rate": summary.get("packet_term_hit_rate"),
        "empty_packet_count": summary.get("empty_packet_count"),
        "overclaim_risk_count": summary.get("overclaim_risk_count"),
        "overcompression_risk_count": summary.get("overcompression_risk_count"),
        "packet_avg_latency_ms": summary.get("average_latency_ms"),
        "packet_avg_chars": summary.get("average_packet_chars"),
        "packet_sweep_run_id": payload.get("config", {}).get("run_id"),
    }


def parse_memory_ranking_eval(run_dir: Path) -> dict[str, Any]:
    result_path = run_dir / "ranking_eval_results.json"
    if not result_path.exists():
        return {}
    payload = load_json(result_path)
    summary = payload.get("summary", {})
    return {
        "top_1_source_family_hit_rate": summary.get("top_1_source_family_hit_rate"),
        "top_3_source_family_hit_rate": summary.get("top_3_source_family_hit_rate"),
        "ranking_term_hit_rate": summary.get("term_hit_rate"),
        "provenance_rate": summary.get("provenance_rate"),
        "ranking_avg_latency_ms": summary.get("avg_latency_ms"),
        "ranking_eval_run_id": payload.get("config", {}).get("run_id"),
    }


def parse_memory_packet_eval(run_dir: Path) -> dict[str, Any]:
    result_path = run_dir / "packet_eval_results.json"
    if not result_path.exists():
        return {}
    payload = load_json(result_path)
    summary = payload.get("summary", {})
    return {
        "packet_eval_term_hit_rate": summary.get("packet_term_hit_rate"),
        "packet_eval_provenance_rate": summary.get("provenance_line_rate"),
        "packet_eval_grouping_quality_rate": summary.get("grouping_quality_rate"),
        "packet_eval_diversity_quality_rate": summary.get("diversity_quality_rate"),
        "packet_eval_avg_latency_ms": summary.get("average_latency_ms"),
        "packet_eval_avg_chars": summary.get("average_packet_chars"),
        "packet_eval_run_id": payload.get("config", {}).get("eval_run_id"),
    }


def parse_memory_eval(run_dir: Path) -> dict[str, Any]:
    result_path = run_dir / "memory_eval_results.json"
    if not result_path.exists():
        return {}
    payload = load_json(result_path)
    summary = payload.get("summary", {})
    return {
        "memory_eval_top_1_hit_rate": summary.get("top_1_hit_rate"),
        "memory_eval_top_3_hit_rate": summary.get("top_3_hit_rate"),
        "memory_eval_top_k_hit_rate": summary.get("top_k_hit_rate"),
        "memory_eval_provenance_rate": summary.get("provenance_present_rate"),
        "memory_eval_avg_latency_ms": summary.get("average_latency_ms"),
        "memory_eval_run_id": payload.get("config", {}).get("eval_run_id"),
    }


def parse_from_dir(run_dir: Path) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    if (run_dir / "sweep_results.json").exists():
        metrics.update(parse_memory_packet_sweep(run_dir))
        metrics["safety_hit_rate"] = extract_safety_hit_rate(run_dir)
    if (run_dir / "ranking_eval_results.json").exists():
        metrics.update(parse_memory_ranking_eval(run_dir))
    if (run_dir / "packet_eval_results.json").exists():
        metrics.update(parse_memory_packet_eval(run_dir))
    if (run_dir / "memory_eval_results.json").exists():
        metrics.update(parse_memory_eval(run_dir))
    return metrics


def extract_safety_hit_rate(run_dir: Path) -> float | None:
    result_path = run_dir / "sweep_results.json"
    if not result_path.exists():
        return None
    payload = load_json(result_path)
    results = payload.get("results", [])
    safety = [r for r in results if r.get("category") == "safety"]
    if not safety:
        return None
    hit_rate = sum(1 for r in safety if r.get("packet_term_hit")) / len(safety)
    return round(hit_rate, 4)


def collect_latest(run_root: Path = RUN_ROOT) -> MetricSnapshot:
    packet_sweep_dir = latest_run_dir(run_root / "memory_packet_sweep")
    ranking_eval_dir = latest_run_dir(run_root / "memory_ranking_eval")
    packet_eval_dir = latest_run_dir(run_root / "memory_packet_eval")
    memory_eval_dir = latest_run_dir(run_root / "memory_eval")

    metrics: dict[str, Any] = {}
    sources: dict[str, str] = {}

    if packet_sweep_dir:
        metrics.update(parse_memory_packet_sweep(packet_sweep_dir))
        metrics["safety_hit_rate"] = extract_safety_hit_rate(packet_sweep_dir)
        sources["memory_packet_sweep"] = str(packet_sweep_dir)
    if ranking_eval_dir:
        metrics.update(parse_memory_ranking_eval(ranking_eval_dir))
        sources["memory_ranking_eval"] = str(ranking_eval_dir)
    if packet_eval_dir:
        metrics.update(parse_memory_packet_eval(packet_eval_dir))
        sources["memory_packet_eval"] = str(packet_eval_dir)
    if memory_eval_dir:
        metrics.update(parse_memory_eval(memory_eval_dir))
        sources["memory_eval"] = str(memory_eval_dir)

    return MetricSnapshot(label="latest", source_paths=sources, metrics=metrics)


def resolve_run_id(run_id: str, run_root: Path = RUN_ROOT) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    sources: dict[str, str] = {}
    for name, parser in [
        ("memory_packet_sweep", parse_memory_packet_sweep),
        ("memory_ranking_eval", parse_memory_ranking_eval),
        ("memory_packet_eval", parse_memory_packet_eval),
        ("memory_eval", parse_memory_eval),
    ]:
        candidate = run_root / name / run_id
        if candidate.exists():
            metrics.update(parser(candidate))
            if name == "memory_packet_sweep":
                metrics["safety_hit_rate"] = extract_safety_hit_rate(candidate)
            sources[name] = str(candidate)
    return {"metrics": metrics, "source_paths": sources}


def resolve_metrics_ref(ref: str, run_root: Path = RUN_ROOT) -> dict[str, Any]:
    if ref == "latest":
        snap = collect_latest(run_root=run_root)
        return {"metrics": snap.metrics, "source_paths": snap.source_paths}

    path = Path(ref)
    if path.exists():
        if path.is_file():
            payload = load_json(path)
            if "metrics" in payload:
                return {"metrics": payload.get("metrics", {}), "source_paths": payload.get("source_paths", {})}
        if path.is_dir():
            metrics = parse_from_dir(path)
            if metrics:
                return {"metrics": metrics, "source_paths": {"custom": str(path)}}
            latest = latest_run_dir(path)
            if latest:
                metrics = parse_from_dir(latest)
                return {"metrics": metrics, "source_paths": {"custom": str(latest)}}

    from_id = resolve_run_id(ref, run_root=run_root)
    if from_id["metrics"]:
        return from_id
    raise FileNotFoundError(f"Unable to resolve metrics reference: {ref}")


def metric_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    keys = sorted(set(before) | set(after))
    deltas: dict[str, Any] = {}
    for key in keys:
        b = safe_float(before.get(key))
        a = safe_float(after.get(key))
        if b is None or a is None:
            if before.get(key) != after.get(key):
                deltas[key] = {"before": before.get(key), "after": after.get(key)}
            continue
        deltas[key] = round(a - b, 4)
    return deltas


def snapshot(label: str) -> Path:
    SNAPSHOT_ROOT.mkdir(parents=True, exist_ok=True)
    snap = collect_latest()
    path = SNAPSHOT_ROOT / f"{label}.json"
    payload = {"label": label, "source_paths": snap.source_paths, "metrics": snap.metrics}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def compare_snapshots(before: str, after: str) -> dict[str, Any]:
    b = resolve_metrics_ref(before)
    a = resolve_metrics_ref(after)
    return {
        "before": b.get("metrics", {}),
        "after": a.get("metrics", {}),
        "deltas": metric_delta(b.get("metrics", {}), a.get("metrics", {})),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect or compare IVY autoresearch metrics.")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("latest", help="Print latest metrics snapshot.")

    snap = sub.add_parser("snapshot", help="Save latest snapshot with label.")
    snap.add_argument("--label", required=True)

    comp = sub.add_parser("compare", help="Compare two snapshots or run paths.")
    comp.add_argument("--before", required=True)
    comp.add_argument("--after", required=True)

    args = parser.parse_args()
    if args.command == "snapshot":
        path = snapshot(args.label)
        print(f"snapshot saved: {path}")
        return
    if args.command == "compare":
        payload = compare_snapshots(args.before, args.after)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    snap = collect_latest()
    print(json.dumps({"label": snap.label, "source_paths": snap.source_paths, "metrics": snap.metrics}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
