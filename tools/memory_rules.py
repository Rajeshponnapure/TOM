"""
Turning memories into behaviour.

  * is_preference_statement / is_pure_preference — spot corrections and rules
    the user states ("always put PDFs in Invoices", "no, keep emails short").
  * categorize — a stable task tag so memories are filed and recalled per kind
    of work (file organization, email, documents, …).
  * FolderRule + parse_folder_rules / rules_from_structured — convert recalled
    facts (free text from Hindsight) into concrete file-organizing rules that
    tools/file_ops.py applies deterministically.

Pure stdlib, no I/O — fully unit-testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ── Preferences / corrections ────────────────────────────────────────────
_PREF_START = re.compile(
    r"^\s*(?:(?:ok(?:ay)?|no|nope|actually|also|and|hey tom|tom|wait|hmm)\s*[,.!:;\u2014\u2013-]*\s+)*"
    r"(?:always|never|from now on|going forward|in (?:the )?future|next time|remember(?: that|:)?\s"
    r"|please remember|note that|i (?:always |really |generally |usually )?(?:prefer|hate|dislike|don'?t (?:like|want)"
    r"|like (?:my|it|them|when|to keep|to have|things|emails|files)|want (?:my|all|every|you to always|you to never))\b"
    r"|don'?t (?:ever|you ever)|do not ever|stop (?:doing|putting|moving|adding|using|sending)"
    r"|my (?:preference|rule)|keep (?:my |the |all |your )?\w+ (?:short|brief|formal|casual|professional|concise|simple)"
    r"|(?:use|sign (?:off|emails?)(?: with| as)?)\b.{0,40}\b(?:always|every time|by default)"
    r"|(?:you should|make sure (?:to|you))\s)",
    re.IGNORECASE,
)
_PREF_ANYWHERE = re.compile(
    r"\b(?:from now on|from here on|going forward|in (?:the )?future|next time|every time"
    r"|don'?t ever|remember (?:that|this))\b",
    re.IGNORECASE,
)
_CORRECTION_START = re.compile(
    r"^\s*(?:no[,.!]?\s|nope|wrong|that'?s (?:wrong|not right|not what)|not like that"
    r"|actually[,.]?\s|instead[,.]?\s|i meant\b|you should have)",
    re.IGNORECASE,
)


_LEAD = re.compile(r"^\s*(?:(?:ok(?:ay)?|no|nope|actually|also|and|hey tom|tom|wait|hmm|wrong)\s*[,.!:;\u2014\u2013-]*\s+)*",
                   re.IGNORECASE)
# A rule stated mid-sentence: "PDFs always go in Invoices", "screenshots belong in Screenshots".
_RULE_WORDS = re.compile(
    r"\b(?:always|never|should(?:n'?t| not)?|must(?:n'?t| not)?|belongs?|go(?:es)? (?:in|into|to|under)"
    r"|prefer|instead of|rather than|by default)\b", re.IGNORECASE)
_TASK_START = re.compile(
    r"^(?:please\s+|can you\s+|could you\s+)?(?:organi[sz]e|tidy|clean|sort|create|write|make|draft|send|e-?mail"
    r"|open|build|search|find|run|generate|analy[sz]e|schedule|summari[sz]e|read|show|launch|start|move|copy"
    r"|delete|rename|zip|convert|check|book|plan|fix|debug)\b", re.IGNORECASE)
_DO_IT_NOW = re.compile(r"\b(?:now|right now|then|and then)\b\s*[.!]?\s*$|\b(?:do it|go ahead|run it|redo it)\b",
                        re.IGNORECASE)


def is_correction(text: str) -> bool:
    return bool(_CORRECTION_START.search(text or ""))


def _stated_rule(text: str) -> bool:
    """A declarative rule with no task verb up front ("PDFs always go in Invoices")."""
    body = _LEAD.sub("", text or "", count=1).strip()
    if re.match(r"^(?:what|how|why|when|where|who|which|is|are|do|does|did|can|could|should|would|will|shall)\b",
                body, re.IGNORECASE):
        # Questions are not rules — except "can you always / never …" requests.
        return bool(re.match(r"^(?:can|could|would|will) you (?:please )?(?:always|never)\b", body, re.IGNORECASE))
    return bool(body and _RULE_WORDS.search(body) and not _TASK_START.search(body))


def is_preference_statement(text: str) -> bool:
    """True when the message states a rule/preference/correction worth keeping."""
    t = text or ""
    return bool(_PREF_START.search(t) or _PREF_ANYWHERE.search(t) or is_correction(t) or _stated_rule(t))


def is_pure_preference(text: str) -> bool:
    """True when the message *only* teaches TOM something (no task to run now)."""
    t = (text or "").strip()
    if not t or _DO_IT_NOW.search(t):
        return False
    return bool(_PREF_START.search(t) or _stated_rule(t))


# ── Task categories ──────────────────────────────────────────────────────
_CATEGORIES: List[Tuple[str, Tuple[str, ...]]] = [
    ("file_organization", ("organize", "organise", "tidy", "clean up", "cleanup", "sort my",
                           "sort the", "downloads", "folder", "declutter", "rename", "move files",
                           "pdfs", "screenshots", "installers")),
    ("email", ("email", "e-mail", "mail ", "inbox", "sign off", "sign-off", "signature",
               "subject line", "reply to")),
    ("presentations", ("presentation", "slides", "slide deck", "ppt", "powerpoint")),
    ("spreadsheets", ("excel", "spreadsheet", "xlsx", "budget", "tracker")),
    ("documents", ("word doc", "document", "report", "letter", "pdf report", "resume")),
    ("messaging", ("whatsapp", "message ", "text ")),
    ("web", ("search", "research", "website", "browse", "scrape")),
    ("code", ("code", "script", "python", "debug", "function", "bug")),
    ("scheduling", ("schedule", "remind", "every day", "every week", "daily")),
]


def categorize(text: str) -> str:
    t = f" {(text or '').lower()} "
    for name, keys in _CATEGORIES:
        if any(k in t for k in keys):
            return name
    return "general"


# ── Folder rules ─────────────────────────────────────────────────────────
# Group names match tools/file_ops.TYPE_GROUPS.
_TYPE_WORDS: List[Tuple[str, Tuple[str, str]]] = [
    (r"screen\s?shots?|screen captures?", ("name", "screenshot")),
    (r"invoices?|receipts?|bills?", ("name", "invoice")),
    (r"pdfs?|\.pdf\b|pdf files?", ("ext", ".pdf")),
    (r"installers?|setup files?|\.exe\b|\.msi\b|executables?", ("group", "Installers")),
    (r"images?|photos?|pictures?|pics|\.png\b|\.jpe?g\b", ("group", "Images")),
    (r"videos?|movies?|clips?|\.mp4\b", ("group", "Video")),
    (r"music|songs?|audio|mp3s?|\.mp3\b", ("group", "Audio")),
    (r"zips?|archives?|\.zip\b|compressed files?", ("group", "Archives")),
    (r"spreadsheets?|excel files?|csvs?|\.xlsx\b|\.csv\b", ("group", "Spreadsheets")),
    (r"presentations?|slides|slide decks?|\.pptx?\b", ("group", "Presentations")),
    (r"code files?|scripts?|source files?|notebooks?", ("group", "Code")),
    (r"word (?:docs?|documents?)|\.docx?\b", ("ext", ".docx")),
    (r"text files?|\.txt\b|notes", ("ext", ".txt")),
]
_EXPLICIT_EXT = re.compile(r"(?<![\w/\\])\.([a-z0-9]{2,5})\b", re.IGNORECASE)
# Preposition (+ determiners, "folder called") is case-insensitive; the folder
# name itself is case-sensitive so "Work Docs" stays two words but "Invoices
# folder" stops at "Invoices".
_DEST = re.compile(
    r"(?i:\b(?:into|in|to|under|inside|within)\s+"
    r"(?:(?:the|a|an|my|their|his|her|its|separate|new|dedicated)\s+)*"
    r"(?:(?:folder|directory|subfolder)\s+)?(?:(?:called|named|titled)\s+)?)"
    r"(\"[^\"]{1,40}\"|'[^']{1,40}'|`[^`]{1,40}`|[A-Za-z0-9][\w\-/]*(?:\s+[A-Z0-9][\w\-/]*){0,2})"
)
_SKIP = re.compile(
    r"\b(?:never|don'?t|do not|not to|should not|shouldn'?t|must not|stop)\b[^.;]{0,40}?"
    r"\b(?:move|moving|moved|touch|touching|touched|organi[sz]e|sort|sorting|sorted|relocate)\b"
    r"|\b(?:leave|keep|left|kept|remain|stay)\b[^.;]{0,40}?\b(?:alone|where (?:they|it) (?:are|is)|in place"
    r"|untouched|as (?:they|it) (?:are|is)|unsorted|unmoved)\b",
    re.IGNORECASE,
)
_NOT_A_FOLDER = {
    "downloads", "download", "place", "folders", "folder", "them", "it", "there", "one",
    "subfolders", "future", "order", "general", "mind", "be", "go", "always", "never", "keep",
    "put", "move", "sort", "sorted", "organize", "organise", "which", "where", "their", "my",
    "this", "that", "these", "those", "any", "each", "every", "its", "front", "addition",
    "case", "time", "the", "a", "an", "pdf", "files", "file", "make", "do", "have", "get",
}


@dataclass
class FolderRule:
    kind: str            # "ext" | "group" | "name"
    value: str           # ".pdf" | "Images" | "screenshot"
    action: str = "move"  # "move" | "skip"
    dest: str = ""       # subfolder name for "move"
    source: str = ""     # the memory text this came from (shown to the user)

    def matches(self, filename: str, group: str) -> bool:
        name = filename.lower()
        if self.kind == "ext":
            return name.endswith(self.value.lower())
        if self.kind == "group":
            return group.lower() == self.value.lower()
        if self.kind == "name":
            return self.value.lower() in name
        return False

    def describe(self) -> str:
        what = {"ext": f"{self.value} files", "group": self.value.lower(),
                "name": f"files named '*{self.value}*'"}.get(self.kind, self.value)
        return f"leave {what} where they are" if self.action == "skip" else f"{what} → {self.dest}/"

    def key(self) -> Tuple[str, str]:
        return (self.kind, self.value.lower())

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind, "value": self.value, "action": self.action,
                "dest": self.dest, "source": self.source}


_SPECIFICITY = {"name": 0, "ext": 1, "group": 2}


def _clean_dest(raw: str) -> str:
    d = re.sub(r"\s+", " ", raw or "").strip(" -_\\'\"`.,;:")
    d = d.strip("/")
    words = d.split()
    while words and words[-1].lower() in ("folder", "directory", "subfolder", "files", "please", "only"):
        words.pop()
    d = " ".join(words[:3])
    if not d or len(d) > 40 or d.split()[0].lower() in _NOT_A_FOLDER:
        return ""
    if re.search(r"[<>:|?*]", d) or ".." in d:
        return ""
    return d[0].upper() + d[1:]


def _type_spans(clause: str) -> List[Tuple[int, int, Tuple[str, str]]]:
    spans: List[Tuple[int, int, Tuple[str, str]]] = []
    low = clause.lower()
    for pattern, spec in _TYPE_WORDS:
        for m in re.finditer(rf"(?<![\w.]){pattern}", low):
            spans.append((m.start(), m.end(), spec))
    for m in _EXPLICIT_EXT.finditer(clause):
        if not any(a <= m.start() < b for a, b, _ in spans):
            spans.append((m.start(), m.end(), ("ext", "." + m.group(1).lower())))
    spans.sort()
    return spans


def _types_in(clause: str) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for _a, _b, spec in _type_spans(clause):
        if spec not in out:
            out.append(spec)
    return out


def _dest_spans(clause: str) -> List[Tuple[int, int, str]]:
    out = []
    for m in _DEST.finditer(clause):
        name = _clean_dest(m.group(1))
        if name:
            out.append((m.start(1), m.end(1), name))
    return out


def _split_clauses(text: str) -> List[str]:
    return [c.strip() for c in re.split(
        r"(?<=[.;!?])\s+|\s*\n\s*|\s+[—–-]\s+|,\s*(?:and\s+|but\s+)?(?=(?:never|always|don'?t|do not|leave|keep|put|move|send|not)\b)",
        text or "", flags=re.IGNORECASE) if c and c.strip()]


def parse_folder_rules(texts: Iterable[str]) -> List[FolderRule]:
    """Extract folder-organizing rules from free-text memories.

    Handles both the user's own words ("always put PDFs in Invoices") and the
    third-person facts Hindsight stores ("The user wants PDF files sorted into
    the Invoices folder"). Earlier texts win on conflicts, so pass the most
    relevant / most recent first.
    """
    rules: Dict[Tuple[str, str], FolderRule] = {}
    for text in texts:
        source = (text or "").strip()
        for clause in _split_clauses(text):
            dests = _dest_spans(clause)
            # A type word inside a destination ("into the Invoices folder") names
            # the folder, not the files being moved.
            types = [(a, b, spec) for a, b, spec in _type_spans(clause)
                     if not any(da <= a < db for da, db, _ in dests)]
            if not types:
                continue
            specs: List[Tuple[str, str]] = []
            for _a, _b, spec in types:
                if spec not in specs:
                    specs.append(spec)
            # "invoice PDFs" → the specific name rule, not every PDF
            if ("name", "invoice") in specs and ("ext", ".pdf") in specs:
                specs.remove(("ext", ".pdf"))
                types = [t for t in types if t[2] != ("ext", ".pdf")]

            if _SKIP.search(clause) and not dests:
                for kind, value in specs:
                    rules.setdefault((kind, value.lower()), FolderRule(kind, value, "skip", "", source))
                continue
            for a, b, (kind, value) in types:
                if (kind, value) not in specs:
                    continue
                after = [d for d in dests if d[0] >= b]
                if not after:
                    continue
                rules.setdefault((kind, value.lower()),
                                 FolderRule(kind, value, "move", after[0][2], source))
    return sorted(rules.values(), key=lambda r: _SPECIFICITY.get(r.kind, 9))


# JSON schema handed to Hindsight reflect() when free-text parsing finds nothing.
FOLDER_RULES_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "rules": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["ext", "group", "name"],
                             "description": "ext = file extension like .pdf; group = one of Images, "
                                            "Documents, Spreadsheets, Presentations, Audio, Video, "
                                            "Archives, Code, Installers; name = text contained in the filename"},
                    "value": {"type": "string"},
                    "action": {"type": "string", "enum": ["move", "skip"]},
                    "dest": {"type": "string", "description": "destination subfolder name for move"},
                },
                "required": ["kind", "value", "action"],
            },
        }
    },
    "required": ["rules"],
}


def rules_from_structured(obj: Any, source: str = "reflect") -> List[FolderRule]:
    out: Dict[Tuple[str, str], FolderRule] = {}
    items = (obj or {}).get("rules") if isinstance(obj, dict) else None
    for it in items or []:
        if not isinstance(it, dict):
            continue
        kind = str(it.get("kind", "")).lower()
        value = str(it.get("value", "")).strip()
        action = str(it.get("action", "move")).lower()
        dest = _clean_dest(str(it.get("dest", "")))
        if kind not in ("ext", "group", "name") or not value:
            continue
        if kind == "ext" and not value.startswith("."):
            value = "." + value
        if action not in ("move", "skip") or (action == "move" and not dest):
            continue
        out.setdefault((kind, value.lower()), FolderRule(kind, value, action, dest, source))
    return sorted(out.values(), key=lambda r: _SPECIFICITY.get(r.kind, 9))


def merge_rules(*groups: Iterable[FolderRule]) -> List[FolderRule]:
    merged: Dict[Tuple[str, str], FolderRule] = {}
    for group in groups:
        for rule in group:
            merged.setdefault(rule.key(), rule)
    return sorted(merged.values(), key=lambda r: _SPECIFICITY.get(r.kind, 9))


def match_rule(filename: str, group: str, rules: Iterable[FolderRule]) -> Optional[FolderRule]:
    for rule in rules:
        if rule.matches(filename, group):
            return rule
    return None
