from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = REPO_ROOT / "MoME-MoCE-Exp" / "scripts" / "start_context_memory_daemon.ps1"


def test_context_memory_bootstrap_script_parses() -> None:
    command = (
        "$errors=$null; "
        f"[System.Management.Automation.Language.Parser]::ParseFile('{BOOTSTRAP}',[ref]$null,[ref]$errors) | Out-Null; "
        "if ($errors.Count) { $errors | Format-List *; exit 1 }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", command], check=True, capture_output=True, text=True)


def test_context_memory_bootstrap_mentions_warm_and_stop_after_warm() -> None:
    text = BOOTSTRAP.read_text(encoding="utf-8")
    assert "/warm" in text
    assert "StopAfterWarm" in text
    assert "process_caches" in text
