"""TaskService — the single entry point every interface submits through (PRD supplement §S3, R2).

R2 scope: wrap the existing TomAgent pipeline (passed in as `runner`) so every request gets a task
id, a durable lifecycle record, cross-process cancellation and an honest terminal state. Planning,
typed tools and policy checks arrive in R3/R4 behind this same API.
"""
from __future__ import annotations

import asyncio
import contextvars
import threading
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from tom_core.tasks.models import TaskRecord, TaskState
from tom_core.tasks.store import TaskStore, open_store

_current_task: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("tom_current_task", default=None)

# Response types whose "success" is the answer itself (read-only, nothing outside TOM changed),
# so delivering it is the verification. Everything else that claims success without evidence is
# UNVERIFIED (FR-008: never mark a side effect successful just because a handler returned).
OBSERVATION_TYPES = frozenset({
    "chat", "voice_chat", "capabilities", "health", "capability_health", "skill_usage", "logs",
    "voice_check", "memory", "memory_status", "memory_recall", "memory_reflect", "feedback",
    "explanation", "web_search", "screen_read",
})
FAILED_STATUSES = frozenset({"error", "unsupported", "unhandled", "failed", "timeout"})

Runner = Callable[[str], Awaitable[Dict[str, Any]]]


def classify(result: Any) -> Tuple[TaskState, str]:
    """Terminal state for a legacy handler result, plus a short note for the event log."""
    if not isinstance(result, dict):
        return TaskState.UNVERIFIED, "handler returned a non-dict result"
    if result.get("safe") is False:
        return TaskState.REJECTED, "blocked by safety policy"
    status = str(result.get("status", "")).lower()
    if status in FAILED_STATUSES:
        return TaskState.FAILED, status
    if status == "cancelled":
        return TaskState.REJECTED, "declined by the user"
    if status == "blocked":
        return TaskState.REJECTED, "blocked by safety policy"
    if status == "needs_input":
        return TaskState.NEEDS_INPUT, "more information needed"
    if status == "success":
        if result.get("verified") is True:
            return TaskState.SUCCEEDED, "verified"
        if str(result.get("response_type", "")) in OBSERVATION_TYPES:
            return TaskState.SUCCEEDED, "answer delivered"
        return TaskState.UNVERIFIED, "reported success without independent evidence"
    return TaskState.UNVERIFIED, f"status '{status or 'none'}'"


class TaskService:
    def __init__(self, runner: Runner, store: Optional[TaskStore] = None, *, cancel_poll_seconds: float = 1.0) -> None:
        self.runner = runner
        self.store = store or open_store()
        self.cancel_poll_seconds = cancel_poll_seconds
        self._running: Dict[str, Tuple[asyncio.Task, asyncio.AbstractEventLoop]] = {}
        self._lock = threading.Lock()
        self._watchers: Dict[int, asyncio.Task] = {}
        self.recovered: List[str] = self.store.recover_interrupted()

    # ── the contract interfaces use (§S3) ────────────────────────────────
    async def submit_task(self, text: str, interface: str = "unknown") -> Dict[str, Any]:
        """Run one request as a task. Returns the handler's result plus task_id / task_state."""
        rec = self.store.create(text, interface, parent_id=_current_task.get())
        token = _current_task.set(rec.id)
        task = asyncio.current_task()
        loop = asyncio.get_running_loop()
        try:
            self.store.transition(rec.id, TaskState.RUNNING)
            if task is not None:
                with self._lock:
                    self._running[rec.id] = (task, loop)
                self._ensure_watcher(loop)
            try:
                result = await self.runner(text)
            except asyncio.CancelledError:
                self._finish(rec.id, TaskState.CANCELLED, note="cancelled", error="Cancelled before it finished.")
                raise
            except Exception as exc:
                self._finish(rec.id, TaskState.FAILED, note="exception", error=f"{type(exc).__name__}: {exc}")
                raise
            state, note = classify(result)
            result = dict(result) if isinstance(result, dict) else {"status": "success", "message": str(result)}
            if state is TaskState.REJECTED and note.startswith("blocked") and "status" not in result:
                result["status"] = "blocked"
            self._finish(rec.id, state, note=note, outcome=str(result.get("message", "")),
                         result_status=str(result.get("status", "")),
                         response_type=str(result.get("response_type", "")))
            result["task_id"] = rec.id
            result["task_state"] = state.value
            return result
        finally:
            with self._lock:
                self._running.pop(rec.id, None)
            _current_task.reset(token)

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        return self.store.get(task_id)

    def list_tasks(self, limit: int = 50, *, active_only: bool = False) -> List[TaskRecord]:
        return self.store.list(limit, active_only=active_only)

    def cancel_task(self, task_id: str) -> bool:
        """Request cancellation. Thread-safe; works for tasks owned by another TOM process too."""
        requested = self.store.request_cancel(task_id)
        self._cancel_local(task_id)
        return requested

    def cancel_all(self) -> List[str]:
        """Emergency stop (PRD §11.2): cancel every task this process is running."""
        with self._lock:
            ids = list(self._running)
        for task_id in ids:
            self.cancel_task(task_id)
        return ids

    # ── internals ────────────────────────────────────────────────────────
    def _finish(self, task_id: str, state: TaskState, *, note: str = "", **fields: Any) -> None:
        try:
            self.store.transition(task_id, state, note=note, **fields)
        except Exception as exc:          # never let bookkeeping hide the real result
            self.store.add_event(task_id, "store_error", str(exc))

    def _cancel_local(self, task_id: str) -> None:
        with self._lock:
            entry = self._running.get(task_id)
        if entry is not None:
            task, loop = entry
            loop.call_soon_threadsafe(task.cancel)

    def _ensure_watcher(self, loop: asyncio.AbstractEventLoop) -> None:
        key = id(loop)
        watcher = self._watchers.get(key)
        if watcher is None or watcher.done():
            self._watchers[key] = loop.create_task(self._watch_cancellations(loop))

    async def _watch_cancellations(self, loop: asyncio.AbstractEventLoop) -> None:
        """Cancellation requested from another interface/process reaches the running task (AT-012)."""
        while True:
            await asyncio.sleep(self.cancel_poll_seconds)
            with self._lock:
                mine = [tid for tid, (_t, lp) in self._running.items() if lp is loop]
            if not mine:
                return
            for task_id in await asyncio.to_thread(self.store.cancel_requested_for, mine):
                self._cancel_local(task_id)
