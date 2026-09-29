"""
Long-term memory for TOM, backed by Hindsight (https://github.com/vectorize-io/hindsight).

TOM's other memories (chat_memory, RAG) are transcripts of what was *said*.
This layer stores what TOM *learned*: the user's corrections, preferences and
the outcome of every task — and brings the relevant ones back before TOM acts.

    retain()  — after a correction, a stated preference, or a finished task
    recall()  — before TOM decides how to execute a request
    reflect() — on demand: "what have you learned about how I work?", and to
                turn recalled facts into structured rules (e.g. folder rules)

Design rules
  * Never block or crash a task. Every call is time-boxed; failures degrade to
    "no memory" and are reported in status(), not raised.
  * Retains are fire-and-forget on a background thread. If Hindsight is
    unreachable they are queued to disk and flushed on the next success.
  * A small local journal mirrors what was retained so the UI can show it
    instantly, even offline.

Configuration (.env)
  HINDSIGHT_API_KEY    — Hindsight Cloud key (enables Cloud by default)
  HINDSIGHT_BASE_URL   — default https://api.hindsight.vectorize.io
                         (use http://localhost:8888 for a self-hosted server)
  HINDSIGHT_BANK_ID    — optional; default "tom-<stable machine id>"
  HINDSIGHT_ENABLED    — set to 0 to switch the layer off
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.project_paths import PROJECT_ROOT

CLOUD_URL = "https://api.hindsight.vectorize.io"
STATE_DIR = Path(PROJECT_ROOT) / "tom_brain" / "hindsight"
JOURNAL_FILE = STATE_DIR / "journal.jsonl"
PENDING_FILE = STATE_DIR / "pending.jsonl"
BANK_FILE = STATE_DIR / "bank_id.txt"

BANK_MISSION = (
    "TOM is a desktop automation agent that works for one person on their own "
    "computer. Learn how this person likes work done: their corrections, explicit "
    "rules, preferences for file organization, email tone and sign-offs, document "
    "formats, apps and tools they use, and which past attempts succeeded or failed. "
    "Prefer the most recent instruction when two conflict."
)

# Tags TOM writes. Kept small and stable so recall filters stay meaningful.
TAG_PREFERENCE = "preference"
TAG_CORRECTION = "correction"
TAG_TASK = "task"

# Session-scoped tag, per Hindsight's tag naming conventions
# (https://hindsight — tags: `session:<id>` so one conversation's memories can
# be filtered or audited later). The same id is sent as `document_id`, which is
# how Hindsight groups a session's turns into one document instead of creating
# a duplicate document on every retain.
SESSION_TAG_PREFIX = "session:"


def session_tag(session_id: str) -> str:
    """Filter tag for one chat session; "" for an unknown session."""
    return f"{SESSION_TAG_PREFIX}{session_id}" if (session_id or "").strip() else ""


def session_document_id(session_id: str) -> str:
    """Stable Hindsight document id for a chat session."""
    return f"session-{session_id}" if (session_id or "").strip() else ""


@dataclass
class MemoryHit:
    text: str
    type: str = ""
    tags: List[str] = field(default_factory=list)
    id: str = ""
    when: str = ""

    @property
    def is_preference(self) -> bool:
        return TAG_PREFERENCE in self.tags or TAG_CORRECTION in self.tags

    def to_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "type": self.type, "tags": list(self.tags),
                "id": self.id, "when": self.when}


def _default_bank_id() -> str:
    """Stable per-installation bank id, persisted so memory survives restarts."""
    try:
        if BANK_FILE.exists():
            value = BANK_FILE.read_text(encoding="utf-8").strip()
            if value:
                return value
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        value = f"tom-{uuid.uuid4().hex[:12]}"
        BANK_FILE.write_text(value, encoding="utf-8")
        return value
    except OSError:
        return "tom-default"


class HindsightMemory:
    """Thin, failure-tolerant wrapper around the Hindsight Python client."""

    def __init__(self, client: Any = None, bank_id: Optional[str] = None,
                 timeout: Optional[float] = None, state_dir: Optional[Path] = None) -> None:
        self.state_dir = Path(state_dir or os.environ.get("TOM_MEMORY_STATE_DIR") or STATE_DIR)
        self.journal_file = self.state_dir / JOURNAL_FILE.name
        self.pending_file = self.state_dir / PENDING_FILE.name
        self.base_url = (os.environ.get("HINDSIGHT_BASE_URL") or CLOUD_URL).rstrip("/")
        self.api_key = os.environ.get("HINDSIGHT_API_KEY", "").strip() or None
        self.bank_id = bank_id or os.environ.get("HINDSIGHT_BANK_ID", "").strip() or _default_bank_id()
        self.timeout = float(timeout or os.environ.get("HINDSIGHT_TIMEOUT_SECONDS", "12"))
        self.last_error: str = ""
        self.last_recall: List[MemoryHit] = []
        self.last_recall_query: str = ""
        self._bank_ready = False
        self._lock = threading.Lock()
        self._retain_q: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._inflight = 0
        self.stats = {"retained": 0, "recalled": 0, "reflected": 0, "failed": 0, "queued": 0}

        self.client = client
        self.enabled = os.environ.get("HINDSIGHT_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")
        if self.client is None and self.enabled:
            self.client = self._build_client()

    # ── setup ────────────────────────────────────────────────────────────
    def _build_client(self) -> Any:
        is_cloud = self.base_url.startswith(CLOUD_URL)
        if is_cloud and not self.api_key:
            self.last_error = ("HINDSIGHT_API_KEY is not set. Add it to .env "
                               "(or point HINDSIGHT_BASE_URL at a self-hosted server).")
            return None
        try:
            from hindsight_client import Hindsight
        except ImportError:
            self.last_error = "hindsight-client is not installed. Fix: pip install hindsight-client"
            return None
        try:
            return Hindsight(base_url=self.base_url, api_key=self.api_key,
                             timeout=self.timeout, max_attempts=2)
        except Exception as exc:  # bad URL etc.
            self.last_error = f"Could not create Hindsight client: {exc}"
            return None

    @property
    def available(self) -> bool:
        return bool(self.enabled and self.client is not None)

    def _ensure_bank(self) -> None:
        if self._bank_ready or not self.available:
            return
        with self._lock:
            if self._bank_ready:
                return
            try:
                self.client.create_bank(bank_id=self.bank_id, name="TOM — personal workflow memory",
                                        mission=BANK_MISSION)
            except Exception as exc:
                # Already-exists (409) is fine; anything else is surfaced but not fatal —
                # Hindsight also creates banks implicitly on first retain.
                msg = str(exc)
                if "409" not in msg and "exist" not in msg.lower():
                    self.last_error = f"create_bank: {msg[:200]}"
            self._bank_ready = True

    # ── retain ───────────────────────────────────────────────────────────
    def retain(self, content: str, *, context: str = "", tags: Optional[List[str]] = None,
               metadata: Optional[Dict[str, str]] = None, wait: bool = False,
               timestamp: Optional[datetime] = None, index_now: bool = False,
               session_id: str = "") -> bool:
        """Store a memory. Non-blocking by default (background thread + disk queue).

        index_now — ask Hindsight to finish fact extraction before returning
        (used for corrections, so they are recallable on the very next request).
        timestamp — when it happened (defaults to now; seeding uses past dates).
        session_id — the chat session this happened in. Adds a `session:<id>`
        tag for filtering/audit and sends it as the stable `document_id`, so a
        conversation's memories group together instead of fragmenting.
        """
        content = (content or "").strip()
        if not content:
            return False
        when = timestamp or datetime.now(timezone.utc)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        tag_list = list(tags or [])
        tag = session_tag(session_id)
        if tag and tag not in tag_list:
            tag_list.append(tag)
        meta = {k: str(v)[:200] for k, v in (metadata or {}).items()}
        if tag:
            meta.setdefault("session_id", str(session_id)[:200])
        item = {"content": content[:4000], "context": context[:200], "tags": tag_list,
                "metadata": meta,
                "timestamp": when.isoformat(timespec="seconds"), "index_now": bool(index_now)}
        document_id = session_document_id(session_id)
        if document_id:
            item["document_id"] = document_id
        self._journal(item)
        if not self.available:
            self._queue_pending(item)
            return False
        if wait:
            return self._send_retain(item)
        with self._lock:
            self._inflight += 1
        self._retain_q.put(item)
        self._start_worker()
        return True

    def _send_retain(self, item: Dict[str, Any]) -> bool:
        self._ensure_bank()
        try:
            self.client.retain(
                bank_id=self.bank_id,
                content=item["content"],
                context=item.get("context") or None,
                timestamp=datetime.fromisoformat(item["timestamp"]),
                tags=item.get("tags") or None,
                metadata=item.get("metadata") or None,
                retain_async=not item.get("index_now", False),
                document_id=item.get("document_id") or None,
            )
            self.stats["retained"] += 1
            return True
        except Exception as exc:
            self.stats["failed"] += 1
            self.last_error = f"retain: {str(exc)[:200]}"
            self._queue_pending(item)
            return False

    def _start_worker(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._drain, name="hindsight-retain", daemon=True)
        self._worker.start()

    def _drain(self) -> None:
        while True:
            try:
                item = self._retain_q.get(timeout=5)
            except queue.Empty:
                return
            try:
                if self._send_retain(item):
                    self.flush_pending()
            finally:
                with self._lock:
                    self._inflight -= 1

    def flush(self, timeout: float = 10.0) -> None:
        """Wait for queued retains to be sent (used by scripts and tests)."""
        deadline = time.time() + timeout
        while time.time() < deadline and self._inflight > 0:
            time.sleep(0.05)

    # ── offline queue + journal ──────────────────────────────────────────
    def _append_jsonl(self, path: Path, item: Dict[str, Any]) -> None:
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def _journal(self, item: Dict[str, Any]) -> None:
        self._append_jsonl(self.journal_file, item)

    def _queue_pending(self, item: Dict[str, Any]) -> None:
        self.stats["queued"] += 1
        self._append_jsonl(self.pending_file, item)

    def flush_pending(self) -> int:
        """Re-send retains that were queued while Hindsight was unreachable."""
        if not self.available or not self.pending_file.exists():
            return 0
        with self._lock:
            try:
                lines = self.pending_file.read_text(encoding="utf-8").splitlines()
                self.pending_file.unlink()
            except OSError:
                return 0
        sent = 0
        for i, line in enumerate(lines):
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if self._send_retain(item):
                sent += 1
            else:
                # Still offline; _send_retain already re-queued this item.
                # Re-queue the remaining, not-yet-attempted lines too, so
                # they aren't silently dropped (the file was unlinked above).
                remaining = lines[i + 1:]
                if remaining:
                    try:
                        self.state_dir.mkdir(parents=True, exist_ok=True)
                        with self.pending_file.open("a", encoding="utf-8") as fh:
                            for line_text in remaining:
                                fh.write(line_text + "\n")
                        self.stats["queued"] += len(remaining)
                    except OSError:
                        pass
                break
        return sent

    def recent_journal(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Most recent things TOM retained (local mirror; newest first)."""
        if not self.journal_file.exists():
            return []
        try:
            lines = self.journal_file.read_text(encoding="utf-8").splitlines()[-limit:]
        except OSError:
            return []
        out = []
        for line in reversed(lines):
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def pending_count(self) -> int:
        try:
            return (len(self.pending_file.read_text(encoding="utf-8").splitlines())
                    if self.pending_file.exists() else 0)
        except OSError:
            return 0

    # ── recall ───────────────────────────────────────────────────────────
    def recall(self, query: str, *, tags: Optional[List[str]] = None, limit: int = 6,
               budget: str = "low", max_tokens: int = 1200) -> List[MemoryHit]:
        """Facts relevant to `query`, most relevant first. Never raises."""
        self.last_recall_query = query
        if not self.available or not (query or "").strip():
            self.last_recall = []
            return []
        self._ensure_bank()
        try:
            resp = self.client.recall(bank_id=self.bank_id, query=query[:800], budget=budget,
                                      max_tokens=max_tokens, tags=tags or None,
                                      tags_match="any")
            hits = [self._to_hit(r) for r in (getattr(resp, "results", None) or [])]
            hits = [h for h in hits if h.text][:limit]
            self.stats["recalled"] += 1
            self.last_recall = hits
            if self.pending_count():
                threading.Thread(target=self.flush_pending, daemon=True).start()
            return hits
        except Exception as exc:
            self.stats["failed"] += 1
            self.last_error = f"recall: {str(exc)[:200]}"
            self.last_recall = []
            return []

    async def arecall(self, query: str, **kwargs: Any) -> List[MemoryHit]:
        """Async, hard time-boxed recall — a slow memory server never stalls a task."""
        try:
            return await asyncio.wait_for(asyncio.to_thread(self.recall, query, **kwargs),
                                          timeout=self.timeout + 2)
        except asyncio.TimeoutError:
            self.last_error = f"recall: timed out after {self.timeout:.0f}s"
            return []

    @staticmethod
    def _to_hit(result: Any) -> MemoryHit:
        get = (lambda k: result.get(k)) if isinstance(result, dict) else (lambda k: getattr(result, k, None))
        when = get("mentioned_at") or get("occurred_start") or ""
        return MemoryHit(text=str(get("text") or "").strip(), type=str(get("type") or ""),
                         tags=list(get("tags") or []), id=str(get("id") or ""),
                         when=str(when)[:10] if when else "")

    # ── reflect ──────────────────────────────────────────────────────────
    def reflect(self, query: str, *, context: str = "", budget: str = "low",
                response_schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Reason over the whole bank. Returns {"text", "structured", "ok"}."""
        if not self.available:
            return {"ok": False, "text": "", "structured": None, "error": self.last_error}
        self._ensure_bank()
        try:
            resp = self.client.reflect(bank_id=self.bank_id, query=query, budget=budget,
                                       context=context or None, response_schema=response_schema)
            self.stats["reflected"] += 1
            return {"ok": True, "text": (getattr(resp, "text", "") or "").strip(),
                    "structured": getattr(resp, "structured_output", None)}
        except Exception as exc:
            self.stats["failed"] += 1
            self.last_error = f"reflect: {str(exc)[:200]}"
            return {"ok": False, "text": "", "structured": None, "error": self.last_error}

    async def areflect(self, query: str, timeout: float = 45.0, **kwargs: Any) -> Dict[str, Any]:
        try:
            return await asyncio.wait_for(asyncio.to_thread(self.reflect, query, **kwargs),
                                          timeout=timeout)
        except asyncio.TimeoutError:
            self.last_error = f"reflect: timed out after {timeout:.0f}s"
            return {"ok": False, "text": "", "structured": None, "error": self.last_error}

    # ── browsing ─────────────────────────────────────────────────────────
    def list_memories(self, limit: int = 25) -> List[MemoryHit]:
        if not self.available:
            return []
        try:
            resp = self.client.list_memories(bank_id=self.bank_id, limit=limit)
            return [self._to_hit(i) for i in (getattr(resp, "items", None) or [])]
        except Exception as exc:
            self.last_error = f"list_memories: {str(exc)[:200]}"
            return []

    # ── status ───────────────────────────────────────────────────────────
    def status(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "enabled": self.enabled,
            "base_url": self.base_url,
            "bank_id": self.bank_id,
            "pending": self.pending_count(),
            "last_error": self.last_error,
            **self.stats,
        }

    def status_line(self) -> str:
        if not self.enabled:
            return "Long-term memory: OFF (HINDSIGHT_ENABLED=0)"
        if not self.available:
            return f"Long-term memory: OFFLINE — {self.last_error or 'not configured'}"
        where = "Hindsight Cloud" if self.base_url.startswith(CLOUD_URL) else f"Hindsight @ {self.base_url}"
        extra = f", {self.pending_count()} queued" if self.pending_count() else ""
        return f"Long-term memory: ONLINE — {where}, bank '{self.bank_id}'{extra}"


_instance: Optional[HindsightMemory] = None


def get_memory() -> HindsightMemory:
    global _instance
    if _instance is None:
        _instance = HindsightMemory()
    return _instance


def set_memory(memory: Optional[HindsightMemory]) -> None:
    """Swap the singleton (tests, demo scripts)."""
    global _instance
    _instance = memory
