"""Live web search without an API key: Google News RSS + Wikipedia.

Owner report 2026-10-21: the Web Search quick action answered "No instant answer found." — it only
asked DuckDuckGo's Instant Answer API, which returns encyclopedia abstracts, not search results.
Measured the same day from this machine:
  * googlesearch-python 1.3.0            → 0 results (Google blocks automated queries)
  * DuckDuckGo html / lite endpoints      → HTTP 202 bot challenge, no results
  * Bing HTML                             → unrelated results (Pinterest pages) for a news query
  * Google News RSS                       → 51–100 current, relevant items (works for most topics)
  * Wikipedia search + REST summary       → reliable for "what is / how does" questions
So TOM searches those two and answers only from what they return, with the sources listed.
"""
from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"}
_EXPLAIN = re.compile(r"^\s*(?:what|who|how|why|explain|define|meaning of|history of)\b", re.IGNORECASE)


@dataclass(frozen=True)
class SearchHit:
    title: str
    url: str
    snippet: str = ""
    source: str = ""
    date: str = ""
    kind: str = "news"          # news | wiki


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text or "")).strip()


def news_search(query: str, limit: int = 8, timeout: float = 10.0) -> List[SearchHit]:
    import requests
    from bs4 import BeautifulSoup
    r = requests.get("https://news.google.com/rss/search", timeout=timeout, headers=_HEADERS,
                     params={"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"})
    r.raise_for_status()
    hits = []
    for item in BeautifulSoup(r.text, "xml").find_all("item")[:limit]:
        title = _clean(item.title.get_text() if item.title else "")
        source = _clean(item.source.get_text()) if item.source else ""
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3]
        desc = item.description.get_text() if item.description else ""
        snippet = _clean(BeautifulSoup(desc, "html.parser").get_text(" ", strip=True)) if desc else ""
        hits.append(SearchHit(title=title, url=_clean(item.link.get_text() if item.link else ""),
                              snippet=snippet if snippet != title else "", source=source,
                              date=_clean(item.pubDate.get_text()) if item.pubDate else "", kind="news"))
    return hits


def wiki_search(query: str, limit: int = 2, timeout: float = 10.0) -> List[SearchHit]:
    import requests
    found = requests.get("https://en.wikipedia.org/w/api.php", timeout=timeout, headers=_HEADERS,
                         params={"action": "query", "list": "search", "srsearch": query, "format": "json",
                                 "srlimit": limit}).json()
    hits = []
    for entry in found.get("query", {}).get("search", [])[:limit]:
        title = entry.get("title", "")
        summary = requests.get("https://en.wikipedia.org/api/rest_v1/page/summary/" + title.replace(" ", "_"),
                               timeout=timeout, headers=_HEADERS).json()
        hits.append(SearchHit(title=title, kind="wiki", source="Wikipedia",
                              url=summary.get("content_urls", {}).get("desktop", {}).get("page", ""),
                              snippet=_clean(summary.get("extract", ""))[:900]))
    return hits


def search(query: str, limit: int = 8) -> List[SearchHit]:
    """News first (or Wikipedia first for "what/how/why" questions); a failing source is skipped."""
    order = (wiki_search, news_search) if _EXPLAIN.match(query or "") else (news_search, wiki_search)
    hits: List[SearchHit] = []
    for source in order:
        try:
            hits.extend(source(query))
        except Exception as exc:          # offline, blocked, changed format: try the next source
            logger.info("web search source %s failed: %s", source.__name__, exc)
    return hits[:limit]


def sources_text(hits: List[SearchHit]) -> str:
    lines = []
    for i, h in enumerate(hits, 1):
        meta = " · ".join(x for x in (h.source, h.date[:16]) if x)
        lines.append(f"[{i}] {h.title}" + (f" — {meta}" if meta else "") + (f"\n    {h.url}" if h.url else ""))
    return "\n".join(lines)


def context_text(hits: List[SearchHit]) -> str:
    """The results as numbered context for the model (title, source, date, snippet)."""
    return "\n".join(f"[{i}] {h.title} ({h.source}{', ' + h.date[:16] if h.date else ''})"
                     + (f": {h.snippet}" if h.snippet else "") for i, h in enumerate(hits, 1))
