from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def dataset_exists(name: str) -> bool:
    dataset = ROOT / "out" / name
    return (
        (dataset / "corpus" / "corpus_items.jsonl").exists()
        and (dataset / "eval" / "cases.json").exists()
        and (dataset / "metadata" / "dataset_manifest.json").exists()
    )


def run_script(*args: str) -> None:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


@pytest.fixture(scope="session", autouse=True)
def ensure_generated_datasets() -> None:
    for scale in ("smoke", "medium", "stress"):
        name = f"context_stress_{scale}"
        if not dataset_exists(name):
            run_script("scripts/generate_context_stress_dataset.py", "--scale", scale, "--seed", "123")

    if not dataset_exists("context_stress_ivy_real"):
        run_script(
            "scripts/generate_ivy_real_dataset.py",
            "--output",
            "out/context_stress_ivy_real",
            "--seed",
            "777",
        )

    if not dataset_exists("context_stress_ivy_real_v2"):
        run_script(
            "scripts/generate_ivy_real_v2_dataset.py",
            "--output",
            "out/context_stress_ivy_real_v2",
            "--seed",
            "778",
        )

    if not dataset_exists("context_stress_freshness_authority_cp27"):
        run_script(
            "scripts/generate_freshness_authority_dataset.py",
            "--output",
            "out/context_stress_freshness_authority_cp27",
        )
