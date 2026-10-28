"""Find a file the owner names ("read the file budget.xlsx") in the places their files live.

Live audit 2026-10-27: "read the file report.txt" went to chat, and the old reader looked for relative
names inside TOM's own source folder, not in the owner's folders, and couldn't read Word or PDF.
"""
from __future__ import annotations

import os
import re
from typing import List, Optional

READ_RX = re.compile(
    r"^(?:please\s+|can you\s+|could you\s+)?(read|show(?: me)?|display|view|summari[sz]e|what(?:'s| is) in|"
    r"what does|tell me what(?:'s| is) in|explain)\s+(?:out\s+)?(?:the\s+|my\s+|this\s+)?(?:file\s+|document\s+)?"
    r"[\"'“]?(?P<name>[^\"'”]+?\.[A-Za-z0-9]{2,5})[\"'”]?(?:\s+(?:file|document))?"
    r"(?P<rest>\s+(?:say|says|about|and|for).*)?\s*[?.!]?$", re.I)


def search_roots() -> List[str]:
    home = os.path.expanduser("~")
    onedrive = os.environ.get("OneDrive", "")
    roots = []
    try:
        from tools.project_paths import workspace_root
        roots.append(str(workspace_root()))
    except Exception:
        pass
    for base in filter(None, (onedrive, home)):
        for sub in ("Desktop", "Documents", "Downloads"):
            roots.append(os.path.join(base, sub))
    seen, out = set(), []
    for r in roots:
        key = os.path.normcase(os.path.abspath(r))
        if os.path.isdir(r) and key not in seen:
            seen.add(key)
            out.append(r)
    return out


def find(name: str, roots: Optional[List[str]] = None, max_depth: int = 4, limit: int = 8) -> List[str]:
    """Paths whose file name matches `name` (case-insensitive), newest first. An existing path is returned as is."""
    name = name.strip().strip("\"'")
    expanded = os.path.expandvars(os.path.expanduser(name))
    if os.path.isabs(expanded):
        return [expanded] if os.path.isfile(expanded) else []
    want = os.path.normcase(name.replace("\\", "/"))
    base = os.path.basename(want)
    hits: List[str] = []
    for root in roots if roots is not None else search_roots():
        direct = os.path.join(root, name)
        if os.path.isfile(direct):
            hits.append(direct)
            continue
        depth0 = root.rstrip("\\/").count(os.sep)
        for dirpath, dirs, files in os.walk(root):
            if dirpath.count(os.sep) - depth0 >= max_depth:
                dirs[:] = []
            dirs[:] = [d for d in dirs if not d.startswith(".") and d.lower() not in ("node_modules", "__pycache__",
                                                                                     "venv", ".venv", "appdata")]
            for f in files:
                if os.path.normcase(f) == base:
                    full = os.path.join(dirpath, f)
                    if os.path.normcase(full.replace("\\", "/")).endswith(want):
                        hits.append(full)
            if len(hits) >= limit * 3:
                break
    uniq = list(dict.fromkeys(os.path.abspath(h) for h in hits))
    return sorted(uniq, key=lambda p: -os.path.getmtime(p))[:limit]
