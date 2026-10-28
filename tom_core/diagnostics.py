"""Why is RAM / CPU / VRAM / disk high? Measured answers with the processes behind them (PRD C09).

Live check 2026-10-27: "why is my RAM usage high?" was answered by chat with "I don't have any information
about your current RAM usage" although TOM measures it. This module measures, groups processes by app
(Chrome runs dozens of processes), names what holds GPU memory, and suggests — it never closes anything
by itself (PRD RRM-008).
"""
from __future__ import annotations

import re
import subprocess
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

ASK = re.compile(
    r"\b(?:why|what(?:'s| is)?|which|who)\b.{0,40}\b(ram|memory|cpu|processor|vram|gpu|graphics|disk|storage|"
    r"space|drive)\b.{0,40}\b(high|full|slow|using|usage|used|eating|hogging|maxed|100|so much|low|busy)\b"
    r"|\b(?:what(?:'s| is)|which (?:app|program|process)(?:es)?(?: is| are)?)\s+(?:using|eating|hogging|taking)\s+"
    r"(?:up\s+)?(?:my|the|all)?\s*(ram|memory|cpu|vram|gpu|disk|space)\b"
    r"|\b(?:pc|computer|laptop|system)\s+(?:is\s+)?(?:so\s+|very\s+|really\s+)?(?:slow|laggy|lagging|hanging)\b",
    re.IGNORECASE)


def wants(text: str) -> Optional[str]:
    """The resource asked about ("ram", "cpu", "vram", "disk", or "all" for "my PC is slow"), else None."""
    m = ASK.search(text or "")
    if not m:
        return None
    word = (m.group(1) or m.group(3) or "").lower()
    if word in ("ram", "memory"):
        return "ram"
    if word in ("cpu", "processor"):
        return "cpu"
    if word in ("vram", "gpu", "graphics"):
        return "vram"
    if word in ("disk", "storage", "space", "drive"):
        return "disk"
    return "all"


def _human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def processes_by_app(sort: str = "memory") -> List[Dict[str, Any]]:
    """Processes summed per executable name: [{"name", "count", "memory_mb", "cpu_percent"}]."""
    import psutil
    procs = list(psutil.process_iter(["name", "memory_info"]))
    for p in procs:
        try:
            p.cpu_percent(None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    if sort == "cpu":
        time.sleep(1.0)
    apps: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "memory_mb": 0.0, "cpu_percent": 0.0})
    for p in procs:
        try:
            name = (p.info.get("name") or "unknown").removesuffix(".exe")
            if name.lower() in ("system idle process", "idle"):
                continue
            a = apps[name]
            a["count"] += 1
            a["memory_mb"] += (p.info["memory_info"].rss if p.info.get("memory_info") else 0) / 2**20
            if sort == "cpu":
                a["cpu_percent"] += p.cpu_percent(None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    key = "cpu_percent" if sort == "cpu" else "memory_mb"
    return sorted(({"name": n, **v} for n, v in apps.items()), key=lambda e: -e[key])


def gpu_apps() -> List[Dict[str, Any]]:
    """Processes holding GPU memory (nvidia-smi); [] when unavailable."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
                              "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=8).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    rows = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 3 and parts[2].isdigit():
            rows.append({"pid": parts[0], "name": parts[1].split("\\")[-1].removesuffix(".exe"), "vram_mb": int(parts[2])})
    return sorted(rows, key=lambda r: -r["vram_mb"])


def ollama_models() -> List[str]:
    """Models Ollama currently keeps loaded (they hold RAM/VRAM until the keep-alive ends)."""
    try:
        import requests
        data = requests.get("http://127.0.0.1:11434/api/ps", timeout=3).json()
        return [f"{m.get('name')} ({_human(m.get('size_vram') or m.get('size') or 0)})" for m in data.get("models", [])]
    except Exception:
        return []


_TIPS = {
    "chrome": "Chrome tabs and extensions — close tabs you don't need or use Chrome's Memory Saver.",
    "msedge": "Edge tabs — close unused tabs or turn on Efficiency mode.",
    "brave": "Brave tabs — close tabs you don't need or turn on Memory Saver (Settings › System).",
    "firefox": "Firefox tabs — close unused tabs (about:memory shows which).",
    "svchost": "Windows background services — normal; a sudden jump is often Windows Update.",
    "ollama": "the local AI model (Ollama) — it frees memory after its keep-alive, or run 'ollama stop <model>'.",
    "python": "a Python program (possibly TOM itself or a script you ran).",
    "code": "VS Code and its extensions/language servers.",
    "steam": "Steam and its web helpers — exit Steam when you aren't gaming.",
    "steamwebhelper": "Steam's built-in browser — exit Steam when you aren't gaming.",
    "discord": "Discord — it keeps running in the tray.",
    "msmpeng": "Microsoft Defender scanning — usually temporary.",
    "memcompression": "Windows memory compression — a sign RAM is nearly full.",
    "vmmem": "WSL / Docker virtual machine memory — 'wsl --shutdown' frees it.",
    "vmmemwsl": "WSL virtual machine memory — 'wsl --shutdown' frees it.",
}


def _tip(name: str) -> str:
    return _TIPS.get(name.lower(), "")


def report(what: str = "all") -> Dict[str, Any]:
    import psutil
    vm = psutil.virtual_memory()
    lines: List[str] = []
    tips: List[str] = []
    cpu_now = psutil.cpu_percent(interval=0.5)
    lines.append(f"**Right now:** RAM {vm.percent:.0f}% used ({_human(vm.used)} of {_human(vm.total)}, "
                 f"{_human(vm.available)} free) · CPU {cpu_now:.0f}%")
    try:
        from tom_core.resources.gpu import query_gpu_memory
        g = query_gpu_memory()
        if g:
            lines[-1] += f" · VRAM {g.used_mb:,} of {g.total_mb:,} MB"
    except Exception:
        pass

    if what in ("ram", "all"):
        apps = processes_by_app("memory")[:8]
        lines.append("\n**Using the most memory:**")
        for a in apps:
            lines.append(f"- {a['name']}: {_human(a['memory_mb'] * 2**20)}"
                         + (f" across {a['count']} processes" if a["count"] > 1 else ""))
            if _tip(a["name"]):
                tips.append(f"{a['name']}: {_tip(a['name'])}")
    if what in ("cpu", "all"):
        apps = processes_by_app("cpu")[:6]
        cores = psutil.cpu_count() or 1
        lines.append("\n**Using the most CPU** (sampled over 1 s; 100% = one core of " + str(cores) + "):")
        for a in apps:
            lines.append(f"- {a['name']}: {a['cpu_percent']:.0f}%")
    if what in ("vram", "all"):
        gpu = gpu_apps()
        models = ollama_models()
        if gpu:
            lines.append("\n**Holding GPU memory:**")
            lines += [f"- {r['name']}: {r['vram_mb']:,} MB" for r in gpu[:6]]
        elif what == "vram":
            lines.append("\nWindows doesn't report per-app GPU memory for this GPU right now (nvidia-smi listed none).")
        if models:
            lines.append("Loaded AI models: " + ", ".join(models))
            tips.append(_TIPS["ollama"])
    if what in ("disk", "all"):
        lines.append("\n**Drives:**")
        for part in psutil.disk_partitions(all=False):
            try:
                u = psutil.disk_usage(part.mountpoint)
            except (PermissionError, OSError):
                continue
            lines.append(f"- {part.mountpoint} {u.percent:.0f}% full — {_human(u.free)} free of {_human(u.total)}")
            if u.percent >= 90:
                tips.append(f"{part.mountpoint} is nearly full — Settings › Storage › Temporary files, or say "
                            f"\"find the 5 largest files in my Downloads\".")
    if vm.percent >= 85:
        tips.insert(0, f"RAM is {vm.percent:.0f}% used, so Windows is swapping to disk — closing one of the apps above "
                       "will make the PC noticeably faster.")
    if tips:
        lines.append("\n**What you can do:**")
        lines += [f"- {t}" for t in dict.fromkeys(tips)]
    lines.append("\n_I haven't closed anything — say \"close <app>\" and I'll ask before doing it._")
    return {"status": "success", "response_type": "diagnostics", "verified": True,
            "evidence": "measured with psutil / nvidia-smi just now", "message": "\n".join(lines)}
