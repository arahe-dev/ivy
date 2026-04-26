from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request


def _cast_manifest_value(value: str) -> Any:
    text = value.strip().strip('"').strip("'")
    if text.lower() in {"true", "false"}:
        return text.lower() == "true"
    if text and text.lstrip("-").isdigit():
        try:
            return int(text)
        except Exception:
            return text
    try:
        if "." in text:
            return float(text)
    except Exception:
        return text
    return text


def load_hot_manifest(path: Path) -> dict[str, Any]:
    manifest: dict[str, Any] = {"server_args": []}
    in_server_args = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "server_args:":
            in_server_args = True
            continue
        if in_server_args and line.lstrip().startswith("-"):
            value = line.split("-", 1)[1].strip().strip('"').strip("'")
            manifest["server_args"].append(value)
            continue
        in_server_args = False
        if ":" in line:
            key, raw_value = line.split(":", 1)
            manifest[key.strip()] = _cast_manifest_value(raw_value)
    return manifest


@dataclass
class ChatResult:
    request_payload: dict[str, Any]
    response_payload: dict[str, Any]
    content: str
    prompt_n: int | None
    prompt_ms: float | None
    decode_tps: float | None
    cache_reuse_status: str


class IvyModelClient:
    def __init__(
        self,
        manifest_path: Path,
        slot_id: int,
        request_timeout_sec: int,
        runtime_log_dir: Path,
    ) -> None:
        self.manifest_path = manifest_path
        self.manifest = load_hot_manifest(manifest_path)
        self.slot_id = slot_id
        self.request_timeout_sec = request_timeout_sec
        self.runtime_log_dir = runtime_log_dir
        self.runtime_log_dir.mkdir(parents=True, exist_ok=True)

        self.host = str(self.manifest["host"])
        self.port = int(self.manifest["port"])
        self.endpoint = str(self.manifest["endpoint"])
        self.url = f"http://{self.host}:{self.port}{self.endpoint}"

        self.server_exe = Path(str(self.manifest["server_exe"]))
        self.model_path = str(self.manifest["model"])
        self.server_args = list(self.manifest.get("server_args") or [])
        self.static_prefix_path = Path(str(self.manifest["static_prefix_path"]))
        self.static_prefix = self.static_prefix_path.read_text(encoding="utf-8")

        self.cold_prompt_n_baseline = int(self.manifest.get("cold_prompt_n_baseline", 0))
        self.max_tokens = int(self.manifest.get("max_tokens", 256))
        self.temperature = float(self.manifest.get("temperature", 0.0))
        self.top_k = int(self.manifest.get("top_k", 1))
        self.top_p = float(self.manifest.get("top_p", 1.0))
        self.min_p = float(self.manifest.get("min_p", 0.0))
        self.repeat_penalty = float(self.manifest.get("repeat_penalty", 1.0))
        self.seed = int(self.manifest.get("seed", 12345))
        self.stream = bool(self.manifest.get("stream", False))

        self.launched_server = False
        self._server_process: subprocess.Popen[str] | None = None

    def _health_ok(self) -> bool:
        url = f"http://{self.host}:{self.port}/health"
        try:
            with request.urlopen(url, timeout=2) as response:
                return int(response.status) == 200
        except Exception:
            return False

    def ensure_server(self) -> None:
        if self._health_ok():
            return

        stdout_path = self.runtime_log_dir / "server.stdout.log"
        stderr_path = self.runtime_log_dir / "server.stderr.log"
        stdout_file = stdout_path.open("w", encoding="utf-8")
        stderr_file = stderr_path.open("w", encoding="utf-8")

        args = [
            str(self.server_exe),
            "--model",
            self.model_path,
            "--host",
            self.host,
            "--port",
            str(self.port),
            *self.server_args,
        ]
        self._server_process = subprocess.Popen(
            args,
            stdout=stdout_file,
            stderr=stderr_file,
            text=True,
            shell=False,
        )
        self.launched_server = True

        deadline = time.time() + 240
        while time.time() < deadline:
            if self._server_process.poll() is not None:
                raise RuntimeError(f"llama-server exited during startup with code {self._server_process.returncode}")
            if self._health_ok():
                return
            time.sleep(1)
        raise TimeoutError(f"llama-server did not become ready at {self.host}:{self.port}")

    def stop_server_if_launched(self) -> None:
        if not self.launched_server:
            return
        if self._server_process is None:
            return
        if self._server_process.poll() is not None:
            return
        self._server_process.terminate()
        try:
            self._server_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self._server_process.kill()

    def _classify_cache_reuse(self, prompt_n: int | None, prompt_ms: float | None) -> str:
        if (prompt_n is not None and prompt_n <= 16) or (prompt_ms is not None and prompt_ms < 150):
            return "likely_hot_reuse"
        if (
            prompt_n is not None
            and self.cold_prompt_n_baseline > 0
            and prompt_n < round(self.cold_prompt_n_baseline * 0.85)
        ):
            return "partial_reuse"
        return "cold_or_lost_reuse"

    def chat(self, dynamic_task: str, max_tokens: int | None = None) -> ChatResult:
        full_prompt = self.static_prefix.rstrip() + "\n\nDYNAMIC TASK:\n" + dynamic_task.strip()
        return self.chat_full_prompt(full_prompt, max_tokens=max_tokens)

    def chat_full_prompt(self, full_prompt: str, max_tokens: int | None = None) -> ChatResult:
        payload: dict[str, Any] = {
            "id_slot": self.slot_id,
            "cache_prompt": True,
            "messages": [{"role": "user", "content": full_prompt}],
            "max_tokens": int(max_tokens or self.max_tokens),
            "temperature": self.temperature,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "min_p": self.min_p,
            "repeat_penalty": self.repeat_penalty,
            "seed": self.seed,
            "stream": self.stream,
        }

        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            with request.urlopen(req, timeout=self.request_timeout_sec) as response:
                body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            err_text = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP error from llama-server: {exc.code} {err_text}") from exc

        response_payload = json.loads(body)
        content = str(response_payload["choices"][0]["message"].get("content") or "")

        timings = response_payload.get("timings") or {}
        prompt_n = timings.get("prompt_n")
        prompt_ms = timings.get("prompt_ms")
        predicted_n = timings.get("predicted_n")
        predicted_ms = timings.get("predicted_ms")

        decode_tps: float | None = None
        if predicted_n and predicted_ms and predicted_ms > 0:
            decode_tps = round((predicted_n * 1000.0) / predicted_ms, 3)

        cache_reuse_status = self._classify_cache_reuse(prompt_n, prompt_ms)

        return ChatResult(
            request_payload=payload,
            response_payload=response_payload,
            content=content,
            prompt_n=prompt_n,
            prompt_ms=prompt_ms,
            decode_tps=decode_tps,
            cache_reuse_status=cache_reuse_status,
        )
