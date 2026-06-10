"""
News & Knowledge Agent for TOM.
Self-updating agent that automatically surfs the web daily to stay current
on technology, world events, science, health, and more.

Capabilities:
- Fetch headlines from multiple news sources and RSS feeds
- Extract full article content with newspaper3k / readability
- Search news across APIs and web sources
- Generate daily briefings and topic-specific roundups
- Monitor topics for significant changes over time
- Update knowledge base with daily summaries
- Scrape general web pages with fallback strategies
- Identify trending topics via Google Trends, Reddit, etc.
"""

import asyncio
import hashlib
import json
import logging
import os
import random
import re
import string
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse, quote_plus
from tools.project_paths import project_path_str

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency imports with graceful fallbacks
# ---------------------------------------------------------------------------
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

try:
    from bs4 import BeautifulSoup
    HAS_BEAUTIFULSOUP = True
except ImportError:
    HAS_BEAUTIFULSOUP = False

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

try:
    from newspaper import Article as NewspaperArticle
    HAS_NEWSPAPER = True
except ImportError:
    HAS_NEWSPAPER = False

try:
    from readability import Document as ReadabilityDocument
    HAS_READABILITY = True
except ImportError:
    HAS_READABILITY = False

try:
    from googlesearch import search as google_search
    HAS_GOOGLE_SEARCH = True
except ImportError:
    HAS_GOOGLE_SEARCH = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:127.0) Gecko/20100101 Firefox/127.0",
]

CATEGORIES = {
    "technology": ["tech", "technology", "ai", "cybersecurity", "software", "gadgets"],
    "world": ["world", "international", "global", "foreign"],
    "business": ["business", "finance", "economy", "markets", "stocks"],
    "science": ["science", "space", "nature", "research", "physics", "biology"],
    "health": ["health", "medical", "wellness", "disease", "pharma"],
    "politics": ["politics", "government", "policy", "election", "congress"],
    "sports": ["sports", "nfl", "nba", "mlb", "soccer", "tennis"],
    "entertainment": ["entertainment", "movies", "music", "gaming", "celebrity"],
}

NEWS_API_SOURCES = [
    {
        "name": "newsapi_org",
        "url": "https://newsapi.org/v2/top-headlines",
        "key_env": "NEWSAPI_KEY",
        "params": {"country": "us", "pageSize": 20},
    },
]

RSS_FEEDS = {
    "technology": [
        "https://feeds.feedburner.com/TechCrunch",
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.wired.com/feed/rss",
        "https://hnrss.org/frontpage",
    ],
    "world": [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.theguardian.com/world/rss",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    ],
    "business": [
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    ],
    "science": [
        "https://www.sciencedaily.com/rss/all.xml",
        "https://www.nature.com/nature.rss",
        "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
    ],
    "health": [
        "https://www.who.int/rss-feeds/news-english.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml",
        "https://www.cdc.gov/rss/cdc.xml",
    ],
    "politics": [
        "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
        "https://feeds.bbci.co.uk/news/politics/rss.xml",
    ],
    "sports": [
        "https://www.espn.com/espn/rss/news",
        "https://feeds.bbci.co.uk/sport/rss.xml",
    ],
    "entertainment": [
        "https://variety.com/feed/",
        "https://www.hollywoodreporter.com/feed/",
        "https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml",
    ],
}

TRENDING_SOURCES = {
    "reddit": "https://www.reddit.com/r/all/top/.json?t=day&limit=25",
    "github": "https://api.github.com/search/repositories?q=created:>%s&sort=stars&order=desc&per_page=10",
    "hackernews": "https://hacker-news.firebaseio.com/v0/topstories.json",
}

CACHE_DIR = project_path_str(".cache", "news_agent")
KNOWLEDGE_DIR = project_path_str("knowledge")
DAILY_DIR = os.path.join(KNOWLEDGE_DIR, "daily")
CACHE_TTL_SECONDS = 1800


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _ensure_dirs():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    os.makedirs(DAILY_DIR, exist_ok=True)


def _random_ua() -> str:
    return random.choice(DEFAULT_USER_AGENTS)


def _headers(extra: dict = None) -> dict:
    h = {
        "User-Agent": _random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    if extra:
        h.update(extra)
    return h


def _session() -> Optional[requests.Session]:
    if not HAS_REQUESTS:
        return None
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s


def _cache_key(*parts) -> str:
    raw = "_".join(str(p) for p in parts)
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_get(key: str) -> Optional[Any]:
    path = os.path.join(CACHE_DIR, f"{key}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if time.time() - data.get("_cached_at", 0) > CACHE_TTL_SECONDS:
            return None
        return data.get("payload")
    except Exception:
        return None


def _cache_set(key: str, payload: Any):
    path = os.path.join(CACHE_DIR, f"{key}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"_cached_at": time.time(), "payload": payload}, f, ensure_ascii=False)
    except Exception as exc:
        logger.debug("Cache write failed: %s", exc)


def _slugify(text: str) -> str:
    return re.sub(r"[^\w\-]+", "_", text.lower()).strip("_")[:80]


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _success(result: Any = None, message: str = "OK") -> dict:
    return {"status": "success", "result": result, "message": message}


def _error(message: str = "An error occurred", result: Any = None) -> dict:
    return {"status": "error", "result": result, "message": message}


def _safe_request(url: str, timeout: int = 15, **kwargs) -> Optional[requests.Response]:
    if not HAS_REQUESTS:
        return None
    try:
        s = _session()
        resp = s.get(url, headers=_headers(), timeout=timeout, **kwargs)
        resp.raise_for_status()
        return resp
    except Exception as exc:
        logger.debug("Request failed for %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# NewsAgent
# ---------------------------------------------------------------------------

class NewsAgent:
    """Self-updating news & knowledge agent for Tom.
    Automatically scrapes news, learns, and updates knowledge daily.
    """

    def __init__(self, cache_ttl: int = CACHE_TTL_SECONDS):
        _ensure_dirs()
        self.cache_ttl = cache_ttl
        self._api_keys: dict = {}
        self._learned_topics: Dict[str, dict] = {}
        self._monitor_state: Dict[str, dict] = {}
        self._load_api_keys()
        self._load_learned_topics()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_api_keys(self):
        for key_name in ["NEWSAPI_KEY", "MEDIASTACK_KEY", "GNEWS_API_KEY"]:
            self._api_keys[key_name] = os.environ.get(key_name, "")

    def _load_learned_topics(self):
        path = os.path.join(KNOWLEDGE_DIR, "learned_topics.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._learned_topics = json.load(f)
            except Exception:
                self._learned_topics = {}

    def _save_learned_topics(self):
        path = os.path.join(KNOWLEDGE_DIR, "learned_topics.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._learned_topics, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.debug("Failed to save learned topics: %s", exc)

    def _fetch_rss_feed(self, feed_url: str) -> List[dict]:
        items = []
        if HAS_FEEDPARSER:
            try:
                parsed = feedparser.parse(feed_url)
                for entry in parsed.entries:
                    item = {
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "summary": entry.get("summary", entry.get("description", "")),
                        "date": entry.get("published", entry.get("updated", "")),
                        "source": feed_url,
                    }
                    items.append(item)
                return items
            except Exception as exc:
                logger.debug("feedparser failed for %s: %s", feed_url, exc)

        raw = _safe_request(feed_url, timeout=12)
        if raw is None:
            return items
        try:
            root = ET.fromstring(raw.content)
            ns = {"atom": "http://www.w3.org/2005/Atom", "rss": ""}
            for entry in root.iter("item"):
                title = entry.findtext("title", "")
                link = entry.findtext("link", "")
                desc = entry.findtext("description", "")
                pubdate = entry.findtext("pubDate", "")
                items.append({"title": title, "link": link, "summary": desc, "date": pubdate, "source": feed_url})
            if not items:
                for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
                    title = entry.findtext("{http://www.w3.org/2005/Atom}title", "")
                    link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                    link = link_el.get("href", "") if link_el is not None else ""
                    summary = entry.findtext("{http://www.w3.org/2005/Atom}summary", "")
                    updated = entry.findtext("{http://www.w3.org/2005/Atom}updated", "")
                    items.append({"title": title, "link": link, "summary": summary, "date": updated, "source": feed_url})
        except Exception as exc:
            logger.debug("XML parsing failed for %s: %s", feed_url, exc)
        return items

    def _fetch_newsapi(self, category: str) -> List[dict]:
        """Fetch headlines from newsapi.org if key is configured."""
        api_key = self._api_keys.get("NEWSAPI_KEY", "")
        if not api_key:
            return []

        items = []
        for source in NEWS_API_SOURCES:
            if source["name"] != "newsapi_org":
                continue
            try:
                params = dict(source["params"])
                params["apiKey"] = api_key
                if category:
                    params["category"] = category
                resp = _safe_request(source["url"], params=params, timeout=10)
                if resp is None:
                    continue
                data = resp.json()
                for article in data.get("articles", []):
                    items.append({
                        "title": article.get("title", ""),
                        "link": article.get("url", ""),
                        "summary": article.get("description", ""),
                        "date": article.get("publishedAt", ""),
                        "source": article.get("source", {}).get("name", "NewsAPI"),
                        "image": article.get("urlToImage", ""),
                    })
            except Exception as exc:
                logger.debug("NewsAPI error for %s: %s", category, exc)
        return items

    def _scrape_article_text(self, url: str) -> Optional[str]:
        """Extract article body text using newspaper3k or readability + bs4."""
        if HAS_NEWSPAPER:
            try:
                article = NewspaperArticle(url)
                article.download()
                article.parse()
                return article.text
            except Exception as exc:
                logger.debug("newspaper3k failed for %s: %s", url, exc)

        if HAS_READABILITY and HAS_REQUESTS:
            try:
                resp = _safe_request(url, timeout=15)
                if resp:
                    doc = ReadabilityDocument(resp.text)
                    return doc.summary()
            except Exception as exc:
                logger.debug("readability failed for %s: %s", url, exc)

        if HAS_BEAUTIFULSOUP and HAS_REQUESTS:
            try:
                resp = _safe_request(url, timeout=15)
                if resp:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                        tag.decompose()
                    text = soup.get_text(separator="\n")
                    lines = [l.strip() for l in text.splitlines() if l.strip()]
                    return "\n".join(lines)
            except Exception as exc:
                logger.debug("bs4 fallback failed for %s: %s", url, exc)

        return None

    def _extract_article_metadata(self, url: str, html: str = None) -> dict:
        """Extract metadata like author, date, images from HTML."""
        meta = {"title": "", "author": "", "date": "", "images": [], "description": ""}
        if not html:
            resp = _safe_request(url, timeout=15)
            if resp is None:
                return meta
            html = resp.text

        if not HAS_BEAUTIFULSOUP:
            return meta

        try:
            soup = BeautifulSoup(html, "html.parser")

            og_title = soup.find("meta", property="og:title")
            if og_title:
                meta["title"] = og_title.get("content", "")
            if not meta["title"] and soup.title:
                meta["title"] = soup.title.get_text(strip=True)

            for prop in ["article:author", "twitter:creator"]:
                tag = soup.find("meta", property=prop)
                if tag:
                    meta["author"] = tag.get("content", "")
                    break
            if not meta["author"]:
                for cls in ["author", "byline"]:
                    el = soup.find(class_=cls)
                    if el:
                        meta["author"] = el.get_text(strip=True)
                        break

            for prop in ["article:published_time", "date"]:
                tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
                if tag:
                    meta["date"] = tag.get("content", "")
                    break

            og_desc = soup.find("meta", property="og:description")
            if og_desc:
                meta["description"] = og_desc.get("content", "")
            if not meta["description"]:
                mdesc = soup.find("meta", attrs={"name": "description"})
                if mdesc:
                    meta["description"] = mdesc.get("content", "")

            for img in soup.find_all("meta", property="og:image"):
                src = img.get("content", "")
                if src:
                    meta["images"].append(src)
            if not meta["images"]:
                for img in soup.find_all("img", src=True):
                    src = img["src"]
                    if src.startswith("http") or src.startswith("//"):
                        if src.startswith("//"):
                            src = "https:" + src
                        meta["images"].append(src)
        except Exception as exc:
            logger.debug("Metadata extraction failed: %s", exc)

        return meta

    # ------------------------------------------------------------------
    # 1. fetch_headlines
    # ------------------------------------------------------------------

    def fetch_headlines(self, categories: list = None) -> dict:
        """Fetch top headlines from multiple news sources.

        Args:
            categories: List of categories (e.g. ["technology", "world"]).
                        If None, fetches all categories.

        Returns:
            dict with status, result (dict of category -> list of headlines)
        """
        if categories is None:
            categories = list(CATEGORIES.keys())

        result = {}
        errors = []

        for cat in categories:
            if cat not in CATEGORIES:
                errors.append(f"Unknown category: {cat}")
                continue

            cache_key_str = _cache_key("headlines", cat)
            cached = _cache_get(cache_key_str)
            if cached is not None:
                result[cat] = cached
                continue

            headlines = []

            api_headlines = self._fetch_newsapi(cat)
            headlines.extend(api_headlines)

            rss_urls = RSS_FEEDS.get(cat, [])
            for feed_url in rss_urls:
                try:
                    feed_items = self._fetch_rss_feed(feed_url)
                    headlines.extend(feed_items)
                except Exception as exc:
                    logger.debug("RSS error for %s: %s", feed_url, exc)

            seen_links = set()
            deduped = []
            for h in headlines:
                link = h.get("link", "")
                if link and link not in seen_links:
                    seen_links.add(link)
                    deduped.append(h)
                elif not link:
                    deduped.append(h)

            result[cat] = deduped[:30]
            _cache_set(cache_key_str, result[cat])

        msg = f"Fetched headlines for {len(result)} categories"
        if errors:
            msg += f" ({len(errors)} errors: {'; '.join(errors[:3])})"
        return _success(result, msg)

    # ------------------------------------------------------------------
    # 2. fetch_full_article
    # ------------------------------------------------------------------

    def fetch_full_article(self, url: str) -> dict:
        """Fetch and extract full article content from a URL.

        Extracts title, author, date, body text, images.
        Handles paywalls gracefully.
        """
        if not url or not url.startswith(("http://", "https://")):
            return _error("Invalid URL provided")

        cache_key_str = _cache_key("article", url)
        cached = _cache_get(cache_key_str)
        if cached is not None:
            return _success(cached)

        try:
            resp = _safe_request(url, timeout=20)
            if resp is None:
                return _error("Failed to fetch URL after retries")

            html = resp.text
            metadata = self._extract_article_metadata(url, html)
            body_text = self._scrape_article_text(url)

            article = {
                "url": url,
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "date": metadata.get("date", ""),
                "description": metadata.get("description", ""),
                "body": body_text or "",
                "images": metadata.get("images", []),
                "word_count": len((body_text or "").split()),
                "fetched_at": _now_str(),
                "source_domain": urlparse(url).netloc,
            }

            _cache_set(cache_key_str, article)
            return _success(article, "Article fetched successfully")

        except Exception as exc:
            return _error(f"Article fetch failed: {exc}")

    # ------------------------------------------------------------------
    # 3. search_news
    # ------------------------------------------------------------------

    def search_news(self, query: str, max_results: int = 10) -> dict:
        """Search news across multiple sources.

        Uses Google News search, RSS feeds, and API backends.
        """
        if not query or not query.strip():
            return _error("Search query is required")

        results = []
        seen_links = set()
        errors = []

        cache_key_str = _cache_key("search", query.strip().lower(), str(max_results))
        cached = _cache_get(cache_key_str)
        if cached is not None:
            return _success(cached)

        if HAS_GOOGLE_SEARCH:
            try:
                for url in google_search(query + " news", num_results=max_results):
                    if url not in seen_links:
                        seen_links.add(url)
                        results.append({
                            "title": "",
                            "link": url,
                            "summary": "",
                            "date": "",
                            "source": "Google Search",
                        })
            except Exception as exc:
                errors.append(f"Google search failed: {exc}")

        if HAS_REQUESTS:
            try:
                gnews_url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
                rss_results = self._fetch_rss_feed(gnews_url)
                for item in rss_results:
                    link = item.get("link", "")
                    if link and link not in seen_links and len(results) < max_results:
                        seen_links.add(link)
                        results.append(item)
            except Exception as exc:
                errors.append(f"Google News RSS failed: {exc}")

            try:
            # Also search across relevant RSS feeds for the query
                for cat, urls in RSS_FEEDS.items():
                    for feed_url in urls[:2]:
                        if len(results) >= max_results:
                            break
                        feed_items = self._fetch_rss_feed(feed_url)
                        query_lower = query.lower()
                        for item in feed_items:
                            if len(results) >= max_results:
                                break
                            title = (item.get("title") or "").lower()
                            summary = (item.get("summary") or "").lower()
                            if query_lower in title or query_lower in summary:
                                link = item.get("link", "")
                                if link and link not in seen_links:
                                    seen_links.add(link)
                                    results.append(item)
            except Exception as exc:
                errors.append(f"RSS search failed: {exc}")

        final = results[:max_results]
        _cache_set(cache_key_str, final)

        msg = f"Found {len(final)} results for '{query}'"
        if errors:
            msg += f" ({len(errors)} backends had issues)"
        return _success(final, msg)

    # ------------------------------------------------------------------
    # 4. fetch_rss
    # ------------------------------------------------------------------

    def fetch_rss(self, feed_url: str) -> dict:
        """Parse any RSS/Atom feed.

        Returns items with title, link, summary, date.
        """
        if not feed_url:
            return _error("Feed URL is required")

        cache_key_str = _cache_key("rss", feed_url)
        cached = _cache_get(cache_key_str)
        if cached is not None:
            return _success(cached)

        try:
            items = self._fetch_rss_feed(feed_url)
            feed_info = {
                "url": feed_url,
                "items": items,
                "count": len(items),
                "fetched_at": _now_str(),
            }
            _cache_set(cache_key_str, feed_info)
            return _success(feed_info, f"Parsed {len(items)} items from feed")
        except Exception as exc:
            return _error(f"RSS parsing failed: {exc}")

    # ------------------------------------------------------------------
    # 5. daily_briefing
    # ------------------------------------------------------------------

    def daily_briefing(self) -> dict:
        """Fetch today's top stories across ALL categories.

        Returns a comprehensive daily briefing as formatted markdown.
        """
        all_categories = list(CATEGORIES.keys())
        headlines_result = self.fetch_headlines(all_categories)
        if headlines_result["status"] == "error":
            return headlines_result

        today = _today_str()
        briefing_lines = [
            f"# Daily Briefing — {today}",
            "",
            f"_Generated by Tom's News Agent at {_now_str()}_",
            "",
            "---",
            "",
        ]

        category_titles = {
            "technology": "Technology & AI",
            "world": "World Events",
            "business": "Business & Finance",
            "science": "Science & Discovery",
            "health": "Health & Medicine",
            "politics": "Politics & Policy",
            "sports": "Sports",
            "entertainment": "Entertainment & Culture",
        }

        headlines = headlines_result["result"]
        total_stories = 0

        for cat in all_categories:
            cat_headlines = headlines.get(cat, [])
            if not cat_headlines:
                continue

            display = category_titles.get(cat, cat.title())
            briefing_lines.append(f"## {display}")
            briefing_lines.append("")

            count = min(len(cat_headlines), 7)
            for i in range(count):
                h = cat_headlines[i]
                title = h.get("title", "No title")
                link = h.get("link", "")
                source = h.get("source", "")
                date = h.get("date", "")
                line = f"- **{title}**"
                if source:
                    line += f" — {source}"
                if date:
                    line += f" ({date[:10]})"
                briefing_lines.append(line)

            total_stories += count
            briefing_lines.append("")

        if total_stories == 0:
            briefing_lines.append("_No stories fetched today. Check network connectivity or API keys._")

        briefing_lines.append("---")
        briefing_lines.append(f"_Briefing contains {total_stories} stories across {len(all_categories)} categories._")

        markdown = "\n".join(briefing_lines)

        result = {
            "date": today,
            "categories_covered": all_categories,
            "total_stories": total_stories,
            "markdown": markdown,
        }

        return _success(result, f"Daily briefing generated with {total_stories} stories")

    # ------------------------------------------------------------------
    # 6. monitor_topics
    # ------------------------------------------------------------------

    def monitor_topics(self, topics: list) -> dict:
        """Continuously monitor specified topics for new developments.

        Tracks changes over time by comparing against previously stored state.
        Returns updates when significant changes are detected.
        """
        if not topics:
            return _error("Topics list is empty")

        updates = {}

        for topic in topics:
            topic_lower = topic.strip().lower()
            if not topic_lower:
                continue

            search_result = self.search_news(topic_lower, max_results=15)
            if search_result["status"] == "error":
                updates[topic] = {"error": search_result["message"]}
                continue

            articles = search_result["result"]
            current_links = {a.get("link", "") for a in articles}
            previous_state = self._monitor_state.get(topic_lower, {})
            previous_links = set(previous_state.get("links", []))

            new_articles = [a for a in articles if a.get("link", "") not in previous_links]
            changed = len(new_articles) > 0

            if changed:
                updates[topic] = {
                    "new_articles": new_articles,
                    "new_count": len(new_articles),
                    "total_tracked": len(current_links),
                    "last_checked": _now_str(),
                }
            else:
                updates[topic] = {
                    "new_articles": [],
                    "new_count": 0,
                    "total_tracked": len(current_links),
                    "last_checked": _now_str(),
                }

            self._monitor_state[topic_lower] = {
                "links": list(current_links),
                "last_checked": _now_str(),
            }

        changed_topics = {k: v for k, v in updates.items() if v.get("new_count", 0) > 0}
        unchanged_topics = {k: v for k, v in updates.items() if v.get("new_count", 0) == 0}

        result = {
            "changed": changed_topics,
            "unchanged": unchanged_topics,
            "total_changed": len(changed_topics),
            "total_monitored": len(topics),
            "checked_at": _now_str(),
        }

        msg = f"Monitored {len(topics)} topics: {len(changed_topics)} with new developments"
        return _success(result, msg)

    # ------------------------------------------------------------------
    # 7. technology_roundup
    # ------------------------------------------------------------------

    def technology_roundup(self) -> dict:
        """Focused tech news roundup covering AI/ML, frameworks, security, company news."""
        tech_categories = {
            "ai_ml": ["artificial intelligence", "machine learning", "deep learning", "LLM", "GPT", "neural network"],
            "frameworks": ["framework", "library", "npm", "pypi", "react", "angular", "vue", "rust"],
            "security": ["security vulnerability", "CVE", "data breach", "ransomware", "zero-day", "cyberattack"],
            "company": ["Apple", "Google", "Microsoft", "Meta", "Amazon", "NVIDIA", "OpenAI", "Tesla", "Twitter", "X"],
        }

        categories_result = self.fetch_headlines(["technology"])
        tech_headlines = categories_result.get("result", {}).get("technology", []) if categories_result["status"] == "success" else []

        sections = {}
        total_matched = 0

        for section, keywords in tech_categories.items():
            matched = []
            seen = set()
            for h in tech_headlines:
                title = (h.get("title", "") + " " + h.get("summary", "")).lower()
                for kw in keywords:
                    if kw.lower() in title:
                        link = h.get("link", "")
                        if link not in seen:
                            seen.add(link)
                            matched.append(h)
                            total_matched += 1
                        break
            sections[section] = matched[:8]

        additional_searches = ["cybersecurity news 2025", "AI breakthrough", "software release"]
        for search_term in additional_searches:
            search_result = self.search_news(search_term, max_results=5)
            if search_result["status"] == "success":
                for a in search_result["result"]:
                    sections.setdefault("general_tech", []).append(a)
                    total_matched += 1

        roundup_text_lines = [
            f"# Technology Roundup — {_today_str()}",
            "",
            f"_Curated by Tom's News Agent_",
            "",
            "---",
            "",
        ]

        section_titles = {
            "ai_ml": "## AI / Machine Learning",
            "frameworks": "## Frameworks & Tools",
            "security": "## Security & Vulnerabilities",
            "company": "## Company News",
            "general_tech": "## General Tech",
        }

        for sec, title in section_titles.items():
            items = sections.get(sec, [])
            if items:
                roundup_text_lines.append(title)
                roundup_text_lines.append("")
                for item in items[:5]:
                    t = item.get("title", "No title")
                    s = item.get("source", "")
                    l = item.get("link", "")
                    roundup_text_lines.append(f"- **{t}** ({s})")
                roundup_text_lines.append("")

        result = {
            "date": _today_str(),
            "sections": {k: v[:10] for k, v in sections.items()},
            "total_stories": total_matched,
            "markdown": "\n".join(roundup_text_lines),
        }

        return _success(result, f"Technology roundup: {total_matched} stories across {len(sections)} sections")

    # ------------------------------------------------------------------
    # 8. world_events
    # ------------------------------------------------------------------

    def world_events(self) -> dict:
        """World events coverage: conflicts, disasters, diplomacy, climate, economy."""
        categories_result = self.fetch_headlines(["world", "business", "science"])
        combined = []
        if categories_result["status"] == "success":
            for cat in ["world", "business", "science"]:
                combined.extend(categories_result["result"].get(cat, []))

        seen_links = set()
        deduped = []
        for h in combined:
            link = h.get("link", "")
            if link and link not in seen_links:
                seen_links.add(link)
                deduped.append(h)
            elif not link:
                deduped.append(h)

        event_keywords = {
            "conflicts": ["war", "conflict", "military", "invasion", "sanction", "diplomat", "treaty", "ceasefire", "missile", "defense", "army", "navy"],
            "disasters": ["earthquake", "hurricane", "flood", "wildfire", "tsunami", "tornado", "drought", "famine", "eruption", "landslide"],
            "climate": ["climate change", "global warming", "emissions", "renewable", "fossil fuel", "carbon", "Paris Agreement", "COP", "green energy"],
            "economy": ["inflation", "GDP", "recession", "interest rate", "central bank", "trade war", "tariff", "unemployment", "stock market", "crypto"],
            "health_crisis": ["pandemic", "outbreak", "epidemic", "WHO", "vaccine", "infection", "virus", "hospital"],
        }

        sections = {}
        for section, keywords in event_keywords.items():
            matched = []
            seen_sec = set()
            for h in deduped:
                text = (h.get("title", "") + " " + h.get("summary", "")).lower()
                for kw in keywords:
                    if kw.lower() in text:
                        link = h.get("link", "")
                        if link not in seen_sec:
                            seen_sec.add(link)
                            matched.append(h)
                        break
            sections[section] = matched[:10]

        briefing_lines = [
            f"# World Events Briefing — {_today_str()}",
            "",
            f"_Compiled by Tom's News Agent_",
            "",
            "---",
            "",
        ]

        section_titles = {
            "conflicts": "## Conflicts & Geopolitics",
            "disasters": "## Natural Disasters",
            "climate": "## Climate & Environment",
            "economy": "## Economic Developments",
            "health_crisis": "## Health Crises",
        }

        total = 0
        for sec, title in section_titles.items():
            items = sections.get(sec, [])
            if items:
                briefing_lines.append(title)
                briefing_lines.append("")
                for item in items[:5]:
                    t = item.get("title", "No title")
                    s = item.get("source", "")
                    briefing_lines.append(f"- **{t}** ({s})")
                briefing_lines.append("")
                total += len(items)

        result = {
            "date": _today_str(),
            "sections": sections,
            "total_stories": total,
            "markdown": "\n".join(briefing_lines),
        }

        return _success(result, f"World events: {total} stories across {len(sections)} categories")

    # ------------------------------------------------------------------
    # 9. update_knowledge_base
    # ------------------------------------------------------------------

    def update_knowledge_base(self, output_dir: str = "knowledge") -> dict:
        """Take today's news and persist it into the knowledge base.

        Generates a daily summary file in knowledge/daily/ and tracks
        what has been learned over time.
        """
        target_dir = output_dir if os.path.isabs(output_dir) else project_path_str(output_dir)
        daily_target = os.path.join(target_dir, "daily")
        os.makedirs(daily_target, exist_ok=True)

        today = _today_str()
        log = {
            "date": today,
            "timestamp": _now_str(),
            "categories_fetched": [],
            "total_articles": 0,
            "files_written": [],
            "errors": [],
        }

        briefing_result = self.daily_briefing()
        if briefing_result["status"] == "success":
            briefing_data = briefing_result["result"]
            briefing_path = os.path.join(daily_target, f"briefing_{today}.md")
            try:
                with open(briefing_path, "w", encoding="utf-8") as f:
                    f.write(briefing_data.get("markdown", ""))
                log["files_written"].append(briefing_path)
                log["categories_fetched"] = briefing_data.get("categories_covered", [])
                log["total_articles"] = briefing_data.get("total_stories", 0)
            except Exception as exc:
                log["errors"].append(f"Failed to write briefing: {exc}")

        tech_result = self.technology_roundup()
        if tech_result["status"] == "success":
            tech_data = tech_result["result"]
            tech_path = os.path.join(daily_target, f"tech_roundup_{today}.md")
            try:
                with open(tech_path, "w", encoding="utf-8") as f:
                    f.write(tech_data.get("markdown", ""))
                log["files_written"].append(tech_path)
            except Exception as exc:
                log["errors"].append(f"Failed to write tech roundup: {exc}")

        world_result = self.world_events()
        if world_result["status"] == "success":
            world_data = world_result["result"]
            world_path = os.path.join(daily_target, f"world_events_{today}.md")
            try:
                with open(world_path, "w", encoding="utf-8") as f:
                    f.write(world_data.get("markdown", ""))
                log["files_written"].append(world_path)
            except Exception as exc:
                log["errors"].append(f"Failed to write world events: {exc}")

        for cat in CATEGORIES:
            if cat in ["technology", "world"]:
                continue
            headlines_result = self.fetch_headlines([cat])
            if headlines_result["status"] == "success":
                cat_data = headlines_result["result"].get(cat, [])
                if cat_data:
                    cat_path = os.path.join(daily_target, f"{cat}_{today}.json")
                    try:
                        with open(cat_path, "w", encoding="utf-8") as f:
                            json.dump({
                                "date": today,
                                "category": cat,
                                "articles": cat_data[:20],
                                "fetched_at": _now_str(),
                            }, f, ensure_ascii=False, indent=2)
                        log["files_written"].append(cat_path)
                    except Exception as exc:
                        log["errors"].append(f"Failed to write {cat}: {exc}")

        self._learned_topics[today] = {
            "files_written": log["files_written"],
            "total_articles": log["total_articles"],
            "categories": log["categories_fetched"],
        }
        self._save_learned_topics()

        summary_path = os.path.join(target_dir, "learned_topics.json")
        log["summary"] = {
            "total_files": len(log["files_written"]),
            "topics_tracked_file": summary_path,
        }

        return _success(log, f"Knowledge base updated: {len(log['files_written'])} files written for {today}")

    # ------------------------------------------------------------------
    # 10. scrape_website
    # ------------------------------------------------------------------

    def scrape_website(self, url: str) -> dict:
        """General-purpose web scraper with multiple fallback strategies.

        Extracts all text content from a URL. Supports static HTML
        and attempts JavaScript-rendered content via Playwright.
        """
        if not url or not url.startswith(("http://", "https://")):
            return _error("Invalid URL")

        cache_key_str = _cache_key("scrape", url)
        cached = _cache_get(cache_key_str)
        if cached is not None:
            return _success(cached)

        result = {
            "url": url,
            "title": "",
            "text_content": "",
            "metadata": {},
            "links": [],
            "images": [],
            "scrape_method": "",
            "scraped_at": _now_str(),
        }

        html = None
        resp = _safe_request(url, timeout=25)
        if resp is not None:
            html = resp.text
            result["metadata"]["status_code"] = resp.status_code
            result["metadata"]["content_type"] = resp.headers.get("content-type", "")
            result["scrape_method"] = "requests"

        if html is None:
            try:
                from playwright.async_api import async_playwright
                result["scrape_method"] = "playwright"

                async def _playwright_scrape():
                    async with async_playwright() as p:
                        browser = await p.chromium.launch(headless=True)
                        page = await browser.new_page()
                        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        content = await page.content()
                        title = await page.title()
                        await browser.close()
                        return content, title

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                html, page_title = loop.run_until_complete(_playwright_scrape())
                loop.close()
                result["title"] = page_title

            except ImportError:
                return _error("No scraping backend available (install requests or playwright)")
            except Exception as exc:
                return _error(f"Playwright scraping failed: {exc}")

        if html and HAS_BEAUTIFULSOUP:
            try:
                soup = BeautifulSoup(html, "html.parser")
                if not result["title"] and soup.title:
                    result["title"] = soup.title.get_text(strip=True)

                for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
                    tag.decompose()

                for tag in soup.find_all(["a"]):
                    href = tag.get("href", "")
                    if href and not href.startswith("#") and not href.startswith("javascript:"):
                        absolute = urljoin(url, href)
                        if absolute.startswith(("http://", "https://")):
                            result["links"].append({"text": tag.get_text(strip=True), "href": absolute})

                for tag in soup.find_all("img"):
                    src = tag.get("src", "")
                    if src:
                        absolute = urljoin(url, src)
                        result["images"].append(absolute)

                body = soup.get_text(separator="\n")
                lines = [l.strip() for l in body.splitlines() if l.strip()]
                result["text_content"] = "\n".join(lines)

                og_desc = soup.find("meta", property="og:description")
                if og_desc:
                    result["metadata"]["description"] = og_desc.get("content", "")
            except Exception as exc:
                logger.debug("BeautifulSoup parsing failed: %s", exc)
                result["text_content"] = html

        elif html:
            try:
                from lxml import html as lxml_html
                tree = lxml_html.fromstring(html)
                result["text_content"] = tree.text_content()
            except ImportError:
                result["text_content"] = html

        result["word_count"] = len(result["text_content"].split()) if result["text_content"] else 0
        result["char_count"] = len(result["text_content"]) if result["text_content"] else 0

        _cache_set(cache_key_str, result)
        return _success(result, f"Scraped {result['word_count']} words from {url} via {result['scrape_method']}")

    # ------------------------------------------------------------------
    # 11. get_trending_topics
    # ------------------------------------------------------------------

    def get_trending_topics(self) -> dict:
        """Identify trending topics across the web.

        Uses Reddit, GitHub trending, Hacker News, and web searches
        to identify what's popular right now.
        """
        cache_key_str = _cache_key("trending")
        cached = _cache_get(cache_key_str)
        if cached is not None:
            return _success(cached)

        trends = {
            "reddit": [],
            "github": [],
            "hackernews": [],
            "web": [],
            "aggregated": [],
        }
        errors = []

        if HAS_REQUESTS:
            try:
                reddit_url = TRENDING_SOURCES["reddit"]
                resp = _safe_request(reddit_url, timeout=10,
                                     headers={"User-Agent": "tom-news-agent/1.0"})
                if resp is not None:
                    data = resp.json()
                    for post in data.get("data", {}).get("children", []):
                        pdata = post.get("data", {})
                        trends["reddit"].append({
                            "title": pdata.get("title", ""),
                            "url": pdata.get("url", ""),
                            "score": pdata.get("score", 0),
                            "subreddit": pdata.get("subreddit", ""),
                            "num_comments": pdata.get("num_comments", 0),
                            "source": "reddit",
                        })
            except Exception as exc:
                errors.append(f"Reddit trending failed: {exc}")

            try:
                gh_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                gh_url = TRENDING_SOURCES["github"] % gh_date
                resp = _safe_request(gh_url, timeout=10)
                if resp is not None:
                    data = resp.json()
                    for repo in data.get("items", [])[:10]:
                        trends["github"].append({
                            "title": repo.get("full_name", ""),
                            "url": repo.get("html_url", ""),
                            "description": repo.get("description", ""),
                            "stars": repo.get("stargazers_count", 0),
                            "language": repo.get("language", ""),
                            "source": "github",
                        })
            except Exception as exc:
                errors.append(f"GitHub trending failed: {exc}")

            try:
                hn_url = TRENDING_SOURCES["hackernews"]
                resp = _safe_request(hn_url, timeout=10)
                if resp is not None:
                    story_ids = resp.json()[:20]
                    stories = []
                    for sid in story_ids:
                        s_resp = _safe_request(
                            f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                            timeout=5
                        )
                        if s_resp is not None:
                            stories.append(s_resp.json())
                    for story in stories:
                        if story and story.get("title"):
                            trends["hackernews"].append({
                                "title": story.get("title", ""),
                                "url": story.get("url", f"https://news.ycombinator.com/item?id={story.get('id', '')}"),
                                "score": story.get("score", 0),
                                "by": story.get("by", ""),
                                "descendants": story.get("descendants", 0),
                                "source": "hackernews",
                            })
            except Exception as exc:
                errors.append(f"Hacker News trending failed: {exc}")

            try:
                web_terms = ["breaking news", "trending today", "viral", "whats happening"]
                seen_phrases = set()
                for term in web_terms:
                    if HAS_GOOGLE_SEARCH:
                        for url in google_search(term, num_results=5):
                            parsed = urlparse(url)
                            phrase = parsed.netloc.replace("www.", "")
                            if phrase not in seen_phrases and len(seen_phrases) < 15:
                                seen_phrases.add(phrase)
                                trends["web"].append({
                                    "title": f"Trending on {phrase}",
                                    "url": url,
                                    "source": "web",
                                })
            except Exception as exc:
                errors.append(f"Web trending search failed: {exc}")

        all_items = []
        for source_key in ["reddit", "github", "hackernews", "web"]:
            all_items.extend(trends[source_key])

        all_items.sort(key=lambda x: x.get("score", 0) if isinstance(x.get("score"), (int, float)) else 0, reverse=True)

        trends["aggregated"] = all_items[:30]

        topic_cloud = {}
        for item in all_items:
            title = item.get("title", "")
            words = re.findall(r'\b[A-Z][a-z]{2,}\b', title)
            for w in words[:5]:
                wl = w.lower()
                if len(wl) > 3:
                    topic_cloud[wl] = topic_cloud.get(wl, 0) + 1

        top_terms = sorted(topic_cloud.items(), key=lambda x: -x[1])[:20]
        trends["trending_terms"] = [{"term": t, "count": c} for t, c in top_terms]

        result = {
            "trends": trends,
            "sources_checked": ["reddit", "github", "hackernews", "web"],
            "total_items": len(all_items),
            "fetched_at": _now_str(),
            "errors": errors if errors else None,
        }

        _cache_set(cache_key_str, result)
        msg = f"Found {len(all_items)} trending items across {len(result['sources_checked'])} sources"
        return _success(result, msg)

    # ------------------------------------------------------------------
    # Async variants
    # ------------------------------------------------------------------

    async def fetch_headlines_async(self, categories: list = None) -> dict:
        """Async version of fetch_headlines using aiohttp."""
        if not HAS_AIOHTTP:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self.fetch_headlines, categories)

        if categories is None:
            categories = list(CATEGORIES.keys())

        result = {}
        errors = []

        async def _fetch_category_async(cat: str):
            cache_key_str = _cache_key("headlines", cat)
            cached = _cache_get(cache_key_str)
            if cached is not None:
                return cat, cached, None

            headlines = []

            rss_urls = RSS_FEEDS.get(cat, [])
            for feed_url in rss_urls:
                try:
                    async with aiohttp.ClientSession(headers=_headers()) as session:
                        async with session.get(feed_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                            if resp.status == 200:
                                text = await resp.text()
                                if HAS_FEEDPARSER:
                                    import io
                                    parsed = feedparser.parse(io.StringIO(text))
                                    for entry in parsed.entries:
                                        headlines.append({
                                            "title": entry.get("title", ""),
                                            "link": entry.get("link", ""),
                                            "summary": entry.get("summary", ""),
                                            "date": entry.get("published", ""),
                                            "source": feed_url,
                                        })
                except Exception as exc:
                    logger.debug("Async RSS error for %s: %s", feed_url, exc)

            seen_links = set()
            deduped = []
            for h in headlines:
                link = h.get("link", "")
                if link and link not in seen_links:
                    seen_links.add(link)
                    deduped.append(h)
                elif not link:
                    deduped.append(h)

            return cat, deduped[:30], None

        tasks = [_fetch_category_async(cat) for cat in categories]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, Exception):
                errors.append(str(r))
                continue
            cat, headlines, _ = r
            result[cat] = headlines
            _cache_set(_cache_key("headlines", cat), headlines)

        msg = f"Fetched headlines for {len(result)} categories (async)"
        return _success(result, msg)

    async def daily_briefing_async(self) -> dict:
        """Async version of daily_briefing."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.daily_briefing)

    async def technology_roundup_async(self) -> dict:
        """Async version of technology_roundup."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.technology_roundup)

    async def world_events_async(self) -> dict:
        """Async version of world_events."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.world_events)

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    def clear_cache(self, older_than_hours: int = 0) -> dict:
        """Clear the news agent cache.

        Args:
            older_than_hours: If > 0, only clear cache entries older than this.
        """
        cleared = 0
        errors = 0
        cutoff = time.time() - (older_than_hours * 3600) if older_than_hours > 0 else 0

        for fname in os.listdir(CACHE_DIR):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(CACHE_DIR, fname)
            try:
                if cutoff > 0:
                    mtime = os.path.getmtime(fpath)
                    if mtime > cutoff:
                        continue
                os.remove(fpath)
                cleared += 1
            except Exception:
                errors += 1

        msg = f"Cleared {cleared} cache files"
        if errors:
            msg += f" ({errors} errors)"
        return _success({"cleared": cleared, "errors": errors}, msg)


# ---------------------------------------------------------------------------
# Standalone entry points
# ---------------------------------------------------------------------------

def run_daily_briefing():
    """CLI entry point: run daily briefing and print markdown."""
    agent = NewsAgent()
    result = agent.daily_briefing()
    if result["status"] == "success":
        print(result["result"]["markdown"])
    else:
        print(f"Error: {result['message']}")
        return 1
    return 0


def run_technology_roundup():
    """CLI entry point: run technology roundup."""
    agent = NewsAgent()
    result = agent.technology_roundup()
    if result["status"] == "success":
        print(result["result"]["markdown"])
    else:
        print(f"Error: {result['message']}")
        return 1
    return 0


def run_update_knowledge():
    """CLI entry point: update knowledge base."""
    agent = NewsAgent()
    result = agent.update_knowledge_base()
    if result["status"] == "success":
        log = result["result"]
        print(f"Knowledge base updated for {log['date']}")
        for f in log.get("files_written", []):
            print(f"  Written: {f}")
    else:
        print(f"Error: {result['message']}")
        return 1
    return 0


def run_trending():
    """CLI entry point: show trending topics."""
    agent = NewsAgent()
    result = agent.get_trending_topics()
    if result["status"] == "success":
        trends = result["result"]["trends"]
        print(f"\n=== Trending Topics ({result['result']['fetched_at']}) ===\n")
        for source_key in ["reddit", "github", "hackernews"]:
            items = trends.get(source_key, [])
            if items:
                print(f"\n--- {source_key.upper()} ---")
                for item in items[:5]:
                    title = item.get("title", "")
                    score = item.get("score", 0)
                    lang = item.get("language", "")
                    extra = f" [{lang}]" if lang else ""
                    print(f"  [{score} pts] {title}{extra}")
        if trends.get("trending_terms"):
            print("\n--- Trending Terms ---")
            for t in trends["trending_terms"][:10]:
                print(f"  {t['term']} ({t['count']} mentions)")
    else:
        print(f"Error: {result['message']}")
        return 1
    return 0


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "briefing"
    modes = {
        "briefing": run_daily_briefing,
        "tech": run_technology_roundup,
        "update": run_update_knowledge,
        "trending": run_trending,
    }
    fn = modes.get(mode, run_daily_briefing)
    sys.exit(fn())
