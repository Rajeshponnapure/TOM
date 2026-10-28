"""Recovery points for every file change TOM makes (PRD FR-012, C17 rollback).

Before a change, the tool records how to reverse it; "undo last change" reverses the newest one.

    write  — an overwritten file's previous version is backed up; a new file is removed on undo
    move   — moved back
    copy / mkdir — the created copy/folder is removed on undo (to the Recycle Bin when possible)
    delete — a copy is kept here first (files/folders up to MAX_BACKUP_MB), so undo restores it even
             though the original went to the Recycle Bin

Journal: tom_brain/recovery/journal.jsonl; backups beside it. Nothing here deletes user data outright:
undo of a created item moves it to the Recycle Bin.
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from tools.project_paths import project_path

MAX_BACKUP_MB = 300
_LOCK = threading.Lock()


def _dir() -> str:
    d = str(project_path("tom_brain", "recovery"))
    os.makedirs(d, exist_ok=True)
    return d


def _journal() -> str:
    return os.path.join(_dir(), "journal.jsonl")


def _size_mb(path: str) -> float:
    if os.path.isfile(path):
        return os.path.getsize(path) / 2**20
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total / 2**20


def backup(path: str) -> str:
    """Copy `path` into the recovery store; "" when it is too large or missing."""
    if not os.path.exists(path) or _size_mb(path) > MAX_BACKUP_MB:
        return ""
    dest = os.path.join(_dir(), "backups", uuid.uuid4().hex[:12], os.path.basename(path.rstrip("\\/")) or "item")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    (shutil.copytree if os.path.isdir(path) else shutil.copy2)(path, dest)
    return dest


def record(kind: str, **data: Any) -> str:
    entry = {"id": uuid.uuid4().hex[:12], "at": time.strftime("%Y-%m-%d %H:%M:%S"), "kind": kind,
             "undone": False, **{k: str(v) for k, v in data.items() if v is not None}}
    try:
        from tom_core.tasks.service import current_task_id
        if current_task_id():
            entry["task_id"] = current_task_id()
    except Exception:
        pass
    with _LOCK, open(_journal(), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry["id"]


def entries(limit: int = 50, include_undone: bool = False) -> List[Dict[str, Any]]:
    try:
        with open(_journal(), encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
    except OSError:
        return []
    latest: Dict[str, Dict[str, Any]] = {}
    for r in rows:                                   # later lines (undo markers) override earlier state
        latest[r["id"]] = {**latest.get(r["id"], {}), **r}
    out = [r for r in latest.values() if include_undone or not r.get("undone")]
    return list(reversed(out))[:limit]


def _mark_undone(entry_id: str) -> None:
    with _LOCK, open(_journal(), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"id": entry_id, "undone": True, "undone_at": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")


def _remove(path: str) -> None:
    """Remove a TOM-created item — to the Recycle Bin when possible."""
    if not os.path.exists(path):
        return
    try:
        from tom_core.tools.builtin import _recycle
        if _recycle(path):
            return
    except Exception:
        pass
    (shutil.rmtree if os.path.isdir(path) else os.remove)(path)


def describe(e: Dict[str, Any]) -> str:
    k = e["kind"]
    if k == "write":
        return f"wrote {e.get('path')}" + (" (replacing an earlier version)" if e.get("backup") else "")
    if k == "move":
        return f"moved {e.get('src')} → {e.get('dst')}"
    if k == "copy":
        return f"copied to {e.get('dst')}"
    if k == "mkdir":
        return f"created folder {e.get('path')}"
    if k == "delete":
        return f"deleted {e.get('path')}" + ("" if e.get("backup") else " (too large to keep a copy)")
    if k == "create":
        return f"created {e.get('path')}"
    if k == "organize":
        return f"organized {e.get('folder')} ({e.get('count', '?')} files moved)"
    return k


def changed_since(e: Dict[str, Any]) -> bool:
    """True when the item was modified after TOM's change (an undo would overwrite the owner's edits)."""
    path = e.get("path") or e.get("dst")
    if not path or not os.path.exists(path) or e["kind"] not in ("write", "create"):
        return False
    try:
        at = time.mktime(time.strptime(e["at"], "%Y-%m-%d %H:%M:%S"))
    except (KeyError, ValueError):
        return False
    return os.path.getmtime(path) > at + 5


def undo(entry_id: Optional[str] = None) -> Dict[str, Any]:
    """Reverse one recorded change (the newest when no id is given)."""
    todo = entries(200)
    e = next((x for x in todo if x["id"] == entry_id), None) if entry_id else (todo[0] if todo else None)
    if e is None:
        return {"status": "error", "message": "There is no change of mine to undo."}
    k = e["kind"]
    try:
        if k == "write":
            if e.get("backup") and os.path.exists(e["backup"]):
                shutil.copy2(e["backup"], e["path"])
            else:
                _remove(e["path"])
        elif k == "move":
            if os.path.exists(e["src"]):
                return {"status": "error", "message": f"Cannot move back: something is already at {e['src']}."}
            shutil.move(e["dst"], e["src"])
        elif k == "organize":
            from tools.file_ops import FileOps
            ops = FileOps()
            plan = ops.plan_undo_last_organization(e.get("folder") or None)
            if plan.get("status") != "plan":                # already undone through "undo the organization of …"
                _mark_undone(e["id"])
                return {"status": "error", "message": f"That organization of {e.get('folder')} was already undone. "
                                                      "Say \"undo\" again for the change before it."}
            done = ops.execute_undo_plan(plan)
            if not done.get("moved"):
                return {"status": "error", "message": done.get("message", "Undo failed: nothing could be moved back.")}
        elif k in ("copy", "mkdir", "create"):
            target = e.get("dst") or e.get("path")
            if not isinstance(target, str):
                return {"status": "error", "message": "Cannot undo this change because its target path is missing."}
            if k == "mkdir" and os.path.isdir(target) and os.listdir(target):
                return {"status": "error", "message": f"{target} is no longer empty, so I left it in place."}
            _remove(target)
        elif k == "delete":
            if not e.get("backup") or not os.path.exists(e["backup"]):
                return {"status": "error", "message": f"No copy was kept of {e['path']} — restore it from the Recycle Bin."}
            if os.path.exists(e["path"]):
                return {"status": "error", "message": f"Something is already at {e['path']}; not overwriting it."}
            os.makedirs(os.path.dirname(e["path"]) or ".", exist_ok=True)
            (shutil.copytree if os.path.isdir(e["backup"]) else shutil.copy2)(e["backup"], e["path"])
        else:
            return {"status": "error", "message": f"I don't know how to undo '{k}'."}
    except OSError as exc:
        return {"status": "error", "message": f"Undo failed: {exc}"}
    _mark_undone(e["id"])
    return {"status": "success", "verified": True, "message": f"Undone: {describe(e)}.", "entry": e}
