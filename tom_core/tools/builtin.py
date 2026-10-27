"""TOM's built-in typed tools (PRD §8, §12.1; R7 filesystem/shell/git/diagnostics/browser adapters).

Every tool declares its action class; writes are verified on disk afterwards (FR-008: evidence, not
claims). Text read from files or web pages is returned with "untrusted": True — it is data for the
model, never instructions (FR-017, AT-011).
"""
from __future__ import annotations

import contextvars
import fnmatch
import os
import re
import shlex
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from tom_core.policy.engine import ActionClass
from tom_core.tools.registry import ToolRegistry, ToolSpec
from tools.project_paths import project_path

_agent = None
_depth: contextvars.ContextVar[int] = contextvars.ContextVar("tom_tool_request_depth", default=0)
MAX_REQUEST_DEPTH = 2          # tom.request from inside tom.request from inside a plan — no deeper


def set_agent(agent) -> None:
    """TomAgent registers itself so `tom.request` can hand sub-requests to the full pipeline."""
    global _agent
    _agent = agent


def _abs(path: str) -> str:
    return os.path.abspath(os.path.expanduser(os.path.expandvars(str(path).strip().strip('"'))))


def _entry(path: str) -> Dict[str, Any]:
    st = os.stat(path)
    return {"path": path, "name": os.path.basename(path), "type": "folder" if os.path.isdir(path) else "file",
            "size_bytes": st.st_size, "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))}


def _human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# ── filesystem: observe ──────────────────────────────────────────────────
class ListDirArgs(BaseModel):
    path: str
    pattern: str = "*"
    limit: int = Field(200, ge=1, le=2000)


def list_dir(path: str, pattern: str = "*", limit: int = 200) -> Dict[str, Any]:
    root = _abs(path)
    if not os.path.isdir(root):
        return {"status": "error", "error_class": "not_found", "message": f"No folder at {root}."}
    items = []
    for name in sorted(os.listdir(root)):
        if fnmatch.fnmatch(name.lower(), pattern.lower()):
            try:
                items.append(_entry(os.path.join(root, name)))
            except OSError:
                continue
        if len(items) >= limit:
            break
    return {"status": "success", "output": items, "evidence": f"listed {len(items)} entries of {root}",
            "message": f"{len(items)} item(s) in {root}"}


class LargestArgs(BaseModel):
    path: str
    count: int = Field(10, ge=1, le=200)
    recursive: bool = True


def largest_files(path: str, count: int = 10, recursive: bool = True) -> Dict[str, Any]:
    root = _abs(path)
    if not os.path.isdir(root):
        return {"status": "error", "error_class": "not_found", "message": f"No folder at {root}."}
    found, scanned = [], 0
    walker = os.walk(root) if recursive else [(root, [], os.listdir(root))]
    for dirpath, dirnames, files in walker:
        dirnames[:] = [d for d in dirnames if not d.startswith((".", "$")) and d not in ("node_modules", "__pycache__")]
        for f in files:
            p = os.path.join(dirpath, f)
            try:
                if os.path.isfile(p):
                    found.append((os.path.getsize(p), p))
                    scanned += 1
            except OSError:
                continue
        if scanned > 50000:
            break
    found.sort(reverse=True)
    top = [{"path": p, "size": _human(s), "size_bytes": s} for s, p in found[:count]]
    return {"status": "success", "output": top, "evidence": f"measured {scanned} files under {root}",
            "message": "\n".join(f"{i}. {t['path']} — {t['size']}" for i, t in enumerate(top, 1))
            or f"No files under {root}."}


class FindArgs(BaseModel):
    path: str
    pattern: str
    limit: int = Field(100, ge=1, le=2000)


def find_files(path: str, pattern: str, limit: int = 100) -> Dict[str, Any]:
    root = _abs(path)
    if not os.path.isdir(root):
        return {"status": "error", "error_class": "not_found", "message": f"No folder at {root}."}
    hits: List[str] = []
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith((".", "$"))]
        hits += [os.path.join(dirpath, f) for f in files if fnmatch.fnmatch(f.lower(), pattern.lower())]
        if len(hits) >= limit:
            break
    hits = hits[:limit]
    return {"status": "success", "output": hits, "evidence": f"searched {root} for {pattern}",
            "message": f"{len(hits)} match(es) for {pattern} in {root}"}


class PathArgs(BaseModel):
    path: str


def file_info(path: str) -> Dict[str, Any]:
    p = _abs(path)
    if not os.path.exists(p):
        return {"status": "error", "error_class": "not_found", "message": f"Nothing at {p}."}
    return {"status": "success", "output": _entry(p), "evidence": f"stat {p}", "message": str(_entry(p))}


class ReadArgs(BaseModel):
    path: str
    max_chars: int = Field(20000, ge=1, le=200000)


def read_text(path: str, max_chars: int = 20000) -> Dict[str, Any]:
    p = _abs(path)
    if not os.path.isfile(p):
        return {"status": "error", "error_class": "not_found", "message": f"No file at {p}."}
    with open(p, "rb") as fh:
        raw = fh.read(max_chars * 4)
    if b"\x00" in raw[:4096]:
        return {"status": "error", "error_class": "binary", "message": f"{p} is not a text file."}
    text = raw.decode("utf-8", errors="replace")[:max_chars]
    return {"status": "success", "output": {"text": text, "untrusted": True}, "evidence": f"read {len(text)} chars",
            "message": f"Read {len(text)} characters from {p}"}


# ── filesystem: write (workspace; outside needs approval) ────────────────
class WriteArgs(BaseModel):
    path: str
    content: str
    overwrite: bool = False


def _backup(path: str) -> str:
    """Copy a file about to be overwritten into <state>/tom_brain/backups (FR-012 recovery point)."""
    dest_dir = project_path("tom_brain", "backups", "files", time.strftime("%Y%m%d"))
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{time.strftime('%H%M%S')}_{os.path.basename(path)}"
    shutil.copy2(path, dest)
    return str(dest)


def write_text(path: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
    p = _abs(path)
    backup = ""
    if os.path.exists(p):
        if not overwrite:
            return {"status": "error", "error_class": "exists", "message": f"{p} already exists (overwrite=false)."}
        backup = _backup(p)
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(content)
    with open(p, encoding="utf-8", newline="") as fh:
        ok = fh.read() == content                 # verified by reading it back, not assumed
    if ok:
        from tom_core import recovery
        recovery.record("write", path=p, backup=backup or None)
    return {"status": "success" if ok else "error", "verified": ok, "path": p, "backup": backup,
            "evidence": f"{p} holds {len(content)} chars" + (f"; previous version saved to {backup}" if backup else ""),
            "message": f"Wrote {p}" if ok else f"Writing {p} could not be verified."}


def make_dir(path: str) -> Dict[str, Any]:
    p = _abs(path)
    existed = os.path.isdir(p)
    os.makedirs(p, exist_ok=True)
    ok = os.path.isdir(p)
    if ok and not existed:
        from tom_core import recovery
        recovery.record("mkdir", path=p)
    return {"status": "success" if ok else "error", "verified": ok, "path": p,
            "evidence": f"{p} exists" if ok else "", "message": f"Folder ready: {p}"}


class CopyArgs(BaseModel):
    src: str
    dst: str


def copy_path(src: str, dst: str) -> Dict[str, Any]:
    s, d = _abs(src), _abs(dst)
    if not os.path.exists(s):
        return {"status": "error", "error_class": "not_found", "message": f"Nothing at {s}."}
    if os.path.exists(d):
        return {"status": "error", "error_class": "exists", "message": f"{d} already exists."}
    os.makedirs(os.path.dirname(d) or ".", exist_ok=True)
    (shutil.copytree if os.path.isdir(s) else shutil.copy2)(s, d)
    ok = os.path.exists(d)
    if ok:
        from tom_core import recovery
        recovery.record("copy", src=s, dst=d)
    return {"status": "success" if ok else "error", "verified": ok, "path": d,
            "evidence": f"{d} exists", "message": f"Copied to {d}"}


def move_path(src: str, dst: str) -> Dict[str, Any]:
    s, d = _abs(src), _abs(dst)
    if not os.path.exists(s):
        return {"status": "error", "error_class": "not_found", "message": f"Nothing at {s}."}
    if os.path.exists(d):
        return {"status": "error", "error_class": "exists", "message": f"{d} already exists."}
    os.makedirs(os.path.dirname(d) or ".", exist_ok=True)
    shutil.move(s, d)
    ok = os.path.exists(d) and not os.path.exists(s)
    if ok:
        from tom_core import recovery
        recovery.record("move", src=s, dst=d)
    return {"status": "success" if ok else "error", "verified": ok, "path": d,
            "evidence": f"{d} exists and {s} is gone" if ok else "", "message": f"Moved to {d}"}


def _recycle(path: str) -> bool:
    """Send to the Windows Recycle Bin (recoverable) via SHFileOperationW."""
    if os.name != "nt":
        return False
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_uint16), ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]
    FO_DELETE, FOF_SILENT, FOF_NOCONFIRMATION, FOF_ALLOWUNDO, FOF_NOERRORUI = 3, 0x4, 0x10, 0x40, 0x400
    op = SHFILEOPSTRUCTW(None, FO_DELETE, path + "\0", None,
                         FOF_SILENT | FOF_NOCONFIRMATION | FOF_ALLOWUNDO | FOF_NOERRORUI, False, None, None)
    return ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op)) == 0 and not op.fAnyOperationsAborted


def delete_path(path: str) -> Dict[str, Any]:
    p = _abs(path)
    if not os.path.exists(p):
        return {"status": "error", "error_class": "not_found", "message": f"Nothing at {p}."}
    from tom_core import recovery
    kept = recovery.backup(p)                     # FR-012: a copy first, so "undo" can restore it
    if not _recycle(p):
        return {"status": "error", "error_class": "unsupported",
                "message": "Could not move it to the Recycle Bin, so nothing was deleted."}
    ok = not os.path.exists(p)
    if ok:
        recovery.record("delete", path=p, backup=kept or None)
    return {"status": "success" if ok else "error", "verified": ok,
            "evidence": f"{p} is in the Recycle Bin" if ok else "", "message": f"Moved {p} to the Recycle Bin."}


# ── web ──────────────────────────────────────────────────────────────────
class SearchArgs(BaseModel):
    query: str = Field(min_length=2)
    limit: int = Field(8, ge=1, le=20)


def web_search(query: str, limit: int = 8) -> Dict[str, Any]:
    from tools import web_search as ws
    hits = ws.search(query, limit)
    if not hits:
        return {"status": "error", "error_class": "no_results", "message": f"No search results for '{query}'."}
    return {"status": "success", "output": [h.__dict__ for h in hits], "evidence": f"{len(hits)} results",
            "message": ws.sources_text(hits)}


class FetchArgs(BaseModel):
    url: str = Field(pattern=r"^https?://")
    max_chars: int = Field(8000, ge=200, le=60000)


def web_fetch(url: str, max_chars: int = 8000) -> Dict[str, Any]:
    import requests
    from bs4 import BeautifulSoup
    r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = re.sub(r"\n\s*\n+", "\n\n", soup.get_text("\n", strip=True))[:max_chars]
    return {"status": "success", "output": {"title": soup.title.get_text(strip=True) if soup.title else "",
                                            "text": text, "untrusted": True},
            "evidence": f"HTTP {r.status_code}, {len(text)} chars", "message": f"Fetched {url}"}


# ── system / network diagnostics (PRD C09, read-only) ─────────────────────
class NoArgs(BaseModel):
    pass


def system_info() -> Dict[str, Any]:
    import platform

    import psutil
    vm = psutil.virtual_memory()
    du = psutil.disk_usage(os.path.abspath(os.sep))
    info = {"os": f"{platform.system()} {platform.release()}", "cpu_percent": psutil.cpu_percent(interval=0.5),
            "cpu_cores": psutil.cpu_count(), "ram_used": _human(vm.used), "ram_total": _human(vm.total),
            "ram_available": _human(vm.available), "ram_percent": vm.percent,
            "disk_free": _human(du.free), "disk_total": _human(du.total)}
    try:
        from tom_core.resources.gpu import query_gpu_memory
        gpu = query_gpu_memory()
        if gpu:
            info.update({"vram_used_mb": gpu.used_mb, "vram_total_mb": gpu.total_mb, "vram_free_mb": gpu.free_mb})
    except Exception:
        pass
    return {"status": "success", "output": info, "evidence": "measured with psutil/nvidia-smi just now",
            "message": ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in info.items())}


class TopArgs(BaseModel):
    count: int = Field(10, ge=1, le=50)
    sort_by: str = Field("memory", pattern="^(memory|cpu)$")


def top_processes(count: int = 10, sort_by: str = "memory") -> Dict[str, Any]:
    import psutil
    procs = []
    for p in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            procs.append({"pid": p.info["pid"], "name": p.info["name"],
                          "memory_mb": round((p.info["memory_info"].rss if p.info["memory_info"] else 0) / 2**20, 1),
                          "cpu_percent": p.cpu_percent(interval=None)})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if sort_by == "cpu":
        time.sleep(0.5)
        for entry in procs:
            try:
                entry["cpu_percent"] = psutil.Process(entry["pid"]).cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                entry["cpu_percent"] = 0.0
    key = "memory_mb" if sort_by == "memory" else "cpu_percent"
    top = sorted(procs, key=lambda e: e[key], reverse=True)[:count]
    return {"status": "success", "output": top, "evidence": f"sampled {len(procs)} processes",
            "message": "\n".join(f"{e['name']} (pid {e['pid']}): {e['memory_mb']} MB, CPU {e['cpu_percent']}%"
                                 for e in top)}


class PortsArgs(BaseModel):
    host: str = Field("127.0.0.1", pattern=r"^(127\.0\.0\.1|localhost|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+"
                                          r"|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)$")


def open_ports(host: str = "127.0.0.1") -> Dict[str, Any]:
    from tools.network_tools import NetworkTools
    return NetworkTools().scan_ports("127.0.0.1" if host == "localhost" else host)


# ── apps ─────────────────────────────────────────────────────────────────
class AppArgs(BaseModel):
    name: str = Field(min_length=1, max_length=80)


async def open_app(name: str) -> Dict[str, Any]:
    from tools.os_tools import OSTools
    return await OSTools().open_application(name)


# ── shell (allowlisted read-only commands run directly; anything else needs approval) ──
READ_ONLY_COMMANDS = {
    ("git", "status"), ("git", "log"), ("git", "diff"), ("git", "branch"), ("git", "show"),
    ("python", "--version"), ("python", "-V"), ("pip", "list"), ("pip", "show"), ("pip", "freeze"),
    ("ipconfig",), ("hostname",), ("whoami",), ("systeminfo",), ("tasklist",), ("where",), ("ver",),
    ("node", "--version"), ("npm", "--version"), ("ollama", "list"), ("ollama", "ps"), ("nvidia-smi",),
}
_CMD_BUILTINS = {"dir", "ver", "echo", "type", "where"}


class ShellArgs(BaseModel):
    command: str = Field(min_length=1, max_length=500)
    cwd: Optional[str] = None
    timeout: int = Field(60, ge=1, le=600)


def _argv(command: str) -> List[str]:
    return shlex.split(command, posix=(os.name != "nt"))


def shell_class(args: ShellArgs) -> ActionClass:
    try:
        argv = [a.lower() for a in _argv(args.command)]
    except ValueError:
        return ActionClass.MATERIAL_CHANGE
    if any(ch in args.command for ch in "|&;<>`$"):
        return ActionClass.MATERIAL_CHANGE         # pipes/redirects/chaining are never "read-only"
    if any(tuple(argv[:len(ok)]) == ok for ok in READ_ONLY_COMMANDS):
        return ActionClass.OBSERVE
    return ActionClass.MATERIAL_CHANGE


def run_shell(command: str, cwd: Optional[str] = None, timeout: int = 60) -> Dict[str, Any]:
    argv = _argv(command)
    if os.name == "nt" and argv and argv[0].lower() in _CMD_BUILTINS:
        argv = ["cmd", "/c", *argv]
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    proc = subprocess.run(argv, cwd=_abs(cwd) if cwd else None, capture_output=True, text=True,
                          timeout=timeout, creationflags=flags, errors="replace")
    out = (proc.stdout or "")[-6000:]
    err = (proc.stderr or "")[-2000:]
    return {"status": "success" if proc.returncode == 0 else "error", "exit_code": proc.returncode,
            "output": out, "error_class": "" if proc.returncode == 0 else "nonzero_exit",
            "evidence": f"exit code {proc.returncode}", "message": (out or err).strip()[:3000]}


# ── git ──────────────────────────────────────────────────────────────────
class RepoArgs(BaseModel):
    repo: str


class GitLogArgs(BaseModel):
    repo: str
    count: int = Field(10, ge=1, le=100)


class CheckpointArgs(BaseModel):
    repo: str
    label: str = Field("tom-checkpoint", max_length=60, pattern=r"^[\w.\- ]+$")


def _git(repo: str, *args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    return subprocess.run(["git", "-C", _abs(repo), *args], capture_output=True, text=True, timeout=timeout,
                          creationflags=flags, errors="replace")


def git_status(repo: str) -> Dict[str, Any]:
    p = _git(repo, "status", "--short", "--branch")
    return {"status": "success" if p.returncode == 0 else "error", "output": p.stdout,
            "evidence": f"git status exit {p.returncode}", "message": (p.stdout or p.stderr).strip()[:3000]}


def git_diff(repo: str) -> Dict[str, Any]:
    p = _git(repo, "diff", "--stat")
    return {"status": "success" if p.returncode == 0 else "error", "output": p.stdout,
            "evidence": f"git diff exit {p.returncode}", "message": (p.stdout or p.stderr or "No changes.").strip()[:3000]}


def git_log(repo: str, count: int = 10) -> Dict[str, Any]:
    p = _git(repo, "log", f"-{count}", "--oneline")
    return {"status": "success" if p.returncode == 0 else "error", "output": p.stdout,
            "evidence": f"git log exit {p.returncode}", "message": (p.stdout or p.stderr).strip()[:3000]}


def git_checkpoint(repo: str, label: str = "tom-checkpoint") -> Dict[str, Any]:
    """Snapshot the working tree without touching it or the branch (FR-012): `git stash create` makes a
    commit object of the current changes; a ref under refs/tom/checkpoints keeps it. Restore with
    `git stash apply <ref>`."""
    created = _git(repo, "stash", "create", label)
    sha = (created.stdout or "").strip()
    if created.returncode != 0:
        return {"status": "error", "message": (created.stderr or "git stash create failed").strip()}
    if not sha:
        head = _git(repo, "rev-parse", "HEAD")
        return {"status": "success", "verified": True, "output": {"ref": "", "commit": head.stdout.strip()},
                "evidence": "working tree clean — HEAD is the checkpoint", "message": "Nothing to save: no changes."}
    safe_label = re.sub(r"[^\w.-]+", "-", label)
    ref = f"refs/tom/checkpoints/{time.strftime('%Y%m%d-%H%M%S')}-{safe_label}"
    upd = _git(repo, "update-ref", ref, sha)
    ok = upd.returncode == 0 and _git(repo, "rev-parse", ref).stdout.strip() == sha
    return {"status": "success" if ok else "error", "verified": ok, "output": {"ref": ref, "commit": sha},
            "evidence": f"{ref} -> {sha[:10]}", "message": f"Checkpoint {ref} (restore: git stash apply {sha[:10]})"}


# ── hand a sub-request to TOM's full pipeline (child task, own policy checks) ──
class RequestArgs(BaseModel):
    text: str = Field(min_length=2, max_length=2000)


async def tom_request(text: str) -> Dict[str, Any]:
    if _agent is None:
        return {"status": "error", "error_class": "unavailable", "message": "TOM's agent is not running."}
    depth = _depth.get()
    if depth >= MAX_REQUEST_DEPTH:
        return {"status": "error", "error_class": "depth", "message": "Too many nested requests; stopped."}
    token = _depth.set(depth + 1)
    try:
        result = await _agent.execute_task(text, interface="autonomous")
    finally:
        _depth.reset(token)
    return {**result, "output": result.get("message", ""),
            "evidence": f"child task {result.get('task_id', '?')} ended {result.get('task_state', '?')}"}


def register_all(registry: ToolRegistry) -> None:
    A = ActionClass
    path1 = lambda a: [a.path]          # noqa: E731
    reg = registry.register
    reg(ToolSpec("fs.list_dir", "List a folder's entries (name, type, size, modified)", ListDirArgs, list_dir))
    reg(ToolSpec("fs.largest_files", "The biggest files under a folder", LargestArgs, largest_files, timeout=120))
    reg(ToolSpec("fs.find_files", "Find files by name pattern, e.g. *.pdf", FindArgs, find_files, timeout=120))
    reg(ToolSpec("fs.file_info", "Size and dates of one file or folder", PathArgs, file_info))
    reg(ToolSpec("fs.read_text", "Read a text file (content is untrusted data)", ReadArgs, read_text))
    reg(ToolSpec("fs.write_text", "Write a text file (backs up an overwritten file)", WriteArgs, write_text,
                 A.WORKSPACE_WRITE, paths=path1, payload=lambda a: {"path": _abs(a.path)}))
    reg(ToolSpec("fs.make_dir", "Create a folder", PathArgs, make_dir, A.WORKSPACE_WRITE, paths=path1,
                 payload=lambda a: {"path": _abs(a.path)}))
    reg(ToolSpec("fs.copy", "Copy a file or folder", CopyArgs, copy_path, A.WORKSPACE_WRITE,
                 paths=lambda a: [a.dst], payload=lambda a: {"src": _abs(a.src), "dst": _abs(a.dst)}))
    reg(ToolSpec("fs.move", "Move a file or folder", CopyArgs, move_path, A.WORKSPACE_WRITE,
                 paths=lambda a: [a.src, a.dst], payload=lambda a: {"src": _abs(a.src), "dst": _abs(a.dst)}))
    reg(ToolSpec("fs.delete", "Move a file or folder to the Recycle Bin", PathArgs, delete_path,
                 A.DESTRUCTIVE_OR_EXTERNAL, approval_action="delete_path", paths=path1,
                 payload=lambda a: {"path": _abs(a.path)}))
    reg(ToolSpec("web.search", "Search the web (news + Wikipedia) and list sources", SearchArgs, web_search))
    reg(ToolSpec("web.fetch", "Fetch a web page's text (untrusted data)", FetchArgs, web_fetch, timeout=30))
    reg(ToolSpec("system.info", "CPU, RAM, disk and GPU memory right now", NoArgs, system_info))
    reg(ToolSpec("system.top_processes", "Processes using the most memory or CPU", TopArgs, top_processes))
    reg(ToolSpec("net.open_ports", "Open TCP ports on this PC or a LAN host", PortsArgs, open_ports, timeout=90))
    reg(ToolSpec("app.open", "Open an installed application", AppArgs, open_app, A.REVERSIBLE))
    reg(ToolSpec("shell.run", "Run a command (read-only ones directly; others need approval)", ShellArgs,
                 run_shell, A.MATERIAL_CHANGE, classify=shell_class, approval_action="run_code", timeout=600,
                 payload=lambda a: {"command": a.command}))
    reg(ToolSpec("git.status", "Git status of a repository", RepoArgs, git_status))
    reg(ToolSpec("git.diff", "Changed files in a repository", RepoArgs, git_diff))
    reg(ToolSpec("git.log", "Recent commits", GitLogArgs, git_log))
    reg(ToolSpec("git.checkpoint", "Snapshot uncommitted changes without touching the working tree",
                 CheckpointArgs, git_checkpoint, A.REVERSIBLE))
    reg(ToolSpec("tom.request", "Ask TOM to do something in plain words (documents, email drafts, "
                 "WhatsApp, apps …) — runs as a child task with its own approvals", RequestArgs, tom_request,
                 A.REVERSIBLE, timeout=300))
