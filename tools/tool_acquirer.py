"""
Tool acquisition for TOM — getting a capability TOM does not yet have, safely.

Three mechanisms, in increasing order of trust required:

  * install_package(spec)  — install a library from PyPI into TOM's own venv
  * clone_repo(url)        — git-clone a public repo into the workspace and
                             READ it (list files + README); it is never run
  * save_tool(name, code)  — write a generated tool module into the workspace
                             for review; it is not imported or executed

What this module deliberately does NOT do is download code from the internet
and execute it. Fetching and running untrusted code is arbitrary remote code
execution; acquisition stops at install (PyPI, which the user approves) and
read-only inspection. Everything runs as an arg list (never shell=True) and
times out.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional

from tools.project_paths import workspace_root

_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

# A PyPI requirement specifier we are willing to install: name, optional
# extras, optional pinned version. Anything with shell metacharacters, URLs or
# spaces is rejected so nothing but a package name can reach pip.
_PKG_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
                     r"(?:\[[A-Za-z0-9,._-]+\])?"
                     r"(?:(?:==|>=|<=|~=|!=|>|<)[A-Za-z0-9._*+-]+)?$")

# Hosts we will clone from (public forges). Anything else is refused.
_ALLOWED_GIT_HOSTS = ("github.com", "gitlab.com", "bitbucket.org",
                      "codeberg.org", "git.sr.ht")


class ToolAcquirer:
    def __init__(self):
        self._dir = os.path.join(str(workspace_root()), "acquired_tools")
        self._repos = os.path.join(str(workspace_root()), "acquired_repos")

    # ── Install a library from PyPI ──────────────────────────────────────
    def install_package(self, spec: str, timeout: float = 300.0) -> Dict[str, Any]:
        """pip-install one package into TOM's venv (caller must get approval)."""
        spec = (spec or "").strip()
        if not _PKG_RE.match(spec):
            return {"status": "error",
                    "message": (f"'{spec}' is not a valid PyPI package name, so TOM will not "
                                "pass it to pip. Use a plain name like 'requests' or 'pandas==2.2.0'.")}
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", spec],
                capture_output=True, timeout=timeout, creationflags=_NO_WINDOW, encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": f"pip install {spec} timed out after {int(timeout)}s."}
        except Exception as exc:
            return {"status": "error", "message": f"Could not run pip: {exc}"}
        tail = (proc.stdout or "")[-600:] + (("\n" + proc.stderr[-400:]) if proc.stderr else "")
        if proc.returncode == 0:
            return {"status": "success", "response_type": "tool_acquired",
                    "message": f"Installed '{spec}'. TOM can use it now.\n{tail.strip()}",
                    "package": spec}
        return {"status": "error",
                "message": f"pip could not install '{spec}' (exit {proc.returncode}).\n{tail.strip()}"}

    # ── Clone + inspect a public repo (read-only) ────────────────────────
    def clone_repo(self, url: str, timeout: float = 180.0) -> Dict[str, Any]:
        """Shallow-clone a public repo into the workspace and summarize it.

        The repo is READ only — nothing in it is installed or executed.
        """
        url = (url or "").strip().strip('"').strip("'")
        host = ""
        m = re.match(r"https://([^/]+)/", url)
        if m:
            host = m.group(1).lower()
        if not (url.startswith("https://") and host in _ALLOWED_GIT_HOSTS):
            return {"status": "blocked",
                    "message": ("TOM only clones public repos over https from "
                                f"{', '.join(_ALLOWED_GIT_HOSTS)}. "
                                f"'{url or 'that'}' is not one of them.")}
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", url.rstrip("/").split("/")[-1].replace(".git", "")) or "repo"
        os.makedirs(self._repos, exist_ok=True)
        dest = os.path.join(self._repos, name)
        if os.path.exists(dest):
            import shutil
            shutil.rmtree(dest, ignore_errors=True)
        try:
            proc = subprocess.run(
                ["git", "clone", "--depth", "1", url, dest],
                capture_output=True, timeout=timeout, creationflags=_NO_WINDOW, encoding="utf-8", errors="replace")
        except FileNotFoundError:
            return {"status": "error", "message": "git is not installed. Fix: install Git for Windows."}
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": f"git clone timed out after {int(timeout)}s."}
        if proc.returncode != 0:
            return {"status": "error",
                    "message": f"Could not clone '{url}'.\n{(proc.stderr or '')[-400:]}"}
        files = self._top_level(dest)
        readme = self._read_readme(dest)
        msg = (f"Cloned '{url}' into:\n{dest}\n\n"
               f"Top-level files:\n  " + "\n  ".join(files[:40]) +
               (f"\n\nREADME (excerpt):\n{readme[:1200]}" if readme else "") +
               "\n\nNote: TOM has NOT run or installed anything from this repo — "
               "review it first, then ask me to install specific requirements if you want.")
        return {"status": "success", "response_type": "tool_acquired",
                "message": msg, "path": dest, "files": files}

    @staticmethod
    def _top_level(path: str) -> List[str]:
        try:
            return sorted(os.listdir(path))
        except OSError:
            return []

    @staticmethod
    def _read_readme(path: str) -> str:
        for name in ("README.md", "README.rst", "README.txt", "README"):
            fp = os.path.join(path, name)
            if os.path.isfile(fp):
                try:
                    with open(fp, "r", encoding="utf-8", errors="replace") as f:
                        return f.read()
                except OSError:
                    return ""
        return ""

    # ── Save a generated tool module (not executed) ──────────────────────
    def save_tool(self, name: str, code: str) -> Dict[str, Any]:
        """Write a generated tool module into the workspace for review.

        The file is saved, never imported or run — the user/developer reviews
        it and wires it in deliberately.
        """
        slug = re.sub(r"[^A-Za-z0-9_]+", "_", (name or "").strip().lower()).strip("_") or "tool"
        if not (code or "").strip():
            return {"status": "error", "message": "No tool code was provided to save."}
        os.makedirs(self._dir, exist_ok=True)
        path = os.path.join(self._dir, f"{slug}.py")
        banner = (f'"""Acquired tool: {name}\n\n'
                  'Generated by TOM for review. It is NOT auto-imported or executed — '
                  'read it, then wire it in deliberately if you want to use it.\n"""\n\n')
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(banner + code.strip() + "\n")
        except OSError as exc:
            return {"status": "error", "message": f"Could not save the tool: {exc}"}
        return {"status": "success", "response_type": "tool_acquired",
                "message": (f"Saved a new tool module for review:\n{path}\n\n"
                            "It is not active yet — review it, then import it where you need it."),
                "path": path}

    def list_acquired(self) -> Dict[str, Any]:
        tools = self._top_level(self._dir) if os.path.isdir(self._dir) else []
        repos = self._top_level(self._repos) if os.path.isdir(self._repos) else []
        return {"status": "success", "response_type": "tool_acquired",
                "message": (f"Acquired tool modules: {', '.join(tools) or 'none'}\n"
                            f"Cloned repos: {', '.join(repos) or 'none'}"),
                "tools": tools, "repos": repos}
