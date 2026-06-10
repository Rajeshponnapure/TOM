"""
Browser task recipes (Phase B3) — scrape tables to CSV, download files,
extract readable page text. requests + BeautifulSoup only (no browser needed),
so these work even where Playwright isn't installed.
"""

import csv
import os
import re
from typing import Any, Dict, List
from urllib.parse import unquote, urlparse

from tools.project_paths import project_path_str

MAX_DOWNLOAD_MB = 200
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TOM-Assistant/1.0"}


def _out_dir(sub: str) -> str:
    d = project_path_str("output", sub)
    os.makedirs(d, exist_ok=True)
    return d


def parse_tables_html(html: str) -> List[List[List[str]]]:
    """Extract all <table> elements as rows of cell-text (offline-testable)."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    tables = []
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True)
                     for c in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


def scrape_tables(url: str) -> Dict[str, Any]:
    """Fetch a page, extract every table, write each to a CSV."""
    import requests
    try:
        resp = requests.get(url, headers=UA, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        return {"status": "error", "message": f"Could not fetch {url}: {e}"}
    tables = parse_tables_html(resp.text)
    if not tables:
        return {"status": "success", "csv_files": [],
                "message": f"No HTML tables found at {url}."}
    stem = re.sub(r"[^a-z0-9]+", "_", (urlparse(url).netloc + urlparse(url).path).lower())[:40]
    out = _out_dir("web")
    paths = []
    for i, rows in enumerate(tables):
        p = os.path.join(out, f"{stem}_table{i + 1}.csv")
        with open(p, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)
        paths.append(p)
    head = tables[0][0] if tables and tables[0] else []
    return {"status": "success", "csv_files": paths,
            "message": f"Scraped {len(paths)} table(s) from {url} → CSV.\n"
                       f"First table: {len(tables[0])} rows, columns: {', '.join(head[:6])}\n"
                       f"Saved: {', '.join(paths)}"}


def download_file(url: str, dest_dir: str = None) -> Dict[str, Any]:
    """Stream a file to output/downloads (size-capped)."""
    import requests
    dest_dir = dest_dir or _out_dir("downloads")
    name = unquote(os.path.basename(urlparse(url).path)) or "download.bin"
    name = re.sub(r"[^\w.\- ]", "_", name)[:120]
    dest = os.path.join(dest_dir, name)
    try:
        with requests.get(url, headers=UA, timeout=60, stream=True) as r:
            r.raise_for_status()
            size = 0
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 16):
                    size += len(chunk)
                    if size > MAX_DOWNLOAD_MB * 1e6:
                        f.close()
                        os.remove(dest)
                        return {"status": "error",
                                "message": f"Aborted: file exceeds {MAX_DOWNLOAD_MB} MB cap."}
                    f.write(chunk)
    except Exception as e:
        return {"status": "error", "message": f"Download failed: {e}"}
    return {"status": "success", "path": dest, "bytes": size,
            "message": f"Downloaded {name} ({size / 1e6:.1f} MB) → {dest}"}


def fetch_text(url: str, max_chars: int = 4000) -> Dict[str, Any]:
    """Readable text of a page (nav/script stripped)."""
    import requests
    from bs4 import BeautifulSoup
    try:
        resp = requests.get(url, headers=UA, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        return {"status": "error", "message": f"Could not fetch {url}: {e}"}
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = re.sub(r"\n{3,}", "\n\n", soup.get_text("\n", strip=True))
    return {"status": "success", "text": text[:max_chars],
            "message": text[:max_chars]}
