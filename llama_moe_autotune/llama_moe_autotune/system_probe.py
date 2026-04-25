from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _warn(warnings: list[str], message: str) -> None:
    warnings.append(message)


def _run_text(command: list[str], timeout: int = 20) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as exc:
        return -1, "", str(exc)


def _wmic_value(args: list[str]) -> str | None:
    if not shutil.which("wmic"):
        return None
    code, stdout, _ = _run_text(["wmic", *args])
    if code != 0:
        return None
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    return lines[1]


def _memory_info(warnings: list[str]) -> dict[str, Any]:
    try:
        import psutil  # type: ignore

        mem = psutil.virtual_memory()
        return {
            "total_bytes": int(mem.total),
            "available_bytes": int(mem.available),
            "source": "psutil",
        }
    except Exception as exc:
        _warn(warnings, f"psutil memory probe unavailable: {exc}")

    total_kb = _wmic_value(["ComputerSystem", "get", "TotalPhysicalMemory"])
    free_kb = _wmic_value(["OS", "get", "FreePhysicalMemory"])
    result: dict[str, Any] = {"source": "wmic"}
    try:
        if total_kb:
            result["total_bytes"] = int(total_kb)
        if free_kb:
            result["available_bytes"] = int(free_kb) * 1024
    except ValueError as exc:
        _warn(warnings, f"wmic memory parse failed: {exc}")
    return result


def get_available_ram_bytes() -> int | None:
    warnings: list[str] = []
    return _memory_info(warnings).get("available_bytes")


def _cpu_name(warnings: list[str]) -> str | None:
    value = _wmic_value(["cpu", "get", "Name"])
    if value:
        return value
    try:
        return platform.processor() or None
    except Exception as exc:
        _warn(warnings, f"CPU probe failed: {exc}")
        return None


def _nvidia_smi(warnings: list[str]) -> dict[str, Any]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        _warn(warnings, "nvidia-smi not found")
        return {"available": False}
    query = "name,memory.total,memory.used,memory.free,driver_version"
    code, stdout, stderr = _run_text(
        [exe, f"--query-gpu={query}", "--format=csv,noheader,nounits"]
    )
    if code != 0:
        _warn(warnings, f"nvidia-smi failed: {stderr.strip()}")
        return {"available": False, "error": stderr.strip()}
    gpus = []
    for line in stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) >= 5:
            gpus.append(
                {
                    "name": parts[0],
                    "memory_total_mib": _int_or_none(parts[1]),
                    "memory_used_mib": _int_or_none(parts[2]),
                    "memory_free_mib": _int_or_none(parts[3]),
                    "driver_version": parts[4],
                }
            )
    return {"available": True, "gpus": gpus}


def gpu_memory_snapshot() -> dict[str, Any]:
    warnings: list[str] = []
    return _nvidia_smi(warnings)


def _int_or_none(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def _llama_devices(llama_cli: Path | None, warnings: list[str]) -> dict[str, Any]:
    if not llama_cli:
        return {"available": False, "reason": "llama-cli not provided"}
    if not llama_cli.exists():
        return {"available": False, "reason": "llama-cli path does not exist"}
    code, stdout, stderr = _run_text([str(llama_cli), "--list-devices"], timeout=30)
    if code != 0:
        _warn(warnings, "llama-cli --list-devices failed or is unsupported")
        return {"available": False, "exit_code": code, "stderr": stderr[-2000:]}
    return {"available": True, "stdout": stdout[-5000:], "stderr": stderr[-5000:]}


def _disk_info(path: Path, warnings: list[str]) -> dict[str, Any]:
    try:
        target = path if path.exists() else path.parent
        usage = shutil.disk_usage(target)
        drive = Path(target.anchor).as_posix() if target.anchor else str(target)
        return {
            "path": str(target),
            "drive": drive,
            "total_bytes": usage.total,
            "free_bytes": usage.free,
            "storage_type": _storage_type_windows(target, warnings),
        }
    except Exception as exc:
        _warn(warnings, f"disk probe failed: {exc}")
        return {}


def _storage_type_windows(path: Path, warnings: list[str]) -> str | None:
    if platform.system().lower() != "windows":
        return None
    ps = shutil.which("powershell") or shutil.which("pwsh")
    if not ps:
        return None
    drive = path.drive.rstrip(":")
    if not drive:
        return None
    script = (
        "$ErrorActionPreference='SilentlyContinue';"
        f"$p=(Get-Partition -DriveLetter '{drive}');"
        "$d=$p|Get-Disk;"
        "$d.MediaType"
    )
    code, stdout, _ = _run_text([ps, "-NoProfile", "-Command", script], timeout=10)
    if code == 0:
        value = stdout.strip()
        return value or None
    return None


def collect_system_info(llama_cli: Path | None, model: Path | None, out_dir: Path) -> dict[str, Any]:
    warnings: list[str] = []
    info: dict[str, Any] = {
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "platform": platform.platform(),
        },
        "cpu": {"name": _cpu_name(warnings)},
        "memory": _memory_info(warnings),
        "nvidia": _nvidia_smi(warnings),
        "llama_devices": _llama_devices(llama_cli, warnings),
        "cwd": os.getcwd(),
        "warnings": warnings,
    }
    if model:
        try:
            info["model_file"] = {
                "path": str(model),
                "size_bytes": model.stat().st_size if model.exists() else None,
            }
        except Exception as exc:
            _warn(warnings, f"model stat failed: {exc}")
        info["disk"] = _disk_info(model, warnings)
    else:
        info["disk"] = _disk_info(out_dir, warnings)
    return info


def collect_process_peak_memory(pid: int) -> dict[str, Any]:
    try:
        import psutil  # type: ignore

        proc = psutil.Process(pid)
        info = proc.memory_info()
        return {
            "rss_bytes": getattr(info, "rss", None),
            "vms_bytes": getattr(info, "vms", None),
            "source": "psutil",
        }
    except Exception:
        return {"source": "unavailable"}
