"""Durable task store (ADR-004): SQLite in WAL mode, shared by every TOM process on this machine.

The store is the source of truth for task status (PRD §12.2) — model context never is. Text and
outcomes are redacted before they are written (FR-007). A second process (the PySide6 window, the
CLI) sees the same tasks and can request cancellation; the owning process acts on it (AT-012).
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from tom_core.observability.redact import redact
from tools.project_paths import project_path
from tom_core.tasks.models import TERMINAL_STATES, TaskRecord, TaskState, can_transition

SCHEMA_VERSION = 1
DEFAULT_DB = project_path("tom_brain", "tasks.sqlite3")      # follows TOM_STATE_ROOT
MAX_TEXT = 2000


class InvalidTransition(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def pid_alive(pid: Optional[int]) -> bool:
    if not pid:
        return False
    if pid == os.getpid():
        return True
    try:
        import psutil
        return psutil.pid_exists(pid)
    except ImportError:
        return True   # cannot tell: assume alive rather than wrongly interrupting another window's task


def open_store(path: Optional[str] = None) -> "TaskStore":
    """The configured store: TOM_TASK_STORE=0 → in-memory (nothing persisted), else SQLite file."""
    if (os.environ.get("TOM_TASK_STORE") or "1").strip() == "0":
        return TaskStore(":memory:")
    return TaskStore(path or os.environ.get("TOM_TASK_DB") or str(DEFAULT_DB))


class TaskStore:
    def __init__(self, path: str) -> None:
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(path, check_same_thread=False, timeout=10)
        self._db.row_factory = sqlite3.Row
        if path != ":memory:":
            self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA busy_timeout=5000")
        self._migrate()

    # ── schema ───────────────────────────────────────────────────────────
    def _migrate(self) -> None:
        with self._lock:
            self._db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            row = self._db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
            current = int(row[0]) if row else 0
            if current > SCHEMA_VERSION:
                raise RuntimeError(f"task store schema v{current} is newer than this TOM (v{SCHEMA_VERSION})")
            if 0 < current < SCHEMA_VERSION and self.path != ":memory:":
                self._backup(f"v{current}")       # §S4: never migrate without a backup
            with self._db:
                self._db.executescript("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY, text TEXT NOT NULL, interface TEXT NOT NULL,
                        state TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                        parent_id TEXT, owner_pid INTEGER, cancel_requested INTEGER NOT NULL DEFAULT 0,
                        outcome TEXT NOT NULL DEFAULT '', result_status TEXT NOT NULL DEFAULT '',
                        response_type TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT '');
                    CREATE INDEX IF NOT EXISTS tasks_by_time ON tasks(created_at DESC);
                    CREATE TABLE IF NOT EXISTS task_events (
                        id INTEGER PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id),
                        at TEXT NOT NULL, kind TEXT NOT NULL, message TEXT NOT NULL DEFAULT '');
                    CREATE INDEX IF NOT EXISTS events_by_task ON task_events(task_id, id);
                """)
                self._db.execute("INSERT OR REPLACE INTO meta VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),))

    def _backup(self, label: str) -> Path:
        dest = Path(self.path).parent / "backups" / f"tasks-{label}-{datetime.now():%Y%m%d-%H%M%S}.sqlite3"
        dest.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._db.execute("PRAGMA wal_checkpoint(FULL)")
            shutil.copy2(self.path, dest)
        return dest

    # ── writes ───────────────────────────────────────────────────────────
    def create(self, text: str, interface: str, *, parent_id: Optional[str] = None) -> TaskRecord:
        task_id = uuid.uuid4().hex[:12]
        now = _now()
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO tasks (id, text, interface, state, created_at, updated_at, parent_id, owner_pid)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (task_id, redact(text)[:MAX_TEXT], interface or "unknown", TaskState.CREATED.value, now, now,
                 parent_id, os.getpid()))
            self._event(task_id, "state", TaskState.CREATED.value)
        return self.get(task_id)

    def _event(self, task_id: str, kind: str, message: str) -> None:
        self._db.execute("INSERT INTO task_events (task_id, at, kind, message) VALUES (?,?,?,?)",
                         (task_id, _now(), kind, redact(message)[:MAX_TEXT]))

    def add_event(self, task_id: str, kind: str, message: str) -> None:
        with self._lock, self._db:
            self._event(task_id, kind, message)

    def transition(self, task_id: str, new: TaskState, *, note: str = "", **fields: Any) -> TaskRecord:
        allowed = {"outcome", "result_status", "response_type", "error"}
        with self._lock, self._db:
            row = self._db.execute("SELECT state FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None:
                raise KeyError(task_id)
            old = TaskState(row["state"])
            if not can_transition(old, new):
                raise InvalidTransition(f"{task_id}: {old.value} -> {new.value} is not allowed")
            sets, params = ["state=?", "updated_at=?"], [new.value, _now()]
            for key, value in fields.items():
                if key in allowed:
                    sets.append(f"{key}=?")
                    params.append(redact(value)[:MAX_TEXT] if key in ("outcome", "error") else str(value)[:200])
            self._db.execute(f"UPDATE tasks SET {', '.join(sets)} WHERE id=?", params + [task_id])
            self._event(task_id, "state", new.value + (f": {note}" if note else ""))
        return self.get(task_id)

    def request_cancel(self, task_id: str) -> bool:
        with self._lock, self._db:
            cur = self._db.execute(
                "UPDATE tasks SET cancel_requested=1, updated_at=? WHERE id=? AND state NOT IN (%s)"
                % ",".join("?" * len(TERMINAL_STATES)),
                [_now(), task_id] + [s.value for s in TERMINAL_STATES])
            if cur.rowcount:
                self._event(task_id, "cancel_requested", "")
            return cur.rowcount > 0

    def recover_interrupted(self) -> List[str]:
        """Startup reconciliation (PRD §20, AT-006): tasks whose process died are marked BLOCKED, never replayed."""
        recovered = []
        with self._lock:
            rows = self._db.execute(
                "SELECT id, state, owner_pid FROM tasks WHERE state NOT IN (%s)" % ",".join("?" * len(TERMINAL_STATES)),
                [s.value for s in TERMINAL_STATES]).fetchall()
        for row in rows:
            if pid_alive(row["owner_pid"]):
                continue          # still owned by a live process (this one or another TOM window)
            with self._lock, self._db:
                self._db.execute(
                    "UPDATE tasks SET state=?, updated_at=?, error=? WHERE id=?",
                    (TaskState.BLOCKED.value, _now(),
                     f"Interrupted by a restart while {row['state']}. Not replayed - check whether it "
                     "finished before asking again.", row["id"]))
                self._event(row["id"], "state", f"{TaskState.BLOCKED.value}: needs reconciliation")
            recovered.append(row["id"])
        return recovered

    # ── reads ────────────────────────────────────────────────────────────
    def _record(self, row: sqlite3.Row, events: Optional[List[Dict[str, Any]]] = None) -> TaskRecord:
        return TaskRecord(id=row["id"], text=row["text"], interface=row["interface"], state=TaskState(row["state"]),
                          created_at=row["created_at"], updated_at=row["updated_at"], parent_id=row["parent_id"],
                          owner_pid=row["owner_pid"], cancel_requested=bool(row["cancel_requested"]),
                          outcome=row["outcome"], result_status=row["result_status"],
                          response_type=row["response_type"], error=row["error"], events=events or [])

    def get(self, task_id: str) -> Optional[TaskRecord]:
        with self._lock:
            row = self._db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None:
                return None
            events = [dict(e) for e in self._db.execute(
                "SELECT at, kind, message FROM task_events WHERE task_id=? ORDER BY id", (task_id,))]
        return self._record(row, events)

    def list(self, limit: int = 50, *, active_only: bool = False) -> List[TaskRecord]:
        sql, params = "SELECT * FROM tasks", []
        if active_only:
            sql += " WHERE state NOT IN (%s)" % ",".join("?" * len(TERMINAL_STATES))
            params = [s.value for s in TERMINAL_STATES]
        sql += " ORDER BY created_at DESC LIMIT ?"
        with self._lock:
            rows = self._db.execute(sql, params + [int(limit)]).fetchall()
        return [self._record(r) for r in rows]

    def cancel_requested_for(self, task_ids: List[str]) -> List[str]:
        if not task_ids:
            return []
        with self._lock:
            rows = self._db.execute("SELECT id FROM tasks WHERE cancel_requested=1 AND id IN (%s)"
                                    % ",".join("?" * len(task_ids)), task_ids).fetchall()
        return [r["id"] for r in rows]

    def export(self, task_id: str) -> Dict[str, Any]:
        """Redacted report of one task (FR-019): everything stored was redacted on the way in."""
        rec = self.get(task_id)
        return rec.to_dict() if rec else {}

    def close(self) -> None:
        with self._lock:
            self._db.close()


def dumps(rec: TaskRecord) -> str:
    return json.dumps(rec.to_dict(), ensure_ascii=False, indent=2)
