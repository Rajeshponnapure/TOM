"""
File-system task suite (Phase B2) — search, organize, bulk-rename, zip, convert.

Safety contract:
  * Anything that MOVES or RENAMES builds a dry-run PLAN first; the router
    asks user approval with exact counts before execute_plan() touches disk.
  * Never follows into system dirs; depth- and count-limited walks.
  * Pure stdlib (+ optional Pillow for image conversion).
"""

import fnmatch
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


def resolve_folder(text: str) -> Optional[str]:
    """'downloads' → C:\\Users\\me\\Downloads; absolute paths pass through."""
    t = (text or "").strip().strip('"').rstrip("/\\")
    if not t:
        return None
    low = t.lower()
    for key, real in KNOWN_FOLDERS.items():
        if low == key or low == f"my {key}" or low.endswith(os.sep + key):
            cand = Path.home() / real
            return str(cand) if cand.is_dir() else None
    return t if os.path.isdir(t) else None


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
        root = resolve_folder(root) or root
        if not os.path.isdir(root):
            return {"status": "error", "message": f"Folder not found: {root}"}
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
    def plan_organize_by_type(self, folder: str) -> Dict[str, Any]:
        return self._plan_organize(folder, mode="type")

    def plan_organize_by_year(self, folder: str) -> Dict[str, Any]:
        return self._plan_organize(folder, mode="year")

    def _plan_organize(self, folder: str, mode: str) -> Dict[str, Any]:
        folder = resolve_folder(folder) or folder
        if not os.path.isdir(folder):
            return {"status": "error", "message": f"Folder not found: {folder}"}
        moves: List[Tuple[str, str]] = []
        for entry in os.scandir(folder):
            if not entry.is_file():
                continue
            ext = os.path.splitext(entry.name)[1]
            if mode == "type":
                sub = _group_for(ext)
            else:
                sub = str(datetime.fromtimestamp(entry.stat().st_mtime).year)
            dest = os.path.join(folder, sub, entry.name)
            if os.path.abspath(entry.path) != os.path.abspath(dest):
                moves.append((entry.path, dest))
        summary: Dict[str, int] = {}
        for _src, dst in moves:
            sub = os.path.basename(os.path.dirname(dst))
            summary[sub] = summary.get(sub, 0) + 1
        return {"status": "plan", "folder": folder, "moves": moves,
                "summary": summary,
                "message": f"Plan: move {len(moves)} file(s) in {folder} into "
                           f"{len(summary)} subfolder(s): "
                           + ", ".join(f"{k} ({v})" for k, v in sorted(summary.items()))}

    def plan_bulk_rename(self, folder: str, find: str, replace: str) -> Dict[str, Any]:
        folder = resolve_folder(folder) or folder
        if not os.path.isdir(folder):
            return {"status": "error", "message": f"Folder not found: {folder}"}
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
            except OSError:
                skipped += 1
        return {"status": "success", "moved": done, "skipped": skipped,
                "message": f"Done: {done} file(s) processed"
                           + (f", {skipped} skipped." if skipped else ".")}

    # ── Zip ──────────────────────────────────────────────────────────────
    def zip_folder(self, folder: str, dest: str = None) -> Dict[str, Any]:
        folder = resolve_folder(folder) or folder
        if not os.path.isdir(folder):
            return {"status": "error", "message": f"Folder not found: {folder}"}
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
        src = resolve_folder(source) or source
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
