"""Understand a document request before writing anything (deterministic, instant).

"write a leave letter to my manager for tomorrow" and "make a 10 slide animated deck on EV
batteries for investors" need different things: a letter has a recipient, a date and one page;
a deck has an audience, a slide count and a visual theme. Getting this right first is what keeps
a small local model from producing a generic template.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

KINDS = ("docx", "pptx", "xlsx", "pdf")

# genre → words that signal it. Order matters: the first match wins.
GENRES = [
    ("letter", r"\b(letter|leave application|application for leave|cover letter|resignation|"
               r"complaint|recommendation letter|noc|request letter|apology letter|invitation letter|"
               r"sick leave|leave request|permission letter)\b"),
    ("resume", r"\b(resume|résumé|cv|curriculum vitae|biodata)\b"),
    ("minutes", r"\b(minutes of (the )?meeting|meeting minutes|mom\b)"),
    ("proposal", r"\b(proposal|pitch|business plan|project plan|statement of work|sow)\b"),
    ("guide", r"\b(guide|manual|tutorial|how[- ]to|handbook|instructions|sop|standard operating)\b"),
    ("essay", r"\b(essay|article|blog( post)?|story|speech)\b"),
    ("notes", r"\b(notes|summary|cheat ?sheet|study material)\b"),
    ("report", r"\b(report|analysis|research|study|whitepaper|white paper|case study|review)\b"),
]

AUDIENCES = r"\b(?:for|to)\s+(?:my\s+|the\s+|our\s+)?(investors?|students?|kids|children|beginners|executives?|management|clients?|customers?|team|board|manager|professor|teacher|hr|engineers?|developers?|doctors?|employees|stakeholders)\b"
_TONES = {"formal": "formal", "professional": "formal", "casual": "friendly", "friendly": "friendly",
          "fun": "friendly", "academic": "academic", "technical": "technical", "persuasive": "persuasive",
          "simple": "plain", "easy": "plain"}
_THEME_WORDS = r"\b(gaming|neon|cyberpunk|gradient|floral|vibrant|bright|colou?rful|pastel|elegant|luxury|premium|royal|ocean|sunset|dark|minimal|technology|tech|business|corporate|nature|health|medical|creative|education|finance|light)\b"


@dataclass
class DocSpec:
    kind: str                         # docx | pptx | xlsx | pdf
    request: str
    topic: str
    genre: str = "report"
    audience: str = ""
    tone: str = "formal"
    pages: int = 0                    # requested length (0 = default for the genre)
    slides: int = 0
    theme: str = ""
    animated: bool = False
    research: bool = False
    recipient: str = ""
    sender: str = ""
    file_name: str = ""
    extras: Dict[str, Any] = field(default_factory=dict)

    @property
    def target_sections(self) -> int:
        if self.genre == "letter":
            return 1
        if self.pages:
            return max(4, min(14, self.pages * 2))
        return {"resume": 6, "minutes": 5, "notes": 6, "essay": 6, "guide": 7, "proposal": 8}.get(self.genre, 7)

    @property
    def words_per_section(self) -> int:
        if self.pages:
            return max(120, min(450, self.pages * 450 // max(self.target_sections, 1)))
        return {"notes": 120, "resume": 90, "minutes": 110}.get(self.genre, 220)

    def brief(self) -> str:
        bits = [f"Document type: {self.genre} ({self.kind})", f"Topic: {self.topic}"]
        if self.audience:
            bits.append(f"Audience: {self.audience}")
        bits.append(f"Tone: {self.tone}")
        if self.recipient:
            bits.append(f"Recipient: {self.recipient}")
        if self.sender:
            bits.append(f"Written by: {self.sender}")
        bits.append(f"Today's date: {date.today():%B %d, %Y}")
        bits.append(f"Original request: {self.request}")
        return "\n".join(bits)


def owner_name() -> str:
    try:
        from tools.project_paths import project_path
        with open(project_path("tom_brain", "user_profile.json"), encoding="utf-8") as fh:
            return str(json.load(fh).get("name") or "").strip()
    except (OSError, ValueError):
        return ""


def _clean_topic(text: str) -> str:
    t = re.sub(r"\b(please|can you|could you|tom|hey|hi|for me|now|kindly)\b", " ", text, flags=re.I)
    t = re.sub(r"\b(create|make|generate|write|prepare|build|draft|design|produce|give me)\b", " ", t, flags=re.I)
    t = re.sub(r"\b(an?|the)\s+(professional|detailed|animated|beautiful|good|nice|proper|short|long|"
               r"comprehensive|complete|simple)\b", " ", t, flags=re.I)
    t = re.sub(r"\b(professional|detailed|animated|beautiful|comprehensive)\b", " ", t, flags=re.I)
    t = re.sub(r"\b(word|docx|ms word|pdf|power ?point|pptx?|excel|xlsx|spreadsheet|workbook|"
               r"presentation|deck|slides?|document|doc|file|report)\b", " ", t, flags=re.I)
    t = re.sub(r"\b\d+\s*(slides?|pages?|sheets?)\b", " ", t, flags=re.I)
    t = re.sub(_THEME_WORDS + r"\s+(theme|style)", " ", t, flags=re.I)
    t = re.sub(r"\b(with|in|using)\s+(a\s+)?(theme|style|animations?)\b", " ", t, flags=re.I)
    t = re.sub(r"^\W*(on|about|for|regarding|of|an?|the)\s+", "", re.sub(r"\s+", " ", t).strip(), flags=re.I)
    t = re.sub(r"\s+(on|about|for|with|in|and)$", "", t, flags=re.I)
    return t.strip(" .,:;-\"'") or "General topic"


def understand(kind: str, request: str, parsed: Optional[Dict[str, Any]] = None) -> DocSpec:
    parsed = parsed or {}
    low = request.lower()
    genre = next((g for g, rx in GENRES if re.search(rx, low)), "report")
    if kind == "pptx":
        genre = "presentation"
    elif kind == "xlsx":
        genre = "workbook"
    subject = str(parsed.get("subject") or "").strip()
    topic = subject if subject and subject.lower() not in ("document", "report", "presentation", "data") \
        else _clean_topic(request)
    m = re.search(r"\b(?:about|on|regarding|for)\s+(.+?)(?:\s+(?:for|to)\s+(?:my|the|our)\b|\s+with\s+\d|\s+in\s+\w+\s+theme|$)", request, re.I)
    if (not subject) and m and genre not in ("letter",):
        topic = _clean_topic(m.group(1)) or topic
    aud = re.search(AUDIENCES, low)
    tone = next((v for k, v in _TONES.items() if re.search(rf"\b{k}\b", low)), "formal")
    pages = re.search(r"\b(\d{1,2})\s*(?:-|to)?\s*pages?\b", low)
    slides = re.search(r"\b(\d{1,2})\s*(?:-|to)?\s*slides?\b", low)
    theme = re.search(_THEME_WORDS, low)
    recipient = ""
    if genre == "letter":
        r = re.search(r"\bto\s+(?:my\s+|the\s+|our\s+)?([a-z][\w .'-]{1,40}?)(?=\s+(?:for|about|regarding|asking|requesting|saying|as|on|because|that)\b|[,.]|$)", request, re.I)
        recipient = r.group(1).strip() if r else ""
    spec = DocSpec(
        kind=kind, request=request.strip(), topic=topic[:120], genre=genre,
        audience=aud.group(1) if aud else "", tone=tone,
        pages=int(pages.group(1)) if pages else 0,
        slides=min(30, max(3, int(slides.group(1)))) if slides else (10 if kind == "pptx" else 0),
        theme=theme.group(1) if theme else "",
        animated=kind == "pptx",                    # decks are animated unless asked not to be
        research=genre in ("report", "proposal", "essay", "presentation") or bool(parsed.get("requires_data_from_internet")) or bool(
            re.search(r"\b(latest|current|recent|today'?s|this year|202\d|research|statistics|market size|trends?)\b", low)),
        recipient=recipient or str(parsed.get("person_name") or ""),
        sender=owner_name(),
        file_name=str(parsed.get("file_name") or ""),
    )
    if re.search(r"\b(no|without)\s+animations?\b|\bstatic\b", low):
        spec.animated = False
    return spec


def file_name_for(spec: DocSpec, title: str = "") -> str:
    """A short, readable file name: the user's name for it, else the generated title, else the topic."""
    if spec.file_name:
        base = spec.file_name.rsplit(".", 1)[0]
    else:
        source = title if title and (len(spec.topic) > 40 or spec.genre == "letter") else spec.topic
        words = re.sub(r"[^\w\s-]", "", source).strip().lower().split()
        base = " ".join(w for w in words if w not in ("a", "an", "the", "of", "for", "to", "and", "my"))[:50]
        base = re.sub(r"\s+", "_", base)[:60] or spec.genre
        if spec.genre in ("letter", "resume", "minutes", "proposal"):
            base = f"{base}_{spec.genre}" if spec.genre not in base else base
    return f"{base}.{spec.kind}"


def outline_hint(spec: DocSpec) -> List[str]:
    """A sensible section skeleton per genre — used to steer the model and as a fallback outline."""
    return {
        "report": ["Executive Summary", "Introduction and Background", "Current Landscape", "Key Findings",
                   "Analysis and Discussion", "Challenges and Risks", "Recommendations", "Conclusion"],
        "proposal": ["Executive Summary", "Problem Statement", "Proposed Solution", "Scope and Deliverables",
                     "Implementation Plan and Timeline", "Budget and Resources", "Risks and Mitigation",
                     "Expected Outcomes"],
        "guide": ["Overview", "Before You Begin", "Step-by-Step Instructions", "Best Practices",
                  "Common Mistakes to Avoid", "Troubleshooting", "Summary"],
        "essay": ["Introduction", "Background", "Main Argument", "Supporting Evidence",
                  "Counterpoints", "Conclusion"],
        "notes": ["Key Concepts", "Important Definitions", "Core Ideas Explained", "Examples",
                  "Quick Revision Points", "Summary"],
        "minutes": ["Meeting Details", "Attendees", "Agenda", "Discussion Points", "Decisions and Action Items"],
        "resume": ["Professional Summary", "Core Skills", "Professional Experience", "Projects", "Education",
                   "Certifications and Achievements"],
    }.get(spec.genre, ["Overview", "Background", "Key Points", "Details", "Recommendations", "Conclusion"])[
        : max(spec.target_sections, 5)]
