"""On-machine long-term memory with the same client surface tools/hindsight_memory.py drives.

SQLite + FTS5 (PRD §9.2 "SQLite first"): nothing leaves the machine. Implements the subset of
hindsight_client.Hindsight that HindsightMemory calls — create_bank, retain, recall, reflect,
list_memories — so the wrapper's journal, offline queue and time-boxing keep working unchanged.

On first use an empty store is seeded from the wrapper's local journal (tom_brain/hindsight/
journal.jsonl), which mirrors everything TOM ever retained — so switching from Hindsight Cloud to
local keeps existing memories (TOM-MIG-003). Seeding never deletes or modifies the journal.

reflect() has no language model: it returns the relevant stored preferences/corrections as text
and never structured output; callers already fall back to deterministic parsing when that is None.
"""
from __future__ import annotations

import json
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional

SCHEMA_VERSION = 1

_STOPWORDS = {
    "the", "and", "for", "are", "was", "you", "your", "with", "that", "this", "what", "how", "does",
    "user", "want", "wants", "should", "about", "into", "from", "have", "has", "all", "any", "can",
    "where", "when", "which", "who", "why", "their", "they", "them", "other", "request", "please",
}


def _fts_query(text: str) -> str:
    words = [w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) > 2 and w not in _STOPWORDS]
    return " OR ".join(f'"{w}"' for w in dict.fromkeys(words))


class LocalMemoryClient:
    def __init__(self, db_path: Path, *, seed_journal: Optional[Path] = None) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._migrate()
        self.seeded = self._seed(seed_journal) if seed_journal else 0

    # ── schema ───────────────────────────────────────────────────────────
    def _migrate(self) -> None:
        with self._lock, self._db:
            self._db.executescript("""
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
                CREATE TABLE IF NOT EXISTS memories (
                    id          INTEGER PRIMARY KEY,
                    bank_id     TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    context     TEXT,
                    tags        TEXT NOT NULL DEFAULT '[]',
                    metadata    TEXT NOT NULL DEFAULT '{}',
                    document_id TEXT,
                    occurred_at TEXT NOT NULL,
                    source      TEXT NOT NULL DEFAULT 'tom',
                    -- Bank-agnostic: the journal seed ('*') and a later flush of the offline queue
                    -- (real bank id) carry the same item, which must not be stored twice.
                    UNIQUE (content, occurred_at)
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    content, context, content='memories', content_rowid='id', tokenize='porter unicode61');
                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                    INSERT INTO memories_fts(rowid, content, context) VALUES (new.id, new.content, new.context);
                END;
                CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, content, context)
                    VALUES ('delete', old.id, old.content, old.context);
                END;
            """)
            self._db.execute("INSERT OR IGNORE INTO meta VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),))

    def _seed(self, journal: Path) -> int:
        """Import the wrapper's journal once, into the store's bank-agnostic seed area."""
        with self._lock:
            done = self._db.execute("SELECT value FROM meta WHERE key='seeded_from_journal'").fetchone()
        if done or not journal.is_file():
            return 0
        items: List[Dict[str, Any]] = []
        for line in journal.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if isinstance(item, dict) and str(item.get("content", "")).strip():
                items.append(item)
        added = self._insert_many("*", items, source="journal")
        with self._lock, self._db:
            self._db.execute("INSERT OR REPLACE INTO meta VALUES ('seeded_from_journal', ?)",
                             (datetime.now(timezone.utc).isoformat(timespec="seconds"),))
        return added

    def _insert_many(self, bank_id: str, items: Iterable[Dict[str, Any]], source: str) -> int:
        added = 0
        with self._lock, self._db:
            for it in items:
                cur = self._db.execute(
                    "INSERT OR IGNORE INTO memories (bank_id, content, context, tags, metadata, document_id,"
                    " occurred_at, source) VALUES (?,?,?,?,?,?,?,?)",
                    (bank_id, str(it["content"])[:4000], it.get("context") or None,
                     json.dumps(list(it.get("tags") or [])), json.dumps(dict(it.get("metadata") or {})),
                     it.get("document_id") or None,
                     str(it.get("timestamp") or datetime.now(timezone.utc).isoformat(timespec="seconds")),
                     source))
                added += cur.rowcount
        return added

    # ── hindsight_client-compatible surface ──────────────────────────────
    def create_bank(self, bank_id: str, **_kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(bank_id=bank_id)

    def retain(self, bank_id: str, content: str, *, context: Optional[str] = None, timestamp: Any = None,
               tags: Optional[List[str]] = None, metadata: Optional[Dict[str, str]] = None,
               document_id: Optional[str] = None, **_kwargs: Any) -> SimpleNamespace:
        when = timestamp.isoformat(timespec="seconds") if isinstance(timestamp, datetime) else timestamp
        self._insert_many(bank_id, [{"content": content, "context": context, "tags": tags, "metadata": metadata,
                                     "document_id": document_id, "timestamp": when}], source="tom")
        return SimpleNamespace(success=True, bank_id=bank_id, items_count=1)

    def _rows(self, bank_id: str, *, match: str = "", tags: Optional[List[str]] = None,
              limit: int = 50) -> List[sqlite3.Row]:
        where = ["m.bank_id IN (?, '*')"]
        params: List[Any] = [bank_id]
        if tags:
            where.append("(" + " OR ".join("m.tags LIKE ?" for _ in tags) + ")")
            params += [f'%"{t}"%' for t in tags]
        if match:
            sql = ("SELECT m.*, bm25(memories_fts) AS rank FROM memories_fts JOIN memories m ON m.id = memories_fts.rowid "
                   f"WHERE memories_fts MATCH ? AND {' AND '.join(where)} ORDER BY rank, m.occurred_at DESC LIMIT ?")
            params = [match] + params + [limit]
        else:
            sql = f"SELECT m.* FROM memories m WHERE {' AND '.join(where)} ORDER BY m.occurred_at DESC LIMIT ?"
            params.append(limit)
        with self._lock:
            return self._db.execute(sql, params).fetchall()

    @staticmethod
    def _result(row: sqlite3.Row) -> SimpleNamespace:
        tags = json.loads(row["tags"] or "[]")
        kind = "opinion" if ("preference" in tags or "correction" in tags) else "experience"
        return SimpleNamespace(text=row["content"], type=kind, tags=tags, id=str(row["id"]),
                               mentioned_at=row["occurred_at"], occurred_start=None)

    def recall(self, bank_id: str, query: str, *, tags: Optional[List[str]] = None, **_kwargs: Any) -> SimpleNamespace:
        match = _fts_query(query)
        rows = self._rows(bank_id, match=match, tags=tags, limit=25) if match else []
        return SimpleNamespace(results=[self._result(r) for r in rows])

    def reflect(self, bank_id: str, query: str, **_kwargs: Any) -> SimpleNamespace:
        rows = self._rows(bank_id, tags=["preference", "correction"], limit=40)
        seen, lines = set(), []
        for r in rows:                                   # newest first, so the latest instruction wins
            words = json.loads(r["metadata"] or "{}").get("user_words") or r["content"]
            key = words.strip().lower()
            if key and key not in seen:
                seen.add(key)
                lines.append(f"- {words.strip()}")
        text = "\n".join(lines) if lines else ""
        return SimpleNamespace(text=text, structured_output=None)

    def list_memories(self, bank_id: str, limit: int = 100, **_kwargs: Any) -> SimpleNamespace:
        rows = self._rows(bank_id, limit=limit)
        with self._lock:
            total = self._db.execute("SELECT COUNT(*) FROM memories WHERE bank_id IN (?, '*')",
                                     (bank_id,)).fetchone()[0]
        return SimpleNamespace(items=[self._result(r) for r in rows], total=int(total))

    # ── user controls (PRD §9.2: inspect, correct, delete) ───────────────
    def delete_memory(self, memory_id: str) -> bool:
        with self._lock, self._db:
            return self._db.execute("DELETE FROM memories WHERE id = ?", (int(memory_id),)).rowcount > 0

    def close(self) -> None:
        with self._lock:
            self._db.close()
