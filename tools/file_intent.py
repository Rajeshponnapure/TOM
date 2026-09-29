"""Understand a file request as a whole sentence.

`understand()` turns "Hi Tom, could you organize the files in my downloads folder that is at
C:\\...\\sandbox\\Downloads" into a structured FileIntent (operation, folder, file types, destination...).

Two readers, one result:
  * rules - deterministic, no model needed. Always runs; it is the fallback.
  * an LLM (when the agent has one) - reads the whole sentence and fills the slots the rules cannot,
    e.g. "gather my slide decks from the Desktop into a folder called Decks".

The model is never trusted blindly. Everything it returns is validated against what the user actually
wrote: a folder must be quoted from the request (or be a well-known name like "downloads"), a
destination must be a plain folder name, and the model cannot turn a find/undo/zip/convert into moves.
A path the user typed always beats whatever the model says. If the model is unavailable, slow or
returns nonsense, the rules result is used.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

KNOWN_FOLDER_WORDS = ("downloads", "documents", "desktop", "pictures", "photos", "music", "videos")
ALLOWED_OPERATIONS = ("organize", "move", "find", "rename", "zip", "convert", "undo")
# The rules are certain about these from an explicit keyword; a model may not override them.
KEYWORD_OPERATIONS = ("undo", "find", "zip", "convert", "rename")

# (word pattern, ("ext", ".pdf") | ("group", "Images"))
MOVE_TYPES: Tuple[Tuple[str, Tuple[str, str]], ...] = (
    (r"pdfs?", ("ext", ".pdf")),
    (r"images?|photos?|pictures", ("group", "Images")),
    (r"videos?|movies", ("group", "Video")),
    (r"music|songs?|audio|mp3s?", ("group", "Audio")),
    (r"spreadsheets?|excel files?|csvs?", ("group", "Spreadsheets")),
    (r"presentations?|slides?|slide decks?|decks?|powerpoints?", ("group", "Presentations")),
    (r"zips?|archives?", ("group", "Archives")),
    (r"installers?", ("group", "Installers")),
    (r"word docs?|word documents?|docx", ("ext", ".docx")),
    (r"text files?|txt", ("ext", ".txt")),
)

_QUOTED = r"[\"\u201c\u2018']([^\"\u201d\u2019']+[\\/][^\"\u201d\u2019']*)[\"\u201d\u2019']"
_BARE_PATH = r"((?<![\w])(?:[A-Za-z]:[\\/][^\s\"'\u201c\u201d]+|~?/[^\s\"'\u201c\u201d]+))"
PATH_TOKEN = re.compile(f"{_QUOTED}|{_BARE_PATH}")
_TRAILING_PUNCT = ".,;:!?)]}"


@dataclass
class FileIntent:
    operation: str = "unknown"
    folder: str = ""                     # a path exactly as the user gave it, or a known folder word
    folder_is_path: bool = False         # True when the user typed a path (it always wins)
    organize_by: str = "type"            # "type" | "year"
    move_type: Optional[Tuple[str, str]] = None
    destination: str = ""
    find_pattern: str = "*"
    rename_from: str = ""
    rename_to: str = ""
    convert_to: str = "png"
    source: str = "rules"                # "rules" | "llm+rules"


# ── the rules reader ─────────────────────────────────────────────────────────

def _extend_with_spaces(path: str, text_after: str) -> str:
    """'C:\\Users\\Ann Lee\\Downloads' typed without quotes: take following words while the folder exists."""
    if os.path.isdir(path):
        return path
    words = text_after.split()
    best, candidate = path, path
    for word in words[:4]:
        candidate = f"{candidate} {word}"
        stripped = candidate.rstrip(_TRAILING_PUNCT)
        if os.path.isdir(os.path.expandvars(os.path.expanduser(stripped))):
            best = stripped
    return best


def find_path(command: str) -> str:
    """A filesystem path typed in the request ('' if none). Quoted paths and unquoted ones both work."""
    match = PATH_TOKEN.search(command)
    if not match:
        return ""
    if match.group(1):
        return match.group(1).strip()
    raw = match.group(2)
    path = raw.rstrip(_TRAILING_PUNCT)
    if not os.path.isdir(os.path.expandvars(os.path.expanduser(path))):
        path = _extend_with_spaces(path, command[match.end():])
    return path


def pick_folder(command: str) -> str:
    """The folder a request is about: an explicit path, else the name after in/from/inside/of, else the
    first well-known folder mentioned. '' when the request names none."""
    path = find_path(command)
    if path:
        return path
    words = "|".join(KNOWN_FOLDER_WORDS)
    after_prep = re.search(rf"\b(?:in|from|inside|within|of|under|on)\s+(?:my\s+|the\s+)?({words})\b", command, re.IGNORECASE)
    if after_prep:
        return after_prep.group(1)
    bare = re.search(rf"\b(?:my\s+)?({words})\b", command, re.IGNORECASE)
    return bare.group(1) if bare else ""


def type_spec_for(word: str) -> Optional[Tuple[str, str]]:
    """'pdfs' / 'slide decks' / '.docx' -> ('ext', '.pdf') / ('group', 'Presentations') / ('ext', '.docx')."""
    word = (word or "").strip().lower()
    ext = re.fullmatch(r"\.?([a-z0-9]{2,5})", word)
    for pattern, spec in MOVE_TYPES:
        if re.fullmatch(pattern, word):
            return spec
    if word.startswith(".") and ext:
        return ("ext", "." + ext.group(1))
    return None


def parse_move(command: str) -> Tuple[Optional[Tuple[str, str]], str]:
    """(file type, destination subfolder) for 'move the pdfs ... into a folder called Invoices'."""
    low = command.lower()
    spec = next((s for pat, s in MOVE_TYPES if re.search(rf"\b(?:{pat})\b", low)), None)
    if spec is None:
        ext = re.search(r"(?<![\w/\\])\.([a-z0-9]{2,5})\b", low)
        spec = ("ext", "." + ext.group(1)) if ext else None
    skip = {"the", "a", "an", "my", "new", "folder", "subfolder", "directory", "named", "called"}
    dest = ""
    for m in re.finditer(
            r"\b(?:into|to)\s+(?:(?:an?|the|my|new)\s+)*(?:(?:sub)?folder\s+|directory\s+)?"
            r"(?:(?:named|called)\s+)?[\"'\u201c]?([A-Za-z0-9][\w-]*)[\"'\u201d]?", command, re.IGNORECASE):
        if m.group(1).lower() not in skip:
            dest = m.group(1)
    return spec, dest


def parse_rules(command: str) -> FileIntent:
    c = command.lower()
    intent = FileIntent()
    path = find_path(command)
    intent.folder = pick_folder(command)
    intent.folder_is_path = bool(path)

    if re.search(r"\b(revert|undo|roll ?back|restore)\b", c):
        intent.operation = "undo"
    elif re.search(r"\bfind\b", c):
        intent.operation = "find"
        ext = re.search(r"\b(pdfs?|images?|photos?|docs?|documents|videos?|\*?\.[a-z0-9]{2,4})\b", c)
        token = ext.group(1) if ext else "*"
        intent.find_pattern = {"pdf": "*.pdf", "pdfs": "*.pdf", "image": "*.jpg", "images": "*.*", "photo": "*.jpg",
                               "photos": "*.*", "doc": "*.doc*", "docs": "*.doc*", "documents": "*.*",
                               "video": "*.mp4", "videos": "*.*"}.get(token, token if "." in token else "*")
    elif re.search(r"\b(?:zip|compress)", c):
        intent.operation = "zip"
    elif re.search(r"\bconvert\b", c):
        intent.operation = "convert"
        to = re.search(r"\bto\s+\.?([a-z]{3,4})\b", c)
        intent.convert_to = to.group(1) if to else "png"
    elif re.search(r"\b(bulk rename|rename all)\b", c):
        intent.operation = "rename"
        pat = re.search(r"['\"\u201c]([^'\"\u201d]+)['\"\u201d]\s*(?:to|->|\u2192)\s*['\"\u201c]([^'\"\u201d]*)['\"\u201d]", command)
        if pat:
            intent.rename_from, intent.rename_to = pat.group(1), pat.group(2)
    elif re.search(r"\b(move|put|relocate|transfer|gather|collect|shift)\b", c):
        intent.operation = "move"
        intent.move_type, intent.destination = parse_move(command)
    elif re.search(r"\b(organi[sz]e|tidy|clean ?up|declutter|sort)\b", c):
        intent.operation = "organize"
        intent.organize_by = "year" if "year" in c else "type"
        if re.search(r"\bpdfs?\b", c):
            # A request naming PDFs is deliberately narrow: not a whole-folder organization.
            names = re.findall(r"\b(?:folder|subfolder)\s+(?:named|called)\s+['\"]?([a-z0-9_-]+)", command, re.IGNORECASE)
            intent.operation = "move"
            intent.move_type = ("ext", ".pdf")
            intent.destination = names[-1] if names else "PDFs"
    return intent


# ── the LLM reader (validated against the user's own words) ──────────────────

SYSTEM_PROMPT = """You read a user's request about files on their computer and extract its details.
Return ONLY a JSON object, no prose, with these keys (use null when the request does not say):
{
  "operation": "organize | move | find | rename | zip | convert | undo | null",
  "folder_text": "the EXACT words or path the user used to name the folder to work in (e.g. Downloads, or C:\\\\Users\\\\me\\\\Docs), copied from the request - never invent or guess a path",
  "organize_by": "type | year | null",
  "file_types": ["the kinds of files meant, in the user's words, e.g. pdfs, photos, slide decks"],
  "destination_folder": "name of the sub-folder to move files into, if any",
  "find_pattern": "a filename pattern like *.pdf, if searching",
  "rename_from": "text to replace, if renaming", "rename_to": "replacement text, if renaming",
  "convert_to": "target image format like png or jpg, if converting"
}
organize = sort every file in a folder into sub-folders. move = move only some kinds of files into a named sub-folder.
undo = revert what was just done. If the user names a full path, folder_text is that path exactly."""


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else text
    start, end = candidate.find("{"), candidate.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(candidate[start:end + 1])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) and value.strip().lower() not in ("", "null", "none") else ""


def _folder_from_llm(command: str, folder_text: str) -> str:
    """Accept the model's folder only if the user really said it (or it is a well-known name)."""
    text = folder_text.strip().strip("\"'\u201c\u201d")
    if not text:
        return ""
    if re.fullmatch(r"(?:(?:my|the)\s+)*[a-z]+(?:\s+(?:folder|directory))?", text, re.IGNORECASE):
        low = re.sub(r"^(?:(?:my|the)\s+)+|\s+(?:folder|directory)$", "", text.lower())
        return low if low in KNOWN_FOLDER_WORDS else ""
    normalized = lambda t: t.replace("/", "\\").lower().rstrip("\\")
    return text if normalized(text) in normalized(command) else ""


def validate_llm(command: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only the fields that pass validation against the request; drop the rest."""
    out: Dict[str, Any] = {}
    op = _clean(data.get("operation")).lower()
    if op in ALLOWED_OPERATIONS:
        out["operation"] = op
    folder = _folder_from_llm(command, _clean(data.get("folder_text")))
    if folder:
        out["folder"] = folder
    if _clean(data.get("organize_by")).lower() in ("type", "year"):
        out["organize_by"] = _clean(data.get("organize_by")).lower()
    types = data.get("file_types")
    for word in (types if isinstance(types, list) else [types]):
        spec = type_spec_for(_clean(word)) if word else None
        if spec:
            out["move_type"] = spec
            break
    dest = _clean(data.get("destination_folder"))
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _-]{0,39}", dest) and dest.lower() not in KNOWN_FOLDER_WORDS:
        out["destination"] = dest
    pattern = _clean(data.get("find_pattern"))
    if re.fullmatch(r"[\w*.?-]{1,40}", pattern):
        out["find_pattern"] = pattern
    if _clean(data.get("rename_from")):
        out["rename_from"] = _clean(data.get("rename_from"))[:80]
        out["rename_to"] = (data.get("rename_to") or "")[:80] if isinstance(data.get("rename_to"), str) else ""
    if re.fullmatch(r"[a-z]{3,4}", _clean(data.get("convert_to")).lower().lstrip(".")):
        out["convert_to"] = _clean(data.get("convert_to")).lower().lstrip(".")
    return out


def merge(base: FileIntent, llm: Dict[str, Any]) -> FileIntent:
    """Rules first; the model fills gaps and disambiguates, but never overrides certain facts."""
    if not llm:
        return base
    merged = FileIntent(**base.__dict__)
    merged.source = "llm+rules"
    if base.operation not in KEYWORD_OPERATIONS and llm.get("operation"):
        merged.operation = llm["operation"]
    if not base.folder_is_path and llm.get("folder"):        # a path the user typed always wins
        merged.folder = llm["folder"]
        merged.folder_is_path = bool(re.search(r"[\\/]", llm["folder"]))
    if merged.operation == "organize":
        merged.organize_by = llm.get("organize_by") or base.organize_by
    if merged.operation == "move":
        merged.move_type = llm.get("move_type") or base.move_type
        merged.destination = llm.get("destination") or base.destination
    if merged.operation == "find" and llm.get("find_pattern") and base.find_pattern == "*":
        merged.find_pattern = llm["find_pattern"]
    if merged.operation == "rename" and not base.rename_from:
        merged.rename_from, merged.rename_to = llm.get("rename_from", ""), llm.get("rename_to", "")
    if merged.operation == "convert" and llm.get("convert_to"):
        merged.convert_to = llm["convert_to"]
    return merged


async def understand(command: str, llm: Any = None, timeout: Optional[float] = None) -> FileIntent:
    """Rules + (optionally) the model. Never raises; a missing or failing model means rules only."""
    base = parse_rules(command)
    if llm is None:
        return base
    timeout = timeout or float(os.environ.get("NLP_PARSE_TIMEOUT_SECONDS", "25"))
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        response = await asyncio.wait_for(
            llm.ainvoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=command)]), timeout=timeout)
        data = _extract_json(getattr(response, "content", "") or "")
    except Exception:
        return base
    return merge(base, validate_llm(command, data)) if data else base
