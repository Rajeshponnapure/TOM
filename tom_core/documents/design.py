"""Design system shared by the Word, PDF, PowerPoint and Excel renderers."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    name: str
    primary: str        # titles, heading text, header bars
    secondary: str      # sub-headings, second chart series
    accent: str         # highlights, rules, numbers
    dark: str           # dark backgrounds (title slide)
    light: str          # light panels / zebra rows
    text: str = "1F2937"
    muted: str = "6B7280"
    heading_font: str = "Segoe UI Semibold"
    body_font: str = "Segoe UI"


PALETTES = {
    "corporate": Palette("corporate", "1F3A5F", "2E6DA4", "F2A541", "0F1E33", "EEF3F8"),
    "technology": Palette("technology", "0B3D91", "1E88E5", "00C2A8", "0A1929", "E8F1FB"),
    "finance": Palette("finance", "14532D", "15803D", "CA8A04", "0B2A18", "ECF7EF"),
    "health": Palette("health", "0E6E6E", "14A3A3", "F97316", "083B3B", "E7F6F6"),
    "education": Palette("education", "4C1D95", "7C3AED", "F59E0B", "24104A", "F3EEFC"),
    "creative": Palette("creative", "9D174D", "DB2777", "FBBF24", "4A0B26", "FCEEF5"),
    "nature": Palette("nature", "3F6212", "65A30D", "EAB308", "1F3108", "F1F8E6"),
    "dark": Palette("dark", "111827", "374151", "38BDF8", "0B0F19", "F3F4F6"),
    "elegant": Palette("elegant", "3B2F2F", "7C5E3C", "C9A227", "1E1717", "F7F3EE", heading_font="Georgia",
                       body_font="Segoe UI"),
    "gaming": Palette("gaming", "5B21B6", "DB2777", "22D3EE", "0B0420", "F1EBFF"),
    "ocean": Palette("ocean", "075985", "0284C7", "F59E0B", "042F4A", "E6F4FB"),
    "minimal": Palette("minimal", "111827", "4B5563", "2563EB", "111827", "F5F5F5"),
}
ALIASES = {"tech": "technology", "business": "corporate", "professional": "corporate", "medical": "health",
           "neon": "gaming", "cyberpunk": "gaming", "luxury": "elegant", "premium": "elegant", "royal": "elegant",
           "vibrant": "creative", "bright": "creative", "colorful": "creative", "colourful": "creative",
           "pastel": "creative", "floral": "nature", "sunset": "creative", "gradient": "technology",
           "light": "minimal"}
_TOPIC_HINTS = [
    ("technology", r"\b(ai|software|cloud|data|cyber|robot|tech|digital|computer|app|machine learning|iot|5g|blockchain|ev|battery|semiconductor)\b"),
    ("finance", r"\b(finance|budget|invest|stock|bank|revenue|sales|profit|tax|accounting|economy|market)\b"),
    ("health", r"\b(health|medical|hospital|disease|nutrition|fitness|mental|covid|wellness|doctor)\b"),
    ("education", r"\b(school|student|education|learning|course|university|exam|teaching|syllabus)\b"),
    ("nature", r"\b(climate|environment|sustainab|green|energy|solar|forest|agricultur|water|ocean)\b"),
    ("creative", r"\b(design|art|marketing|brand|fashion|music|film|social media|creative)\b"),
]


def palette_for(theme: str = "", topic: str = "") -> Palette:
    t = (theme or "").lower().strip()
    t = ALIASES.get(t, t)
    if t in PALETTES:
        return PALETTES[t]
    low = (topic or "").lower()
    for name, rx in _TOPIC_HINTS:
        if re.search(rx, low):
            return PALETTES[name]
    return PALETTES["corporate"]


def rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def split_bold(text: str):
    """'a **b** c' → [('a ', False), ('b', True), (' c', False)]. Inline `code` keeps its text without the
    backticks (renderers that support it use split_inline)."""
    return [(t, b) for t, b, _ in split_inline(text)]


def split_inline(text: str):
    """→ [(text, bold, code)] for **bold** and `code` spans."""
    out = []
    for p in re.split(r"(\*\*[^*]+\*\*|`[^`\n]+`)", text or ""):
        if not p:
            continue
        if p.startswith("**") and p.endswith("**") and len(p) > 4:
            out.append((p[2:-2].replace("`", ""), True, False))
        elif p.startswith("`") and p.endswith("`") and len(p) > 2:
            out.append((p[1:-1], False, True))
        else:
            out.append((p, False, False))
    return out
