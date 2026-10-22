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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional

SCHEMA_VERSION = 2
# v2 (R5, PRD §9.2): provenance (where a memory came from), confidence, retention (expires_at),
# corrections that supersede the memory they fix, and tombstones so a deleted memory never returns.
DEFAULT_CONFIDENCE = 0.6           # something TOM observed
RULE_CONFIDENCE = 0.9              # the user stated a preference / correction
CORRECTED_CONFIDENCE = 0.95        # the user corrected a memory by hand
TASK_RETENTION_DAYS = 180          # task history expires; rules and corrections do not

_STOPWORDS = {
    "the", "and", "for", "are", "was", "you", "your", "with", "that", "this", "what", "how", "does",
    "user", "want", "wants", "should", "about", "into", "from", "have", "has", "all", "any", "can",
    "where", "when", "which", "who", "why", "their", "they", "them", "other", "request", "please",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
                CREATE TABLE IF NOT EXISTS forgotten (content TEXT NOT NULL, occurred_at TEXT NOT NULL,
                                                      PRIMARY KEY (content, occurred_at));
            """)
            have = {r[1] for r in self._db.execute("PRAGMA table_info(memories)")}
            for col, decl in (("confidence", f"REAL NOT NULL DEFAULT {DEFAULT_CONFIDENCE}"),
                              ("expires_at", "TEXT"), ("superseded_by", "INTEGER"),
                              ("provenance", "TEXT NOT NULL DEFAULT '{}'")):
                if col not in have:
                    self._db.execute(f"ALTER TABLE memories ADD COLUMN {col} {decl}")
            self._db.execute("INSERT OR REPLACE INTO meta VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),))
        self.expired = self.prune_expired()

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

    @staticmethod
    def _provenance(source: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        prov = {"source": source}
        try:
            from tom_core.tasks.service import current_interface, current_task_id
            prov.update({k: v for k, v in (("interface", current_interface()), ("task_id", current_task_id())) if v})
        except Exception:
            pass
        for k in ("session_id", "corrects"):
            if meta.get(k):
                prov[k] = str(meta[k])
        return prov

    @staticmethod
    def _confidence_and_expiry(tags: List[str], meta: Dict[str, Any], when: str) -> "tuple[float, Optional[str]]":
        rule = "preference" in tags or "correction" in tags
        try:
            conf = float(meta["confidence"]) if "confidence" in meta else (RULE_CONFIDENCE if rule else DEFAULT_CONFIDENCE)
        except (TypeError, ValueError):
            conf = DEFAULT_CONFIDENCE
        days = meta.get("expires_days")
        if days is None and not rule:
            days = TASK_RETENTION_DAYS
        expires = None
        if days not in (None, "", "never"):
            try:
                start = datetime.fromisoformat(when.replace("Z", "+00:00"))
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                expires = (start + timedelta(days=float(days))).isoformat(timespec="seconds")
            except ValueError:
                expires = None
        return max(0.0, min(1.0, conf)), expires

    def _insert_many(self, bank_id: str, items: Iterable[Dict[str, Any]], source: str) -> int:
        added = 0
        with self._lock, self._db:
            for it in items:
                content = str(it["content"])[:4000]
                when = str(it.get("timestamp") or _now())
                if self._db.execute("SELECT 1 FROM forgotten WHERE content=? AND occurred_at=?",
                                    (content, when)).fetchone():
                    continue                                    # the user deleted it: never re-added
                tags = list(it.get("tags") or [])
                meta = dict(it.get("metadata") or {})
                conf, expires = self._confidence_and_expiry(tags, meta, when)
                cur = self._db.execute(
                    "INSERT OR IGNORE INTO memories (bank_id, content, context, tags, metadata, document_id,"
                    " occurred_at, source, confidence, expires_at, provenance) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (bank_id, content, it.get("context") or None, json.dumps(tags), json.dumps(meta),
                     it.get("document_id") or None, when, source, conf, expires,
                     json.dumps(self._provenance(source, meta))))
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
        where = ["m.bank_id IN (?, '*')", "m.superseded_by IS NULL", "(m.expires_at IS NULL OR m.expires_at > ?)"]
        params: List[Any] = [bank_id, _now()]
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
                               mentioned_at=row["occurred_at"], occurred_start=None,
                               confidence=row["confidence"], source=row["source"],
                               provenance=json.loads(row["provenance"] or "{}"))

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
            total = self._db.execute(
                "SELECT COUNT(*) FROM memories WHERE bank_id IN (?, '*') AND superseded_by IS NULL"
                " AND (expires_at IS NULL OR expires_at > ?)", (bank_id, _now())).fetchone()[0]
        return SimpleNamespace(items=[self._result(r) for r in rows], total=int(total))

    # ── user controls (PRD §9.2: inspect, correct, delete) ───────────────
    def inspect_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Everything stored about one memory, including where it came from and what it replaced."""
        with self._lock:
            row = self._db.execute("SELECT * FROM memories WHERE id = ?", (int(memory_id),)).fetchone()
        if row is None:
            return None
        out = {k: row[k] for k in row.keys()}
        out["tags"] = json.loads(out["tags"] or "[]")
        out["metadata"] = json.loads(out["metadata"] or "{}")
        out["provenance"] = json.loads(out["provenance"] or "{}")
        return out

    def correct_memory(self, memory_id: str, new_text: str) -> Optional[str]:
        """Replace a memory with the user's corrected wording. The old one is kept for audit but is
        superseded: it is never recalled again. Returns the new memory's id (None if no such id)."""
        old = self.inspect_memory(memory_id)
        new_text = (new_text or "").strip()
        if old is None or not new_text:
            return None
        tags = [t for t in old["tags"] if t != "correction"] + ["correction"]
        meta = {**old["metadata"], "user_words": new_text, "corrects": str(old["id"]),
                "confidence": CORRECTED_CONFIDENCE, "expires_days": "never"}
        when = _now()
        self._insert_many(old["bank_id"], [{"content": new_text, "context": old["context"], "tags": tags,
                                            "metadata": meta, "timestamp": when}], source="user")
        with self._lock, self._db:
            row = self._db.execute("SELECT id FROM memories WHERE content=? AND occurred_at=?",
                                   (new_text, when)).fetchone()
            if row is None:
                return None
            self._db.execute("UPDATE memories SET superseded_by=? WHERE id=?", (row[0], int(memory_id)))
        return str(row[0])

    def delete_memory(self, memory_id: str) -> bool:
        """Delete for good: removed from the store and tombstoned, so a queued copy can't bring it back."""
        with self._lock, self._db:
            row = self._db.execute("SELECT content, occurred_at FROM memories WHERE id = ?",
                                   (int(memory_id),)).fetchone()
            if row is None:
                return False
            self._db.execute("INSERT OR IGNORE INTO forgotten VALUES (?, ?)", (row[0], row[1]))
            return self._db.execute("DELETE FROM memories WHERE id = ?", (int(memory_id),)).rowcount > 0

    def prune_expired(self) -> int:
        """Retention: drop memories whose expiry date has passed."""
        with self._lock, self._db:
            return self._db.execute("DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at <= ?",
                                    (_now(),)).rowcount

    def close(self) -> None:
        with self._lock:
            self._db.close()
