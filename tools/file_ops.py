"""
File-system task suite (Phase B2) — search, organize, bulk-rename, zip, convert.

Safety contract:
  * Anything that MOVES or RENAMES builds a dry-run PLAN first; the router
    asks user approval with exact counts before execute_plan() touches disk.
  * Never follows into system dirs; depth- and count-limited walks.
  * Pure stdlib (+ optional Pillow for image conversion).
"""

import fnmatch
import json
import os
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SKIP_DIRS = {"windows", "program files", "program files (x86)", "$recycle.bin",
             "appdata", "node_modules", "__pycache__", ".git", "venv",
             "system volume information"}
MAX_FILES = 5000
JOURNAL_PATH = Path(__file__).resolve().parents[1] / "data" / "file_ops_journal.json"

TYPE_GROUPS = {
    "Images":      {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".heic"},
    "Documents":   {".pdf", ".docx", ".doc", ".txt", ".md", ".rtf", ".odt"},
    "Spreadsheets": {".xlsx", ".xls", ".csv", ".ods"},
    "Presentations": {".pptx", ".ppt", ".odp"},
    "Audio":       {".mp3", ".wav", ".flac", ".m4a", ".ogg"},
    "Video":       {".mp4", ".mkv", ".avi", ".mov", ".webm"},
    "Archives":    {".zip", ".rar", ".7z", ".tar", ".gz"},
    "Code":        {".py", ".js", ".ts", ".html", ".css", ".json", ".ipynb"},
    "Installers":  {".exe", ".msi"},
}

KNOWN_FOLDERS = {"downloads": "Downloads", "documents": "Documents",
                 "desktop": "Desktop", "pictures": "Pictures",
                 "photos": "Pictures", "music": "Music", "videos": "Videos"}


def _known_key(text: str) -> Optional[str]:
    """'downloads' / 'my downloads' / 'the Downloads folder' -> 'downloads'; anything else -> None."""
    low = re.sub(r"^(?:(?:my|the)\s+)+", "", (text or "").strip().lower())
    low = re.sub(r"\s+(?:folder|directory)$", "", low)
    return low if low in KNOWN_FOLDERS else None


def resolve_folder(text: str) -> Optional[str]:
    """The folder a user's words refer to, or None if it does not exist.

    * A well-known NAME ('downloads', 'my desktop', 'the documents folder') means that folder in the
      user's profile (or TOM_<NAME>_DIR if set, e.g. a sandbox copy).
    * Anything else is a PATH and is used exactly as given. A path that merely ends in "Downloads"
      is NOT the Downloads folder: it used to be matched by name, so pointing TOM at
      ...\\demo\\sandbox\\Downloads organized the user's real Downloads instead.
    """
    t = (text or "").strip().strip('"').strip("'").rstrip("/\\")
    if not t:
        return None
    key = _known_key(t)
    if key:
        real = KNOWN_FOLDERS[key]
        # TOM_<NAME>_DIR (e.g. TOM_DOWNLOADS_DIR) redirects a known folder —
        # handy for a sandbox copy or a non-standard profile location.
        override = os.environ.get(f"TOM_{real.upper()}_DIR", "").strip()
        cand = Path(os.path.expandvars(os.path.expanduser(override))) if override else Path.home() / real
        return str(cand) if cand.is_dir() else None
    expanded = os.path.expandvars(os.path.expanduser(t))
    if not (os.path.isabs(expanded) or "/" in t or "\\" in t or t.startswith("~")):
        return None                  # a bare word that is not a known folder is not a path: never guess from the cwd
    return expanded if os.path.isdir(expanded) else None


def _locate(text: str) -> str:
    """resolve_folder, as a plain string: '' when the folder does not exist."""
    return resolve_folder(text) or ""


def _not_found(text: str) -> Dict[str, Any]:
    return {"status": "error", "message": f"Folder not found: {text}"}


def _protected(path: str) -> bool:
    """True for system locations (C:\\Windows, Program Files, ...) TOM must never reorganize."""
    try:
        from safety.guards import SafetyGuards
        return not SafetyGuards().check_file_path_safe(path)
    except Exception:
        return False


def _protected_error(folder: str) -> Dict[str, Any]:
    return {"status": "error",
            "message": f"I won't reorganize {folder}: it is a protected system location."}


def _group_for(ext: str) -> str:
    for group, exts in TYPE_GROUPS.items():
        if ext.lower() in exts:
            return group
    return "Other"


def _safe_walk(root: str):
    count = 0
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]
        for f in files:
            count += 1
            if count > MAX_FILES:
                return
            yield os.path.join(dirpath, f)


class FileOps:
    # ── Search ───────────────────────────────────────────────────────────
    def find_files(self, root: str, pattern: str = "*", limit: int = 200) -> Dict[str, Any]:
        located = _locate(root)
        if not located:
            return _not_found(root)
        root = located
        hits: List[str] = []
        for path in _safe_walk(root):
            if fnmatch.fnmatch(os.path.basename(path).lower(), pattern.lower()):
                hits.append(path)
                if len(hits) >= limit:
                    break
        return {"status": "success", "count": len(hits), "files": hits,
                "message": f"Found {len(hits)} file(s) matching '{pattern}' under {root}."
                           + ("" if hits else " (none)")}

    # ── Organize (plan → approval → execute) ─────────────────────────────
    def plan_organize_by_type(self, folder: str, rules: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Group files by type. `rules` (tools.memory_rules.FolderRule) — the
        user's remembered preferences — are applied first and override defaults."""
        return self._plan_organize(folder, mode="type", rules=rules)

    def plan_organize_by_year(self, folder: str, rules: Optional[List[Any]] = None) -> Dict[str, Any]:
        return self._plan_organize(folder, mode="year", rules=rules)

    def plan_move_by_extension(self, folder: str, extension: str, destination: str) -> Dict[str, Any]:
        """Plan a narrow move, e.g. only PDFs into a user-named subfolder."""
        extension = "." + extension.lower().lstrip(".")
        return self._plan_move(folder, lambda name: Path(name).suffix.lower() == extension,
                               extension, destination)

    def plan_move_by_group(self, folder: str, group: str, destination: str) -> Dict[str, Any]:
        """Plan a move of one file type group (Images, Video, Audio, ...) into a subfolder."""
        return self._plan_move(folder, lambda name: _group_for(Path(name).suffix) == group,
                               group.lower(), destination)

    def _plan_move(self, folder: str, matches, what: str, destination: str) -> Dict[str, Any]:
        located = _locate(folder)
        if not located:
            return _not_found(folder)
        folder = located
        if _protected(folder):
            return _protected_error(folder)
        destination = destination.strip().replace("\\", "/")
        parts = [part for part in destination.split("/") if part and part != "."]
        if not parts or any(part == ".." for part in parts):
            return {"status": "error", "message": "Choose a folder name inside the selected folder."}
        moves = []
        for entry in os.scandir(folder):
            if entry.is_file() and matches(entry.name):
                moves.append((entry.path, os.path.join(folder, *parts, entry.name)))
        label = "/".join(parts)
        return {"status": "plan", "folder": folder, "moves": moves,
                "summary": {label: len(moves)} if moves else {}, "kept": [],
                "applied_rules": [],
                "message": f"Plan: move {len(moves)} {what} file(s) in {folder} into {label}/."}

    def _plan_organize(self, folder: str, mode: str, rules: Optional[List[Any]] = None) -> Dict[str, Any]:
        located = _locate(folder)
        if not located:
            return _not_found(folder)
        folder = located
        if _protected(folder):
            return _protected_error(folder)
        rules = list(rules or [])
        moves: List[Tuple[str, str]] = []
        kept: List[str] = []
        applied: Dict[str, Dict[str, Any]] = {}
        for entry in os.scandir(folder):
            if not entry.is_file():
                continue
            ext = os.path.splitext(entry.name)[1]
            group = _group_for(ext)
            rule = None
            for candidate in rules:
                if candidate.matches(entry.name, group):
                    rule = candidate
                    break
            if rule is not None:
                hit = applied.setdefault(rule.describe(), {"rule": rule, "files": 0})
                hit["files"] += 1
                if rule.action == "skip":
                    kept.append(entry.name)
                    continue
                sub = rule.dest
            elif mode == "type":
                sub = group
            else:
                sub = str(datetime.fromtimestamp(entry.stat().st_mtime).year)
            dest = os.path.normpath(os.path.join(folder, *sub.replace("\\", "/").split("/"), entry.name))
            if os.path.abspath(entry.path) != os.path.abspath(dest):
                moves.append((entry.path, dest))
        summary: Dict[str, int] = {}
        for src, dst in moves:
            sub = os.path.relpath(os.path.dirname(dst), folder)
            summary[sub] = summary.get(sub, 0) + 1
        message = (f"Plan: move {len(moves)} file(s) in {folder} into "
                   f"{len(summary)} subfolder(s): "
                   + ", ".join(f"{k} ({v})" for k, v in sorted(summary.items())))
        if kept:
            message += f". Leaving {len(kept)} file(s) in place"
        return {"status": "plan", "folder": folder, "moves": moves,
                "summary": summary, "kept": kept,
                "applied_rules": [{"rule": v["rule"].describe(), "files": v["files"],
                                   "source": getattr(v["rule"], "source", "")}
                                  for v in applied.values()],
                "message": message}

    def plan_bulk_rename(self, folder: str, find: str, replace: str) -> Dict[str, Any]:
        located = _locate(folder)
        if not located:
            return _not_found(folder)
        folder = located
        if _protected(folder):
            return _protected_error(folder)
        try:
            rx = re.compile(find)
        except re.error as e:
            return {"status": "error", "message": f"Bad pattern: {e}"}
        moves: List[Tuple[str, str]] = []
        for entry in os.scandir(folder):
            if entry.is_file() and rx.search(entry.name):
                new_name = rx.sub(replace, entry.name)
                if new_name and new_name != entry.name:
                    moves.append((entry.path, os.path.join(folder, new_name)))
        return {"status": "plan", "folder": folder, "moves": moves,
                "summary": {"renames": len(moves)},
                "message": f"Plan: rename {len(moves)} file(s) in {folder} "
                           f"('{find}' → '{replace}'). Examples: "
                           + "; ".join(f"{os.path.basename(s)} → {os.path.basename(d)}"
                                       for s, d in moves[:3])}

    def execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a previously built plan (collision-safe)."""
        moves = plan.get("moves", [])
        done, skipped = 0, 0
        completed_moves: List[Tuple[str, str]] = []
        for src, dst in moves:
            try:
                if not os.path.isfile(src):
                    skipped += 1
                    continue
                final = dst
                base, ext = os.path.splitext(dst)
                n = 1
                while os.path.exists(final):
                    final = f"{base}_{n}{ext}"
                    n += 1
                os.makedirs(os.path.dirname(final), exist_ok=True)
                shutil.move(src, final)
                done += 1
                completed_moves.append((src, final))
            except OSError:
                skipped += 1
        return {"status": "success", "moved": done, "skipped": skipped,
                "completed_moves": completed_moves,
                "message": f"Done: {done} file(s) processed"
                           + (f", {skipped} skipped." if skipped else ".")}

    # ── Undo the latest organization ────────────────────────────────────
    @staticmethod
    def _load_journal() -> List[Dict[str, Any]]:
        try:
            with JOURNAL_PATH.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    @staticmethod
    def _save_journal(entries: List[Dict[str, Any]]) -> None:
        JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        temp_path = JOURNAL_PATH.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(entries[-50:], handle, indent=2)
        os.replace(temp_path, JOURNAL_PATH)

    def record_organization(self, plan: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Persist only moves that actually completed, so a later undo is exact."""
        completed = result.get("completed_moves") or []
        if not completed:
            return
        entries = self._load_journal()
        entries.append({"kind": "organize", "folder": os.path.abspath(plan["folder"]),
                        "moves": [[source, dest] for source, dest in completed]})
        self._save_journal(entries)

    def plan_undo_last_organization(self, folder: Optional[str] = None) -> Dict[str, Any]:
        """Build a verified reverse-move plan for the latest organization.

        With a folder: that folder's latest organization. Without one ("revert what you just did"):
        the most recent organization anywhere - it used to fall back to Downloads, whichever folder
        had actually been organized.
        """
        root = ""
        if folder:
            root = os.path.abspath(_locate(folder) or folder)
        for entry in reversed(self._load_journal()):
            if entry.get("kind") != "organize" or (root and entry.get("folder") != root):
                continue
            root = entry.get("folder", root)
            moves = []
            missing = 0
            for original, current in entry.get("moves", []):
                if os.path.isfile(current):
                    moves.append((current, original))
                else:
                    missing += 1
            if not moves:
                return {"status": "error", "message": "The latest organization can no longer be undone: its moved files are no longer where TOM placed them."}
            return {"status": "plan", "folder": root, "moves": moves, "journal_entry": entry,
                    "missing": missing,
                    "message": f"Plan: restore {len(moves)} file(s) to {root}"
                               + (f"; {missing} file(s) were changed or removed and will be left alone." if missing else ".")}
        return {"status": "error",
                "message": ("There is no recorded TOM organization to undo for this folder." if folder
                            else "There is no recorded TOM organization to undo.")}

    def execute_undo_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Reverse a verified journal entry and remove empty TOM-created folders."""
        result = self.execute_plan(plan)
        restored = result["moved"]
        root = plan["folder"]
        if result["skipped"] == 0 and plan.get("missing", 0) == 0:
            entries = self._load_journal()
            target = plan.get("journal_entry")
            self._save_journal([entry for entry in entries if entry != target])
        for current, _original in plan.get("moves", []):
            parent = os.path.dirname(current)
            while os.path.abspath(parent).startswith(root + os.sep):
                try:
                    os.rmdir(parent)
                except OSError:
                    break
                parent = os.path.dirname(parent)
        return {**result, "message": f"Restored {restored} file(s) to {root}"
                + (f", {result['skipped']} skipped." if result["skipped"] else ".")}

    # ── Zip ──────────────────────────────────────────────────────────────
    def zip_folder(self, folder: str, dest: str = None) -> Dict[str, Any]:
        located = _locate(folder)
        if not located:
            return _not_found(folder)
        folder = located
        dest = dest or folder.rstrip("/\\") + ".zip"
        count = 0
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in _safe_walk(folder):
                if os.path.abspath(path) == os.path.abspath(dest):
                    continue
                zf.write(path, os.path.relpath(path, folder))
                count += 1
        size_mb = os.path.getsize(dest) / 1e6
        return {"status": "success", "zip": dest, "files": count,
                "message": f"Zipped {count} file(s) → {dest} ({size_mb:.1f} MB)."}

    # ── Convert images ───────────────────────────────────────────────────
    def convert_images(self, source: str, to_ext: str = "png") -> Dict[str, Any]:
        try:
            from PIL import Image
        except ImportError:
            return {"status": "error",
                    "message": "Pillow not installed. Fix: pip install Pillow"}
        to_ext = to_ext.lower().lstrip(".")
        if to_ext == "jpg":
            to_ext = "jpeg"
        src = _locate(source) or (source if os.path.isfile(source) else "")
        files: List[str] = []
        if os.path.isfile(src):
            files = [src]
        elif os.path.isdir(src):
            files = [e.path for e in os.scandir(src) if e.is_file()
                     and os.path.splitext(e.name)[1].lower() in
                     {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}]
        if not files:
            return {"status": "error", "message": f"No images found at: {source}"}
        out, failed = [], 0
        for f in files[:200]:
            try:
                img = Image.open(f)
                if to_ext == "jpeg" and img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                target = os.path.splitext(f)[0] + "." + ("jpg" if to_ext == "jpeg" else to_ext)
                if os.path.abspath(target) == os.path.abspath(f):
                    continue
                img.save(target)
                out.append(target)
            except Exception:
                failed += 1
        return {"status": "success", "converted": out, "failed": failed,
                "message": f"Converted {len(out)} image(s) to .{to_ext}"
                           + (f" ({failed} failed)." if failed else ".")}
