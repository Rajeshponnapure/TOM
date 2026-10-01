from __future__ import annotations

import os
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def project_path(*parts: str) -> Path:
    return PROJECT_ROOT.joinpath(*parts)


def project_path_str(*parts: str) -> str:
    return str(project_path(*parts))


# ── User workspace (where TOM builds things for the user) ────────────────────
# TOM must NEVER scatter user deliverables (websites, decks, code projects,
# reports) inside its own repo. They go to a dedicated workspace on the user's
# Desktop — a sibling of the TOM folder, not a child of it — unless the user
# names an explicit path or overrides TOM_WORKSPACE_DIR.

def _desktop_dir() -> Path:
    """Best guess at the real Desktop, honouring OneDrive redirection."""
    candidates = []
    for env in ("OneDrive", "OneDriveConsumer", "USERPROFILE", "HOME"):
        base = (os.environ.get(env) or "").strip()
        if base:
            candidates.append(Path(base) / "Desktop")
    candidates.append(Path.home() / "Desktop")
    for cand in candidates:
        try:
            if cand.is_dir():
                return cand
        except OSError:
            continue
    return Path.home()


def _safe_component(name: str) -> str:
    """Turn a free-text project name into one safe path component."""
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", (name or "").strip())
    cleaned = cleaned.strip(". ").replace("..", "_")
    return cleaned[:60] or "project"


def workspace_root() -> Path:
    """The folder TOM builds user deliverables into.

    Order: TOM_WORKSPACE_DIR env override → "<Desktop>/TOM Workspace". Created
    on demand. Falls back to the repo's output/ only if the workspace cannot be
    created (e.g. a read-only Desktop), so a deliverable is never lost.
    """
    override = (os.environ.get("TOM_WORKSPACE_DIR") or "").strip()
    root = Path(override).expanduser() if override else _desktop_dir() / "TOM Workspace"
    try:
        root.mkdir(parents=True, exist_ok=True)
        return root
    except Exception:
        fallback = PROJECT_ROOT / "output"
        try:
            fallback.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        return fallback


def workspace_path(*parts: str) -> Path:
    return workspace_root().joinpath(*parts)


def resolve_deliverable_dir(explicit: str = "", subfolder: str = "") -> Path:
    """Where a user-requested deliverable should be written.

    - An explicit ABSOLUTE path the user named always wins (that is the whole
      point of "build it in D:\\Projects\\Foo").
    - Otherwise the Desktop workspace, optionally inside a per-project subfolder
      so each build gets its own tidy directory.

    Never silently targets the TOM project tree.
    """
    if explicit:
        p = Path(explicit.strip().strip('"').strip("'")).expanduser()
        if p.is_absolute():
            try:
                p.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            return p
    root = workspace_root()
    if subfolder:
        root = root / _safe_component(subfolder)
        try:
            root.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
    return root


def resolve_deliverable_path(raw_path: str, subfolder: str = "") -> str:
    """Resolve one output file path for a user deliverable.

    An absolute path is honoured as-is. A relative path (what an LLM emits in
    "--- FILE: app/index.html ---") is placed under the workspace, inside the
    per-project subfolder when given — so a generated scaffold lands in
    "<Desktop>/TOM Workspace/<project>/app/index.html", never in the repo.
    """
    raw = (raw_path or "").strip().strip('"').strip("'")
    p = Path(raw).expanduser()
    if p.is_absolute():
        return str(p)
    base = resolve_deliverable_dir(subfolder=subfolder) if subfolder else workspace_root()
    return str(base / raw)
