"""News briefings from Google News RSS: fresh items only, real article links, no duplicates.

Live check 2026-10-27: "tech roundup" from the old feed list returned "Top 10 AI Tools in 2022" style
SEO pages, every link the feed's own URL, the same items repeated under every section. Google News
RSS (already used by tools.web_search) returns dated, current articles with their sources.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from tools.web_search import SearchHit, news_search

BRIEFINGS: Dict[str, Tuple[Tuple[str, str], ...]] = {
    "tech": (("AI", "artificial intelligence"), ("Gadgets & Phones", "smartphone launch OR gadgets"),
             ("Security", "cybersecurity breach OR vulnerability"), ("Startups & Funding", "tech startup funding"),
             ("Software & Platforms", "software update OR Microsoft OR Google OR Apple")),
    "daily": (("India", "India top news"), ("World", "world news"), ("Business & Markets", "Sensex OR Nifty OR economy"),
              ("Technology", "technology"), ("Sports", "cricket OR football")),
    "world": (("World", "world news"), ("Asia", "Asia news"), ("Europe", "Europe news"), ("Americas", "US news")),
}


def _when(hit: SearchHit) -> Optional[datetime]:
    try:
        d = parsedate_to_datetime(hit.date)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, IndexError):
        return None


def _key(title: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", title.lower())[:70]


def build(kind: str = "daily", topic: str = "", per_section: int = 5, max_age_days: int = 2,
          fetch: Callable[[str, int], List[SearchHit]] = news_search, now: Optional[datetime] = None) -> Dict:
    """A briefing: {"status", "sections": [(name, [hits])], "message"}. `topic` makes a one-section search."""
    now = now or datetime.now(timezone.utc)
    plan: Sequence[Tuple[str, str]] = ((topic.title(), topic),) if topic else BRIEFINGS.get(kind, BRIEFINGS["daily"])
    seen, sections, failures = set(), [], 0
    for name, query in plan:
        try:
            hits = fetch(f"{query} when:{max_age_days}d", 25)
        except Exception:
            failures += 1
            continue
        fresh = []
        for h in sorted(hits, key=lambda x: _when(x) or datetime.min.replace(tzinfo=timezone.utc), reverse=True):
            when = _when(h)
            if not h.url or (when and now - when > timedelta(days=max_age_days + 1)) or _key(h.title) in seen:
                continue
            seen.add(_key(h.title))
            fresh.append(h)
            if len(fresh) >= per_section:
                break
        if fresh:
            sections.append((name, fresh))
    if not sections:
        return {"status": "error", "sections": [],
                "message": "I couldn't fetch any current news just now (no connection or the news source failed)."}
    title = {"tech": "Technology roundup", "world": "World briefing"}.get(kind, "Daily briefing")
    if topic:
        title = f"News: {topic}"
    lines = [f"# {title} — {now:%A, %d %B %Y}", ""]
    for name, hits in sections:
        lines.append(f"## {name}")
        for h in hits:
            when = _when(h)
            meta = " · ".join(x for x in (h.source, f"{when:%d %b, %H:%M}" if when else "") if x)
            lines.append(f"- **{h.title}**" + (f" — {meta}" if meta else ""))
            lines.append(f"  {h.url}")
        lines.append("")
    total = sum(len(h) for _n, h in sections)
    lines.append(f"_{total} stories from the last {max_age_days} days, via Google News"
                 + (f"; {failures} section(s) could not be fetched" if failures else "") + "._")
    return {"status": "success", "sections": sections, "count": total, "message": "\n".join(lines)}
