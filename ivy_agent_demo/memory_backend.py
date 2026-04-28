from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .memory_packet_cli import run_preview
from .memory_store import DEFAULT_DB_PATH


DEFAULT_DB_PATH = Path("C:/ivy/ivy_agent_demo/memory/ivy_memory.sqlite3")


@dataclass
class MemoryBackendResult:
    packet_text: str
    empty: bool
    backend: str
    available: bool
    provenance_present: bool
    evidence_count: int
    latency_ms: float
    error: str | None = None
    metadata: dict[str, Any] | None = None


class MemoryBackend(ABC):
    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def build_packet(
        self, query: str, policy: str | None = None, max_chars: int = 800
    ) -> MemoryBackendResult:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass


class IvyNativeMemoryBackend(MemoryBackend):
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = db_path or DEFAULT_DB_PATH

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        from .memory_router import route_memory

        decision, candidates, _policy = route_memory(
            query, str(self.db_path), None, top_k
        )
        return [
            {
                "text": c.text[:200],
                "kind": c.kind,
                "score": c.ranking.final_score if c.ranking else 0.0,
                "provenance": c.provenance_present,
                "source_artifact_path": c.source_artifact_path,
            }
            for c in candidates
        ]

    def build_packet(
        self, query: str, policy: str | None = None, max_chars: int = 800
    ) -> MemoryBackendResult:
        start = time.perf_counter()
        try:
            packet, _out_dir = run_preview(
                query=query,
                db_path=str(self.db_path),
                policy=policy,
                top_k=5,
                max_packet_chars=max_chars,
                output_root=None,
                save=False,
            )
            latency_ms = (time.perf_counter() - start) * 1000.0
            provenance_count = sum(1 for line in packet.packet_lines if line.provenance_present)
            return MemoryBackendResult(
                packet_text=packet.packet_text,
                empty=not packet.packet_text.strip(),
                backend="ivy_native",
                available=True,
                provenance_present=provenance_count > 0,
                evidence_count=packet.metrics.evidence_count,
                latency_ms=round(latency_ms, 3),
                error=None,
                metadata={
                    "packet_chars": packet.metrics.packet_chars,
                    "packet_line_count": packet.metrics.packet_line_count,
                    "provenance_line_rate": packet.metrics.provenance_line_rate,
                },
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000.0
            return MemoryBackendResult(
                packet_text="",
                empty=True,
                backend="ivy_native",
                available=True,
                provenance_present=False,
                evidence_count=0,
                latency_ms=round(latency_ms, 3),
                error=str(e),
            )

    def is_available(self) -> bool:
        return self.db_path.exists()


class Mem0MemoryBackend(MemoryBackend):
    def __init__(self):
        self._mem0 = None
        self._check_available()

    def _check_available(self) -> bool:
        try:
            import mem0
            self._mem0 = mem0
            return True
        except ImportError:
            self._mem0 = None
            return False

    def _init_client(self) -> Any:
        if self._mem0 is None:
            return None
        try:
            return self._mem0.Memory.from_llm()
        except Exception:
            try:
                return self._mem0.Memory()
            except Exception:
                return None

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if not self.is_available():
            return []
        client = self._init_client()
        if client is None:
            return []
        try:
            results = client.search(query, limit=top_k)
            return [
                {
                    "text": r.get("memory", r.get("text", ""))[:200],
                    "kind": r.get("metadata", {}).get("kind", "imported"),
                    "score": 0.5,
                    "provenance": bool(r.get("metadata", {}).get("source_artifact_path")),
                    "source_artifact_path": r.get("metadata", {}).get("source_artifact_path"),
                }
                for r in results
            ]
        except Exception:
            return []

    def build_packet(
        self, query: str, policy: str | None = None, max_chars: int = 800
    ) -> MemoryBackendResult:
        start = time.perf_counter()
        
        if not self.is_available():
            latency_ms = (time.perf_counter() - start) * 1000.0
            return MemoryBackendResult(
                packet_text="",
                empty=True,
                backend="mem0",
                available=False,
                provenance_present=False,
                evidence_count=0,
                latency_ms=round(latency_ms, 3),
                error="Mem0 not installed. Install with: pip install mem0",
            )
        
        client = self._init_client()
        if client is None:
            latency_ms = (time.perf_counter() - start) * 1000.0
            return MemoryBackendResult(
                packet_text="",
                empty=True,
                backend="mem0",
                available=False,
                provenance_present=False,
                evidence_count=0,
                latency_ms=round(latency_ms, 3),
                error="Mem0 client initialization failed. Check configuration.",
            )
        
        try:
            results = client.search(query, limit=5)
            if not results:
                latency_ms = (time.perf_counter() - start) * 1000.0
                return MemoryBackendResult(
                    packet_text="",
                    empty=True,
                    backend="mem0",
                    available=True,
                    provenance_present=False,
                    evidence_count=0,
                    latency_ms=round(latency_ms, 3),
                )
            
            lines = []
            provenance_count = 0
            for r in results[:5]:
                text = r.get("memory", r.get("text", ""))
                metadata = r.get("metadata", {})
                if metadata.get("source_artifact_path"):
                    provenance_count += 1
                lines.append(f"- Imported memory: {text[:150]}...")
            
            packet_text = "\n".join(lines)
            if len(packet_text) > max_chars:
                packet_text = packet_text[:max_chars] + "..."
            
            latency_ms = (time.perf_counter() - start) * 1000.0
            return MemoryBackendResult(
                packet_text=packet_text,
                empty=not packet_text.strip(),
                backend="mem0",
                available=True,
                provenance_present=provenance_count > 0,
                evidence_count=len(results),
                latency_ms=round(latency_ms, 3),
                error=None,
                metadata={
                    "packet_chars": len(packet_text),
                    "evidence_count": len(results),
                },
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000.0
            return MemoryBackendResult(
                packet_text="",
                empty=True,
                backend="mem0",
                available=self.is_available(),
                provenance_present=False,
                evidence_count=0,
                latency_ms=round(latency_ms, 3),
                error=str(e),
            )

    def is_available(self) -> bool:
        return self._mem0 is not None


def get_backend(name: str) -> MemoryBackend:
    if name == "ivy_native":
        return IvyNativeMemoryBackend()
    if name == "mem0":
        return Mem0MemoryBackend()
    raise ValueError(f"Unknown backend: {name}")


def list_backends() -> list[str]:
    backends = ["ivy_native"]
    if Mem0MemoryBackend().is_available():
        backends.append("mem0")
    return backends