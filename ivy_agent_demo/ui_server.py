from __future__ import annotations

import argparse
import json
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .agent_loop import DEFAULT_MANIFEST, DEFAULT_SANDBOX_ROOT, run_scenario
from .model_client import IvyModelClient
from .policy import PolicyGate


DEFAULT_UI_RUNS_ROOT = Path("C:/ivy/runs/phase1_agent_demo_ui")
DEFAULT_STATIC_ROOT = Path("C:/ivy/ivy_agent_demo/static")


EVENT_ORDER = {
    "USER_TASK": 0,
    "MODEL_REQUEST": 10,
    "MODEL_RESPONSE": 20,
    "VALIDATION": 30,
    "REPAIR": 35,
    "PROGRESS_GUARD": 40,
    "POLICY": 50,
    "TOOL_CALL": 60,
    "TOOL_RESULT": 70,
    "FINAL_ANSWER": 80,
    "RUN_SUMMARY": 90,
}


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _event(
    event_type: str,
    step: int,
    summary: str,
    details: dict[str, Any] | list[Any] | str | None = None,
    status: str = "neutral",
) -> dict[str, Any]:
    return {
        "type": event_type,
        "step": step,
        "summary": summary,
        "status": status,
        "details": details if details is not None else {},
        "sort_key": [step, EVENT_ORDER[event_type]],
    }


def _summarize_tool_result(tool: str, result: dict[str, Any]) -> str:
    if not result.get("ok", False):
        return f"{tool} returned error: {result.get('error', 'unknown error')}"
    if tool == "fs_list":
        return f"listed {len(result.get('entries', []))} entries"
    if tool == "fs_read":
        return f"read {result.get('path', 'file')} ({result.get('size', 0)} bytes)"
    if tool == "fs_write":
        return f"wrote {result.get('bytes_written', 0)} bytes using {result.get('mode', 'unknown')} mode"
    if tool == "calc_eval":
        return f"calculated result {result.get('result')}"
    if tool == "json_validate":
        return "JSON valid" if result.get("valid") else "JSON invalid"
    if tool == "ask_user":
        return "simulated clarification response"
    return f"{tool} completed"


class UiState:
    def __init__(
        self,
        manifest_path: Path,
        runs_root: Path,
        sandbox_root: Path,
        slot_id: int,
        request_timeout_sec: int,
    ) -> None:
        self.runs_root = runs_root
        self.sandbox_root = sandbox_root.resolve()
        self.model = IvyModelClient(
            manifest_path=manifest_path,
            slot_id=slot_id,
            request_timeout_sec=request_timeout_sec,
            runtime_log_dir=runs_root / "runtime",
        )
        self.policy = PolicyGate(sandbox_root=self.sandbox_root)
        self.model.ensure_server()

    def _build_artifact_timeline(self, run_dir: Path, task: str, summary: dict[str, Any]) -> list[dict[str, Any]]:
        scenario_dir = run_dir / "ui_task"
        events: list[dict[str, Any]] = [
            _event("USER_TASK", 0, task, {"task": task}, "neutral")
        ]
        for step in summary.get("steps", []):
            step_no = int(step.get("step", 0))
            step_status = str(step.get("validation_status", ""))
            request_payload = _read_json(scenario_dir / f"model_request_{step_no}.json")
            if request_payload:
                events.append(
                    _event(
                        "MODEL_REQUEST",
                        step_no,
                        f"sent prompt to model ({len(str(request_payload.get('messages', [{}])[0].get('content', '')))} chars)",
                        request_payload,
                        "model",
                    )
                )

            response_payload = _read_json(scenario_dir / f"model_response_{step_no}.json")
            if response_payload:
                content = str(
                    response_payload.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                response_summary = "model returned output"
                try:
                    parsed = json.loads(content)
                    if "tool" in parsed:
                        response_summary = f"proposed {parsed.get('tool')}"
                    elif "final" in parsed:
                        response_summary = "proposed final answer"
                except Exception:
                    response_summary = "model returned invalid JSON"
                events.append(_event("MODEL_RESPONSE", step_no, response_summary, response_payload, "model"))

            validation_path = scenario_dir / f"validation_{step_no}.json"
            tool_call_path = scenario_dir / f"tool_call_{step_no}.json"
            tool_result_path = scenario_dir / f"tool_result_{step_no}.json"
            progress_guard_path = scenario_dir / f"progress_guard_{step_no}.json"

            validation = _read_json(validation_path)
            if validation:
                validation_ok = bool(validation.get("ok", False))
                validation_kind = validation.get("kind", "invalid")
                failures = validation.get("failure_taxonomy", [])
                if validation_ok:
                    summary_text = f"pass ({validation_kind})"
                    status = "pass"
                else:
                    summary_text = f"fail: {', '.join(failures) if failures else 'invalid'}"
                    status = "fail"
                events.append(_event("VALIDATION", step_no, summary_text, validation, status))
                if validation.get("kind") == "final":
                    final = str(validation.get("final") or "")
                    events.append(_event("FINAL_ANSWER", step_no, final[:180], {"final": final}, "pass"))

            repair_request = _read_text(scenario_dir / f"repair_task_{step_no}.txt")
            if repair_request:
                repair_validation = _read_json(scenario_dir / f"validation_{step_no}_repair.json")
                events.append(
                    _event(
                        "REPAIR",
                        step_no,
                        "one validator repair attempt used",
                        {"repair_task": repair_request, "repair_validation": repair_validation},
                        "blocked",
                    )
                )

            progress_guard = _read_json(progress_guard_path)
            if progress_guard:
                events.append(
                    _event(
                        "PROGRESS_GUARD",
                        step_no,
                        str(progress_guard.get("note") or "progress guard triggered"),
                        progress_guard,
                        "blocked",
                    )
                )
                continue

            tool_call = _read_json(tool_call_path)
            if tool_call:
                approved = bool(tool_call.get("policy_approved", False))
                tool = str(tool_call.get("tool") or "")
                arguments = tool_call.get("arguments") or {}
                policy_summary = "allowed" if approved else f"blocked: {', '.join(tool_call.get('policy_failures', []))}"
                events.append(_event("POLICY", step_no, policy_summary, tool_call, "pass" if approved else "blocked"))
                events.append(_event("TOOL_CALL", step_no, f"{tool} {arguments}", {"tool": tool, "arguments": arguments}, "tool"))

            tool_result = _read_json(tool_result_path)
            if step_status == "tool_executed" and tool_result:
                tool = str(tool_result.get("tool") or "")
                result = tool_result.get("result") or {}
                events.append(
                    _event(
                        "TOOL_RESULT",
                        step_no,
                        _summarize_tool_result(tool, result if isinstance(result, dict) else {}),
                        tool_result,
                        "pass" if isinstance(result, dict) and result.get("ok", False) else "fail",
                    )
                )

        final_answer = _read_text(scenario_dir / "final_answer.txt")
        if final_answer and not any(event["type"] == "FINAL_ANSWER" for event in events):
            events.append(_event("FINAL_ANSWER", 999, final_answer[:180], {"final": final_answer}, "neutral"))

        events.append(
            _event(
                "RUN_SUMMARY",
                1000,
                f"{summary.get('verdict', 'unknown')} | retries={summary.get('retry_count', 0)} | tools={len(summary.get('tool_calls', []))}",
                summary,
                "pass" if summary.get("passed") else "fail",
            )
        )
        return sorted(events, key=lambda event: event["sort_key"])

    def run_task(self, task: str) -> dict[str, Any]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        run_dir = self.runs_root / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        scenario = {
            "id": "ui_task",
            "user_task": task,
            "expected_tools": [],
            "expected_behavior": "Manual UI sandbox run",
            "unsafe": False,
            "success_requirements": (
                "Follow the Phase 1 sandbox contract. Use only allowed tools. "
                "Ask for clarification or refuse safely when the request is unsafe or ambiguous."
            ),
        }
        summary = run_scenario(self.model, self.policy, scenario, run_dir)
        events = self._build_artifact_timeline(run_dir, task, summary)
        run_id = run_dir.name
        phase_summary = {
            "run_id": run_id,
            "status": "complete",
            "run_root": str(run_dir),
            "scenario": summary,
            "events": events,
            "summary": {
                "passed": bool(summary.get("passed")),
                "verdict": summary.get("verdict"),
                "retry_count": int(summary.get("retry_count", 0)),
                "policy_violations": len(summary.get("policy_violations", [])),
                "policy_blocks": len(summary.get("blocked_calls", [])),
                "progress_guard_triggers": int(summary.get("progress_guard_triggered_count", 0)),
                "cache_reuse_status": summary.get("metrics", {}).get("cache_reuse_samples", []),
                "prompt_ms_avg": summary.get("metrics", {}).get("avg_prompt_ms"),
                "decode_tps_avg": summary.get("metrics", {}).get("avg_decode_tps"),
                "artifact_folder": str(run_dir),
            },
        }
        (run_dir / "phase1_ui_result.json").write_text(
            json.dumps(phase_summary, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        return phase_summary


class UiHandler(SimpleHTTPRequestHandler):
    state: UiState

    def __init__(self, *args: Any, directory: str | None = None, **kwargs: Any) -> None:
        super().__init__(*args, directory=directory or str(DEFAULT_STATIC_ROOT), **kwargs)

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, indent=2, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        if self.path != "/api/run":
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Unknown route"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 32_768:
                raise ValueError("Request body must be 1..32768 bytes")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            task = str(payload.get("task") or "").strip()
            if not task:
                raise ValueError("Missing task")
            result = self.state.run_task(task)
        except Exception as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
            return

        self._send_json(HTTPStatus.OK, {"ok": True, **result})


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local IVY Phase 1 sandbox UI")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--runs-root", default=str(DEFAULT_UI_RUNS_ROOT))
    parser.add_argument("--sandbox-root", default=str(DEFAULT_SANDBOX_ROOT))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--slot-id", type=int, default=0)
    parser.add_argument("--request-timeout-sec", type=int, default=180)
    args = parser.parse_args()

    if args.host != "127.0.0.1":
        raise ValueError("Phase 1 UI only binds to 127.0.0.1")

    DEFAULT_STATIC_ROOT.mkdir(parents=True, exist_ok=True)
    runs_root = Path(args.runs_root)
    runs_root.mkdir(parents=True, exist_ok=True)

    UiHandler.state = UiState(
        manifest_path=Path(args.manifest),
        runs_root=runs_root,
        sandbox_root=Path(args.sandbox_root),
        slot_id=args.slot_id,
        request_timeout_sec=args.request_timeout_sec,
    )

    server = ThreadingHTTPServer((args.host, args.port), UiHandler)
    print(f"IVY Phase 1 UI listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
