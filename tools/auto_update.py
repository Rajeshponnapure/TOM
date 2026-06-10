"""
TOM Auto-Update System — Self-improvement and knowledge expansion.
- Checks git for updates
- Updates pip packages
- Downloads new knowledge
- Scrapes web for latest model/framework news
- Keeps TOM's knowledge base current
"""
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from tools.project_paths import PROJECT_ROOT

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False


class AutoUpdate:
    def __init__(self):
        self.project_dir = str(PROJECT_ROOT)
        self.update_log = os.path.join(self.project_dir, "tom_logs", "update_history.json")
        self.knowledge_dir = os.path.join(self.project_dir, "knowledge")
        self._update_knowledge_dir = os.path.join(self.project_dir, "knowledge", "web")
        os.makedirs(self._update_knowledge_dir, exist_ok=True)
        self._news_sources = [
            "https://github.com/trending",
            "https://news.ycombinator.com/",
            "https://www.reddit.com/r/programming/.rss",
        ]

    def check_git_updates(self) -> Dict[str, Any]:
        """Check if the git repo has remote updates."""
        try:
            result = subprocess.run(
                ["git", "remote", "-v"],
                capture_output=True, text=True, timeout=5, cwd=self.project_dir,
            )
            if result.returncode != 0:
                return {"status": "no_remote", "message": "No git remote configured"}
            remote = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
            result = subprocess.run(
                ["git", "fetch", "--dry-run"],
                capture_output=True, text=True, timeout=10, cwd=self.project_dir,
            )
            if result.stderr.strip():
                updates = result.stderr.strip()
                count = updates.count("\n")
                return {
                    "status": "updates_available" if count > 0 else "up_to_date",
                    "count": count,
                    "details": updates[:500],
                    "remote": remote[:100],
                }
            return {"status": "up_to_date", "count": 0}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def pull_updates(self) -> Dict[str, Any]:
        """Pull latest code from git."""
        try:
            result = subprocess.run(
                ["git", "pull"],
                capture_output=True, text=True, timeout=30, cwd=self.project_dir,
            )
            return {
                "status": "success" if result.returncode == 0 else "error",
                "output": result.stdout.strip()[:1000],
                "error": result.stderr.strip()[:500],
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def update_pip_packages(self) -> Dict[str, Any]:
        """Upgrade all outdated pip packages."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--outdated", "--format=columns"],
                capture_output=True, text=True, timeout=15,
            )
            lines = result.stdout.strip().splitlines()
            if len(lines) <= 2:
                return {"status": "up_to_date", "message": "All pip packages up to date"}
            packages = []
            for line in lines[2:]:
                parts = line.split()
                if len(parts) >= 3:
                    packages.append(parts[0])
            if not packages:
                return {"status": "up_to_date", "message": "All pip packages up to date"}
            updated = []
            failed = []
            for pkg in packages[:10]:
                try:
                    r = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "--upgrade", pkg],
                        capture_output=True, text=True, timeout=60,
                    )
                    if r.returncode == 0:
                        updated.append(pkg)
                    else:
                        failed.append(pkg)
                except Exception:
                    failed.append(pkg)
            msg_parts = []
            if updated:
                msg_parts.append(f"Updated: {', '.join(updated)}")
            if failed:
                msg_parts.append(f"Failed: {', '.join(failed)}")
            return {
                "status": "success",
                "message": "; ".join(msg_parts) if msg_parts else "No updates needed",
                "updated_count": len(updated),
                "failed_count": len(failed),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def scrape_knowledge(self, topic: str) -> Dict[str, Any]:
        """Scrape the web for latest information on a topic and store it."""
        if not _HAS_REQUESTS:
            return {"status": "error", "message": "requests library required: pip install requests"}
        if not _HAS_BS4:
            return {"status": "error", "message": "beautifulsoup4 required: pip install beautifulsoup4"}
        results = []
        queries = [
            f"{topic} latest 2026",
            f"{topic} new features",
            f"{topic} updates",
            f"{topic} tutorial",
        ]
        for query in queries[:2]:
            try:
                url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    snippets = []
                    for div in soup.select("div[data-sokoban-container]"):
                        text = div.get_text(strip=True)
                        if text and len(text) > 50:
                            snippets.append(text[:300])
                    for result_div in soup.select(".g"):
                        text = result_div.get_text(strip=True)
                        if text and len(text) > 50:
                            snippets.append(text[:300])
                    if snippets:
                        results.append({"query": query, "snippets": snippets[:3]})
            except Exception:
                continue
        if results:
            knowledge_file = os.path.join(
                self._update_knowledge_dir,
                f"{topic.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.json",
            )
            with open(knowledge_file, "w", encoding="utf-8") as f:
                json.dump({"topic": topic, "scraped_at": datetime.now().isoformat(), "results": results}, f, indent=2)
            return {
                "status": "success",
                "message": f"Knowledge scraped for '{topic}' — {len(results)} sources",
                "file": knowledge_file,
                "results": results,
            }
        return {"status": "no_results", "message": f"No results found for '{topic}'"}

    def fetch_trending_repos(self) -> Dict[str, Any]:
        """Fetch trending GitHub repositories."""
        if not _HAS_REQUESTS:
            return {"status": "error", "message": "requests library required"}
        try:
            resp = requests.get("https://api.github.com/search/repositories?q=created:>2026-01-01&sort=stars&order=desc&per_page=10",
                                headers={"Accept": "application/vnd.github.v3+json"}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                repos = []
                for item in data.get("items", [])[:10]:
                    repos.append({
                        "name": item["full_name"],
                        "stars": item["stargazers_count"],
                        "description": item.get("description", "")[:100],
                        "url": item["html_url"],
                    })
                return {"status": "success", "repos": repos, "count": len(repos)}
            return {"status": "error", "message": f"GitHub API returned {resp.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def full_update(self) -> Dict[str, Any]:
        """Run all update checks and return a comprehensive report."""
        results = {}
        results["git"] = self.check_git_updates()
        if results["git"].get("status") == "updates_available":
            results["git_pull"] = self.pull_updates()
        results["pip"] = self.update_pip_packages()
        news = self.fetch_trending_repos()
        if news["status"] == "success":
            results["trending_repos"] = news
        self._log_update(results)
        return results

    def _log_update(self, result: Dict):
        """Log the update to a history file."""
        try:
            history = []
            if os.path.exists(self.update_log):
                with open(self.update_log, "r", encoding="utf-8") as f:
                    history = json.load(f)
            history.append({
                "timestamp": datetime.now().isoformat(),
                "result": result,
            })
            history = history[-20:]
            with open(self.update_log, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception:
            pass

    def get_update_history(self) -> List[Dict]:
        """Get the last N update records."""
        try:
            if os.path.exists(self.update_log):
                with open(self.update_log, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def start_background_check(self, interval_hours: int = 24) -> Dict[str, Any]:
        """Start a background thread that periodically checks for updates."""
        import threading
        def _check_loop():
            while True:
                result = self.full_update()
                log_file = os.path.join(self.project_dir, "tom_logs", "background_update_log.txt")
                try:
                    with open(log_file, "a") as f:
                        f.write(f"{datetime.now().isoformat()}: {json.dumps(result, default=str)[:200]}\n")
                except Exception:
                    pass
                time.sleep(interval_hours * 3600)
        t = threading.Thread(target=_check_loop, daemon=True)
        t.start()
        return {"status": "success", "message": f"Background update check every {interval_hours}h started"}

    def auto_research(self, topic: str) -> Dict[str, Any]:
        """Research a topic by combining web scraping, LLM knowledge, and saved knowledge."""
        result = self.scrape_knowledge(topic)
        if result["status"] == "success":
            return result
        return {"status": "info", "message": f"No new web data for '{topic}'"}

    def get_stats(self) -> Dict[str, Any]:
        """Get update system statistics."""
        history = self.get_update_history()
        return {
            "total_updates": len(history),
            "last_update": history[-1]["timestamp"][:19] if history else "never",
            "git_status": self.check_git_updates().get("status", "unknown"),
            "knowledge_dir": self._update_knowledge_dir,
            "background_active": len(history) > 0,
        }
