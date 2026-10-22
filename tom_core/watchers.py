"""C11 proactive monitoring (opt-in: TOM_WATCHERS=1). Notify only on actionable *changes*.

Each watcher returns its current problem (or None). A notice is raised when a problem appears and
once more when it clears — never repeated while it persists. Watchers only
observe: they never kill processes or delete files (RRM-008).
"""
from __future__ import annotations

import os
import shutil
import threading
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from tom_core import features


@dataclass(frozen=True)
class Notice:
    watcher: str
    level: str          # "warning" | "resolved"
    message: str


Check = Callable[[], Optional[str]]


def _float_env(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except ValueError:
        return default


def disk_check(path: Optional[str] = None) -> Check:
    def check() -> Optional[str]:
        target = path or os.environ.get("SystemDrive", "C:") + os.sep
        limit = _float_env("TOM_WATCH_DISK_FREE_GB", 10.0)
        free = shutil.disk_usage(target).free / 2**30
        return f"Only {free:.1f} GB free on {target} (alert below {limit:g} GB)." if free < limit else None
    return check


def ram_check() -> Check:
    def check() -> Optional[str]:
        import psutil
        limit = _float_env("TOM_WATCH_RAM_PCT", 90.0)
        used = psutil.virtual_memory().percent
        return f"RAM is {used:.0f}% used (alert above {limit:g}%)." if used > limit else None
    return check


def blocked_tasks_check(store) -> Check:
    def check() -> Optional[str]:
        from tom_core.tasks.models import TaskState
        blocked = [t for t in store.list(limit=50) if t.state is TaskState.BLOCKED]
        if not blocked:
            return None
        return f"{len(blocked)} task(s) are blocked and need you: " + "; ".join(t.text[:60] for t in blocked[:3])
    return check


class WatcherSet:
    def __init__(self, checks: Dict[str, Check]) -> None:
        self.checks = checks
        self._last: Dict[str, Optional[str]] = {}

    def poll(self) -> List[Notice]:
        notices = []
        for name, check in self.checks.items():
            try:
                problem = check()
            except Exception:
                continue                               # a broken watcher stays silent, never noisy
            before = self._last.get(name)
            if problem and before is None:              # numbers drifting (9.8 → 9.7 GB) is not news
                notices.append(Notice(name, "warning", problem))
            elif not problem and before:
                notices.append(Notice(name, "resolved", f"Resolved: {before}"))
            self._last[name] = problem
        return notices


def default_watchers(store=None) -> WatcherSet:
    checks: Dict[str, Check] = {"disk": disk_check(), "ram": ram_check()}
    if store is not None:
        checks["blocked_tasks"] = blocked_tasks_check(store)
    return WatcherSet(checks)


def start(notify: Callable[[Notice], None], store=None, interval: float = 300.0) -> Optional[threading.Event]:
    """Run the watchers in a daemon thread when TOM_WATCHERS is on. Returns a stop Event, or None."""
    if not features.enabled("watchers"):
        return None
    stop = threading.Event()
    ws = default_watchers(store)

    def loop() -> None:
        while not stop.is_set():
            for n in ws.poll():
                try:
                    notify(n)
                except Exception:
                    pass
            stop.wait(interval)

    threading.Thread(target=loop, name="tom-watchers", daemon=True).start()
    return stop
