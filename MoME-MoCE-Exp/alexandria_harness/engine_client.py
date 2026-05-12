from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


class EngineClientError(RuntimeError):
    def __init__(self, message: str, *, path: str, status: int | None = None, body: str = "") -> None:
        super().__init__(message)
        self.path = path
        self.status = status
        self.body = body


@dataclass(frozen=True)
class EngineSnapshot:
    health: dict[str, Any]
    hooks: dict[str, Any]
    memories: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"health": self.health, "hooks": self.hooks, "memories": self.memories}


class DogfoodHttpClient:
    """Small stdlib HTTP client for the D-ACCA dogfood hook service."""

    def __init__(self, base_url: str = "http://127.0.0.1:8766", *, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = self._url(path, params)
        request = urllib.request.Request(url, method="GET")
        return self._send(request, path=path)

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self._url(path),
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._send(request, path=path)

    def health(self) -> dict[str, Any]:
        return self.get("/health")

    def hooks(self) -> dict[str, Any]:
        return self.get("/hooks")

    def memories(self, *, limit: int = 50, offset: int = 0, include_text: bool = False) -> dict[str, Any]:
        return self.get(
            "/memories",
            {
                "limit": limit,
                "offset": offset,
                "include_text": str(include_text).lower(),
            },
        )

    def search(self, query: str, *, limit: int = 10, include_text: bool = False) -> dict[str, Any]:
        return self.get(
            "/search",
            {
                "q": query,
                "limit": limit,
                "include_text": str(include_text).lower(),
            },
        )

    def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post("/ingest", payload)

    def packet(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post("/packet", payload)

    def proof(self, route_id_or_path: str) -> dict[str, Any]:
        path = route_id_or_path if route_id_or_path.startswith("/") else f"/proof/{route_id_or_path}"
        return self.get(path)

    def feedback(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post("/feedback", payload)

    def forget(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post("/forget", payload)

    def snapshot(self, *, limit: int = 50, include_text: bool = False) -> EngineSnapshot:
        return EngineSnapshot(
            health=self.health(),
            hooks=self.hooks(),
            memories=self.memories(limit=limit, include_text=include_text),
        )

    def _url(self, path: str, params: dict[str, Any] | None = None) -> str:
        normalized = path if path.startswith("/") else f"/{path}"
        url = f"{self.base_url}{normalized}"
        if params:
            clean_params = {key: value for key, value in params.items() if value is not None}
            url = f"{url}?{urllib.parse.urlencode(clean_params)}"
        return url

    def _send(self, request: urllib.request.Request, *, path: str) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise EngineClientError(
                f"{exc.code} response from D-ACCA hook service for {path}",
                path=path,
                status=exc.code,
                body=body,
            ) from exc
        except urllib.error.URLError as exc:
            raise EngineClientError(f"could not reach D-ACCA hook service for {path}: {exc}", path=path) from exc

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise EngineClientError(f"non-JSON response from D-ACCA hook service for {path}", path=path, body=body) from exc
        if not isinstance(payload, dict):
            raise EngineClientError(f"JSON response for {path} was not an object", path=path, body=body)
        return payload


class DogfoodHooksObjectClient:
    """In-process adapter for tests and harness runs that do not need HTTP."""

    base_url = "local://dogfood-hooks"

    def __init__(self, hooks: Any) -> None:
        self.hooks_obj = hooks

    def health(self) -> dict[str, Any]:
        return self.hooks_obj.health()

    def hooks(self) -> dict[str, Any]:
        return self.hooks_obj.hooks()

    def memories(self, *, limit: int = 50, offset: int = 0, include_text: bool = False) -> dict[str, Any]:
        return self.hooks_obj.list_memories(limit=limit, offset=offset, include_text=include_text)

    def search(self, query: str, *, limit: int = 10, include_text: bool = False) -> dict[str, Any]:
        return self.hooks_obj.search(query, limit=limit, include_text=include_text)

    def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.hooks_obj.ingest(payload)

    def packet(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.hooks_obj.packet(payload)

    def proof(self, route_id_or_path: str) -> dict[str, Any]:
        route_id = route_id_or_path.strip("/")
        if route_id.startswith("proof/"):
            route_id = route_id.split("/", 1)[1]
        return self.hooks_obj.proof(route_id)

    def feedback(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.hooks_obj.feedback(payload)

    def forget(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.hooks_obj.forget(payload)

    def snapshot(self, *, limit: int = 50, include_text: bool = False) -> EngineSnapshot:
        return EngineSnapshot(
            health=self.health(),
            hooks=self.hooks(),
            memories=self.memories(limit=limit, include_text=include_text),
        )
