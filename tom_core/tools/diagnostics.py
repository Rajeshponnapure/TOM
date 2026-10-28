"""Read-only diagnostics and file-intelligence tools (PRD C09 system diagnostics, C04 duplicate detection).

All of them only observe. Commands run as argument lists (never shell=True) with timeouts.
"""
from __future__ import annotations

import hashlib
import os
import socket
import subprocess
from collections import defaultdict
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from tom_core.policy.engine import ActionClass
from tom_core.tools.registry import ToolRegistry, ToolSpec

_FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def _run(cmd: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, creationflags=_FLAGS,
                          encoding="utf-8", errors="replace")


# ── C04: duplicate files ────────────────────────────────────────────────────
class DupArgs(BaseModel):
    path: str
    min_size_kb: int = Field(16, ge=0, le=10_000_000)
    limit: int = Field(25, ge=1, le=200)


def _digest(path: str, block: int = 1 << 20) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(block), b""):
            h.update(chunk)
    return h.hexdigest()


def find_duplicates(path: str, min_size_kb: int = 16, limit: int = 25) -> Dict[str, Any]:
    root = os.path.abspath(os.path.expanduser(path))
    if not os.path.isdir(root):
        return {"status": "error", "error_class": "not_found", "message": f"No folder at {root}."}
    by_size: Dict[int, List[str]] = defaultdict(list)
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            full = os.path.join(dirpath, f)
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            if size >= min_size_kb * 1024:
                by_size[size].append(full)
    groups = []
    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        by_hash: Dict[str, List[str]] = defaultdict(list)
        for p in paths:
            try:
                by_hash[_digest(p)].append(p)
            except OSError:
                continue
        groups += [{"size_bytes": size, "files": ps} for ps in by_hash.values() if len(ps) > 1]
    groups.sort(key=lambda g: g["size_bytes"] * (len(g["files"]) - 1), reverse=True)
    wasted = sum(g["size_bytes"] * (len(g["files"]) - 1) for g in groups)
    lines = [f"{len(g['files'])} copies, {g['size_bytes'] / 2**20:.1f} MB each: " + " | ".join(g["files"][:4])
             for g in groups[:limit]]
    return {"status": "success", "output": groups[:limit],
            "evidence": f"compared file contents (SHA-1) under {root}",
            "message": (f"{len(groups)} group(s) of identical files; {wasted / 2**20:.1f} MB could be freed.\n"
                        + "\n".join(lines)) if groups else f"No duplicate files found under {root}."}


# ── C09: services, event log, DNS, runtimes ─────────────────────────────────
class ServiceArgs(BaseModel):
    name_filter: str = ""
    only_running: bool = False
    limit: int = Field(40, ge=1, le=300)


def services(name_filter: str = "", only_running: bool = False, limit: int = 40) -> Dict[str, Any]:
    if os.name != "nt":
        return {"status": "error", "error_class": "unsupported", "message": "Windows services are only on Windows."}
    proc = _run(["sc", "query", "type=", "service", "state=", "all"], timeout=30)
    items, cur = [], {}
    for line in proc.stdout.splitlines():
        s = line.strip()
        if s.startswith("SERVICE_NAME:"):
            cur = {"name": s.split(":", 1)[1].strip()}
            items.append(cur)
        elif s.startswith("DISPLAY_NAME:") and cur:
            cur["display"] = s.split(":", 1)[1].strip()
        elif s.startswith("STATE") and cur:
            cur["state"] = s.split()[-1]
    f = name_filter.lower()
    items = [i for i in items if (not f or f in i["name"].lower() or f in i.get("display", "").lower())
             and (not only_running or i.get("state") == "RUNNING")]
    lines = [f"{i.get('state', '?'):<8} {i['name']} — {i.get('display', '')}" for i in items[:limit]]
    return {"status": "success", "output": items[:limit], "evidence": "sc query",
            "message": f"{len(items)} service(s)" + (f" matching '{name_filter}'" if f else "") + ":\n" + "\n".join(lines)}


class EventArgs(BaseModel):
    log: str = Field("System", pattern=r"^(System|Application|Setup)$")
    count: int = Field(15, ge=1, le=100)
    errors_only: bool = True


def windows_events(log: str = "System", count: int = 15, errors_only: bool = True) -> Dict[str, Any]:
    if os.name != "nt":
        return {"status": "error", "error_class": "unsupported", "message": "The Windows event log is only on Windows."}
    cmd = ["wevtutil", "qe", log, f"/c:{count}", "/rd:true", "/f:text"]
    if errors_only:
        cmd.append("/q:*[System[(Level=1 or Level=2)]]")
    proc = _run(cmd, timeout=40)
    events, cur = [], {}
    for line in proc.stdout.splitlines():
        s = line.strip()
        if s.startswith("Event["):
            cur = {}
            events.append(cur)
        elif ":" in s and cur is not None:
            k, v = s.split(":", 1)
            if k in ("Date", "Source", "Event ID", "Level", "Description"):
                cur[k.lower().replace(" ", "_")] = v.strip()
    lines = [f"{e.get('date', '')[:19]}  {e.get('level', '')}  {e.get('source', '')} (ID {e.get('event_id', '')})"
             for e in events]
    kind = "error/critical " if errors_only else ""
    return {"status": "success", "output": events, "evidence": f"wevtutil qe {log}",
            "message": (f"Latest {len(events)} {kind}events in the {log} log:\n" + "\n".join(lines))
            if events else f"No {kind}events in the {log} log."}


class DnsArgs(BaseModel):
    host: str = Field(..., min_length=1, max_length=253, pattern=r"^[A-Za-z0-9.-]+$")


def dns_lookup(host: str) -> Dict[str, Any]:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        return {"status": "error", "error_class": "dns", "message": f"{host} does not resolve: {exc}"}
    addrs = sorted({i[4][0] for i in infos})
    return {"status": "success", "output": addrs, "evidence": "socket.getaddrinfo",
            "message": f"{host} resolves to: " + ", ".join(addrs)}


class NoArgs(BaseModel):
    pass


_RUNTIMES = [("Python", ["python", "--version"]), ("Node.js", ["node", "--version"]), ("Git", ["git", "--version"]),
             ("Docker", ["docker", "--version"]), ("WSL", ["wsl", "--status"]), ("Java", ["java", "-version"]),
             ("Ollama", ["ollama", "--version"]), (".NET", ["dotnet", "--version"])]


def dev_runtimes() -> Dict[str, Any]:
    found = {}
    for name, cmd in _RUNTIMES:
        try:
            p = _run(cmd, timeout=15)
            text = (p.stdout or p.stderr).replace("\x00", "").strip().splitlines()   # wsl prints UTF-16
            found[name] = text[0][:80] if p.returncode == 0 and text else "not installed"
        except (OSError, subprocess.SubprocessError):
            found[name] = "not installed"
    return {"status": "success", "output": found, "evidence": "ran each tool's --version",
            "message": "\n".join(f"{k}: {v}" for k, v in found.items())}


def register(registry: ToolRegistry) -> None:
    A = ActionClass
    reg = registry.register
    reg(ToolSpec("fs.find_duplicates", "Find identical files (by content) under a folder", DupArgs, find_duplicates,
                 A.OBSERVE, timeout=300, paths=lambda a: [a.path]))
    reg(ToolSpec("system.services", "List Windows services and their state", ServiceArgs, services, A.OBSERVE))
    reg(ToolSpec("system.events", "Recent errors in the Windows event log", EventArgs, windows_events, A.OBSERVE,
                 timeout=60))
    reg(ToolSpec("net.dns", "Resolve a host name", DnsArgs, dns_lookup, A.OBSERVE, timeout=15))
    reg(ToolSpec("dev.runtimes", "Installed developer runtimes (Python, Node, Git, Docker, WSL...)", NoArgs,
                 dev_runtimes, A.OBSERVE, timeout=120))
