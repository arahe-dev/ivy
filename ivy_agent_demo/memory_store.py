from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(__file__).resolve().parent / "memory" / "ivy_memory.sqlite3"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class SearchCapabilities:
    fts5: bool
    sqlite_vec: bool


class MemoryStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def capabilities(self) -> SearchCapabilities:
        conn = self.connect()
        try:
            fts5 = self._detect_fts5(conn)
            sqlite_vec = self._detect_sqlite_vec(conn)
            return SearchCapabilities(fts5=fts5, sqlite_vec=sqlite_vec)
        finally:
            conn.close()

    def init_schema(self) -> SearchCapabilities:
        conn = self.connect()
        try:
            caps = SearchCapabilities(
                fts5=self._detect_fts5(conn),
                sqlite_vec=self._detect_sqlite_vec(conn),
            )
            with conn:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS episodes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id TEXT,
                        created_at TEXT,
                        task_text TEXT,
                        outcome TEXT,
                        success INTEGER,
                        failure_type TEXT,
                        artifact_path TEXT,
                        model_profile TEXT,
                        total_steps INTEGER,
                        source_kind TEXT
                    );

                    CREATE TABLE IF NOT EXISTS tool_traces (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        episode_id INTEGER NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
                        step_index INTEGER,
                        tool_name TEXT,
                        status TEXT,
                        args_summary TEXT,
                        args_hash TEXT,
                        result_summary TEXT,
                        artifact_path TEXT
                    );

                    CREATE TABLE IF NOT EXISTS artifacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        episode_id INTEGER REFERENCES episodes(id) ON DELETE CASCADE,
                        path TEXT NOT NULL,
                        kind TEXT,
                        sha256 TEXT,
                        created_at TEXT,
                        UNIQUE(path, sha256)
                    );

                    CREATE TABLE IF NOT EXISTS memory_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_episode_id INTEGER REFERENCES episodes(id) ON DELETE SET NULL,
                        kind TEXT,
                        text TEXT NOT NULL,
                        importance REAL,
                        confidence REAL,
                        status TEXT,
                        source_artifact_path TEXT,
                        created_at TEXT,
                        last_used_at TEXT
                    );

                    CREATE TABLE IF NOT EXISTS memory_vectors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        memory_item_id INTEGER NOT NULL REFERENCES memory_items(id) ON DELETE CASCADE,
                        backend TEXT NOT NULL,
                        embedding_model TEXT NOT NULL,
                        embedding_dim INTEGER NOT NULL,
                        vector_json TEXT,
                        vector_blob BLOB,
                        created_at TEXT,
                        UNIQUE(memory_item_id, backend, embedding_model)
                    );

                    CREATE INDEX IF NOT EXISTS idx_episodes_run_id ON episodes(run_id);
                    CREATE INDEX IF NOT EXISTS idx_tool_traces_episode ON tool_traces(episode_id);
                    CREATE INDEX IF NOT EXISTS idx_artifacts_episode ON artifacts(episode_id);
                    CREATE INDEX IF NOT EXISTS idx_memory_items_episode ON memory_items(source_episode_id);
                    CREATE INDEX IF NOT EXISTS idx_memory_items_kind ON memory_items(kind);
                    """
                )
                if caps.fts5:
                    conn.execute(
                        """
                        CREATE VIRTUAL TABLE IF NOT EXISTS memory_items_fts
                        USING fts5(text, kind, episode_task, run_id);
                        """
                    )
                    self.rebuild_fts(conn)
            return caps
        finally:
            conn.close()

    def _detect_fts5(self, conn: sqlite3.Connection) -> bool:
        try:
            conn.execute("CREATE VIRTUAL TABLE temp._ivy_fts5_probe USING fts5(x)")
            conn.execute("DROP TABLE temp._ivy_fts5_probe")
            return True
        except sqlite3.Error:
            return False

    def _detect_sqlite_vec(self, conn: sqlite3.Connection) -> bool:
        try:
            conn.execute("SELECT vec_version()")
            return True
        except sqlite3.Error:
            return False

    def rebuild_fts(self, conn: sqlite3.Connection | None = None) -> None:
        close = conn is None
        conn = conn or self.connect()
        try:
            if not self._detect_fts5(conn):
                return
            conn.execute("DELETE FROM memory_items_fts")
            rows = conn.execute(
                """
                SELECT mi.id, mi.text, mi.kind, e.task_text, e.run_id
                FROM memory_items mi
                LEFT JOIN episodes e ON e.id = mi.source_episode_id
                """
            ).fetchall()
            for row in rows:
                conn.execute(
                    """
                    INSERT INTO memory_items_fts(rowid, text, kind, episode_task, run_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (row["id"], row["text"], row["kind"], row["task_text"], row["run_id"]),
                )
            if close:
                conn.commit()
        finally:
            if close:
                conn.close()

    def insert_episode(self, **values: Any) -> int:
        payload = {
            "run_id": values.get("run_id"),
            "created_at": values.get("created_at") or utc_now(),
            "task_text": values.get("task_text"),
            "outcome": values.get("outcome"),
            "success": self._bool_or_none(values.get("success")),
            "failure_type": values.get("failure_type"),
            "artifact_path": values.get("artifact_path"),
            "model_profile": values.get("model_profile"),
            "total_steps": values.get("total_steps"),
            "source_kind": values.get("source_kind"),
        }
        conn = self.connect()
        try:
            with conn:
                cur = conn.execute(
                    """
                    INSERT INTO episodes
                    (run_id, created_at, task_text, outcome, success, failure_type, artifact_path, model_profile, total_steps, source_kind)
                    VALUES
                    (:run_id, :created_at, :task_text, :outcome, :success, :failure_type, :artifact_path, :model_profile, :total_steps, :source_kind)
                    """,
                    payload,
                )
                episode_id = int(cur.lastrowid)
            return episode_id
        finally:
            conn.close()

    def insert_memory_item(self, conn: sqlite3.Connection, **values: Any) -> int:
        cur = conn.execute(
            """
            INSERT INTO memory_items
            (source_episode_id, kind, text, importance, confidence, status, source_artifact_path, created_at, last_used_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                values.get("source_episode_id"),
                values.get("kind"),
                values["text"],
                values.get("importance", 0.5),
                values.get("confidence", 0.8),
                values.get("status", "active"),
                values.get("source_artifact_path"),
                values.get("created_at") or utc_now(),
                values.get("last_used_at"),
            ),
        )
        item_id = int(cur.lastrowid)
        if self._detect_fts5(conn):
            row = conn.execute(
                "SELECT task_text, run_id FROM episodes WHERE id = ?",
                (values.get("source_episode_id"),),
            ).fetchone()
            conn.execute(
                """
                INSERT INTO memory_items_fts(rowid, text, kind, episode_task, run_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    values["text"],
                    values.get("kind"),
                    row["task_text"] if row else None,
                    row["run_id"] if row else None,
                ),
            )
        return item_id

    def stats(self) -> dict[str, int | bool]:
        conn = self.connect()
        try:
            tables = ["episodes", "tool_traces", "artifacts", "memory_items", "memory_vectors"]
            out: dict[str, int | bool] = {}
            for table in tables:
                out[table] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            caps = SearchCapabilities(
                fts5=self._detect_fts5(conn),
                sqlite_vec=self._detect_sqlite_vec(conn),
            )
            out["fts5_available"] = caps.fts5
            out["sqlite_vec_available"] = caps.sqlite_vec
            return out
        finally:
            conn.close()

    def _bool_or_none(self, value: Any) -> int | None:
        if value is None:
            return None
        return 1 if bool(value) else 0
