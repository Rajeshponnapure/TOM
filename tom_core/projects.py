"""Project profiles (PRD FR-016): root path, test command, environment hints and permitted tools.

Stored in tom_brain/projects.json. The coding workflow uses a profile's test command, and
"fix the failing tests in <project name>" resolves the name to its root.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from tools.project_paths import project_path

_NAME = re.compile(r"^[A-Za-z0-9][\w .-]{0,40}$")


def _file() -> str:
    return str(project_path("tom_brain", "projects.json"))


def _load() -> Dict[str, Dict[str, Any]]:
    try:
        with open(_file(), encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(data: Dict[str, Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(_file()), exist_ok=True)
    with open(_file(), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def detect(root: str) -> Dict[str, Any]:
    """Sensible defaults from what is in the folder."""
    def has(*names):
        return any(os.path.exists(os.path.join(root, n)) for n in names)
    if has("pyproject.toml", "pytest.ini", "setup.py", "requirements.txt", "tests"):
        return {"language": "python", "test_command": "python -m pytest -q", "build_command": ""}
    if has("package.json"):
        return {"language": "node", "test_command": "npm test", "build_command": "npm run build"}
    if has("Cargo.toml"):
        return {"language": "rust", "test_command": "cargo test", "build_command": "cargo build"}
    if has("go.mod"):
        return {"language": "go", "test_command": "go test ./...", "build_command": "go build ./..."}
    return {"language": "", "test_command": "", "build_command": ""}


def add(name: str, root: str, test_command: str = "", build_command: str = "", notes: str = "",
        tools: Optional[List[str]] = None) -> Dict[str, Any]:
    name = name.strip()
    if not _NAME.match(name):
        raise ValueError("Use a short project name (letters, digits, spaces, . _ -).")
    root = os.path.abspath(os.path.expanduser(root.strip().strip('"')))
    if not os.path.isdir(root):
        raise ValueError(f"No folder at {root}.")
    prof = {"name": name, "root": root, **detect(root), "notes": notes,
            "tools": tools or ["fs.read_text", "fs.list_dir", "fs.find_files", "git.status", "git.diff", "git.log",
                               "git.checkpoint", "shell.run"]}
    if test_command:
        prof["test_command"] = test_command
    if build_command:
        prof["build_command"] = build_command
    data = _load()
    data[name.lower()] = prof
    _save(data)
    return prof


def get(name_or_path: str) -> Optional[Dict[str, Any]]:
    data = _load()
    key = name_or_path.strip().strip('"').lower()
    if key in data:
        return data[key]
    full = os.path.normcase(os.path.abspath(os.path.expanduser(name_or_path.strip().strip('"'))))
    for prof in data.values():
        root = os.path.normcase(prof["root"])
        if full == root or full.startswith(root + os.sep):
            return prof
    return None


def remove(name: str) -> bool:
    data = _load()
    if data.pop(name.strip().lower(), None) is None:
        return False
    _save(data)
    return True


def all_profiles() -> List[Dict[str, Any]]:
    return list(_load().values())


def describe(p: Dict[str, Any]) -> str:
    return (f"{p['name']}: {p['root']}\n  language: {p.get('language') or 'unknown'} · tests: "
            f"{p.get('test_command') or '—'} · build: {p.get('build_command') or '—'}"
            + (f"\n  notes: {p['notes']}" if p.get("notes") else ""))
