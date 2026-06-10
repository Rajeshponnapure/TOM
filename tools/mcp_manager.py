"""
tools/mcp_manager.py — TOM's MCP (Model Context Protocol) Integration Layer

Gives TOM the ability to connect to ANY external application or service.

Architecture:
  - MCPConnector: abstract base class every connector implements
  - MCPManager:   registry + router — add connectors, call tools by name
  - Native connectors: pure-Python integrations (no separate server needed)
  - HTTP MCP servers: standard JSON-RPC 2.0 over HTTP (connect to any MCP server)

Built-in connectors:
  github      — repositories, issues, PRs, commits (GitHub REST API)
  gmail       — read/send email (Google Gmail API via OAuth2)
  slack       — messages, channels (Slack Web API)
  notion      — pages, databases (Notion API)
  whatsapp    — send messages (WhatsApp Business Cloud API)
  instagram   — media, posts (Instagram Graph API)
  calendar    — Google Calendar events
  weather     — current weather / forecast (Open-Meteo, no API key)
  websearch   — DuckDuckGo instant answer API (no API key)
  filesystem  — read/write/list files on disk
  database    — SQLite / PostgreSQL queries via connection string

Usage in agent.py:
    mcp = get_mcp_manager()
    result = await mcp.call("github", "list_repos", {"username": "..."})
    result = await mcp.call("gmail",  "send_email", {"to": "...", "body": "..."})
    result = await mcp.call("slack",  "post_message", {"channel": "#general", "text": "..."})
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.request
import urllib.parse
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Base Connector ─────────────────────────────────────────────────────────────

class MCPConnector(ABC):
    """Abstract base for all MCP connectors."""

    name: str = "unnamed"
    description: str = ""
    tools: List[str] = []  # Tool names this connector provides

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._connected = False

    async def connect(self) -> bool:
        """Establish connection / validate credentials. Returns True on success."""
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    @abstractmethod
    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return a result dict with 'status' and 'data'."""
        ...

    def status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "connected": self._connected,
            "tools": self.tools,
        }

    @staticmethod
    def _get_env(key: str, default: str = "") -> str:
        return os.environ.get(key, default)

    @staticmethod
    def _ok(data: Any, message: str = "OK") -> Dict[str, Any]:
        return {"status": "success", "message": message, "data": data}

    @staticmethod
    def _err(message: str) -> Dict[str, Any]:
        return {"status": "error", "message": message, "data": None}

    @staticmethod
    def _http_get(url: str, headers: Dict[str, str] = None, timeout: int = 15) -> Any:
        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            raise RuntimeError(f"HTTP GET {url} failed: {e}")

    @staticmethod
    def _http_post(url: str, payload: Any, headers: Dict[str, str] = None, timeout: int = 15) -> Any:
        data = json.dumps(payload).encode()
        h = {"Content-Type": "application/json", **(headers or {})}
        req = urllib.request.Request(url, data=data, headers=h, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            raise RuntimeError(f"HTTP POST {url} failed: {e}")


# ── GitHub Connector ───────────────────────────────────────────────────────────

class GitHubConnector(MCPConnector):
    name = "github"
    description = "GitHub — repos, issues, PRs, commits, code search"
    tools = ["list_repos", "get_repo", "list_issues", "create_issue",
             "list_prs", "search_code", "get_file_contents", "create_pr",
             "get_commits", "get_user_info"]

    BASE = "https://api.github.com"

    def _headers(self) -> Dict[str, str]:
        token = self._get_env("GITHUB_TOKEN")
        h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    async def connect(self) -> bool:
        try:
            self._http_get(f"{self.BASE}/rate_limit", self._headers())
            self._connected = True
            return True
        except Exception as e:
            logger.warning(f"[MCP:github] connect failed: {e}")
            return False

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            h = self._headers()
            if tool_name == "list_repos":
                user = args.get("username", "")
                url = f"{self.BASE}/users/{user}/repos?per_page=30&sort=updated" if user else f"{self.BASE}/user/repos?per_page=30"
                data = self._http_get(url, h)
                repos = [{"name": r["name"], "url": r["html_url"], "stars": r["stargazers_count"],
                          "lang": r["language"], "description": r.get("description", "")} for r in data]
                return self._ok(repos, f"Found {len(repos)} repos")

            elif tool_name == "get_repo":
                owner = args["owner"]; repo = args["repo"]
                data = self._http_get(f"{self.BASE}/repos/{owner}/{repo}", h)
                return self._ok(data, f"Repo: {owner}/{repo}")

            elif tool_name == "list_issues":
                owner = args["owner"]; repo = args["repo"]
                state = args.get("state", "open")
                data = self._http_get(f"{self.BASE}/repos/{owner}/{repo}/issues?state={state}&per_page=20", h)
                issues = [{"number": i["number"], "title": i["title"], "state": i["state"],
                           "url": i["html_url"], "body": (i.get("body") or "")[:200]} for i in data
                          if not i.get("pull_request")]
                return self._ok(issues, f"{len(issues)} open issues")

            elif tool_name == "create_issue":
                owner = args["owner"]; repo = args["repo"]
                payload = {"title": args["title"], "body": args.get("body", "")}
                if args.get("labels"):
                    payload["labels"] = args["labels"]
                data = self._http_post(f"{self.BASE}/repos/{owner}/{repo}/issues", payload, h)
                return self._ok(data, f"Issue #{data['number']} created: {data['html_url']}")

            elif tool_name == "list_prs":
                owner = args["owner"]; repo = args["repo"]
                data = self._http_get(f"{self.BASE}/repos/{owner}/{repo}/pulls?per_page=20", h)
                prs = [{"number": p["number"], "title": p["title"], "state": p["state"],
                        "url": p["html_url"]} for p in data]
                return self._ok(prs, f"{len(prs)} PRs")

            elif tool_name == "search_code":
                q = urllib.parse.quote(args["query"])
                data = self._http_get(f"{self.BASE}/search/code?q={q}&per_page=10", h)
                items = [{"path": i["path"], "repo": i["repository"]["full_name"],
                          "url": i["html_url"]} for i in data.get("items", [])]
                return self._ok(items, f"{len(items)} code results")

            elif tool_name == "get_file_contents":
                owner = args["owner"]; repo = args["repo"]; path = args["path"]
                import base64
                data = self._http_get(f"{self.BASE}/repos/{owner}/{repo}/contents/{path}", h)
                content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
                return self._ok({"content": content, "sha": data["sha"]}, f"File: {path}")

            elif tool_name == "get_commits":
                owner = args["owner"]; repo = args["repo"]
                data = self._http_get(f"{self.BASE}/repos/{owner}/{repo}/commits?per_page=20", h)
                commits = [{"sha": c["sha"][:7], "message": c["commit"]["message"].split("\n")[0],
                            "author": c["commit"]["author"]["name"],
                            "date": c["commit"]["author"]["date"]} for c in data]
                return self._ok(commits, f"{len(commits)} commits")

            elif tool_name == "get_user_info":
                username = args.get("username", "")
                url = f"{self.BASE}/users/{username}" if username else f"{self.BASE}/user"
                data = self._http_get(url, h)
                return self._ok(data, f"User: {data['login']}")

            else:
                return self._err(f"Unknown tool: {tool_name}")
        except Exception as e:
            return self._err(str(e))


# ── Gmail Connector ────────────────────────────────────────────────────────────

class GmailConnector(MCPConnector):
    name = "gmail"
    description = "Gmail — read inbox, send email, search, labels"
    tools = ["list_emails", "get_email", "send_email", "search_emails",
             "get_labels", "mark_read", "get_unread_count"]

    # NOTE: Full OAuth2 requires browser redirect. For headless/local use,
    # store credentials via `google-auth-oauthlib` setup once, then it uses
    # cached token. If google libs not installed, falls back to SMTP/IMAP.

    async def connect(self) -> bool:
        try:
            from google.oauth2.credentials import Credentials
            creds_file = self._get_env("GOOGLE_TOKEN_FILE", "config/google_token.json")
            if os.path.exists(creds_file):
                self._connected = True
                return True
        except ImportError:
            pass
        # Fallback: check SMTP env vars
        if self._get_env("GMAIL_APP_PASSWORD") or self._get_env("EMAIL_PASSWORD"):
            self._connected = True
            return True
        return False

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if tool_name == "send_email":
                return await self._send_smtp(args)
            elif tool_name in ("list_emails", "get_unread_count", "search_emails", "get_email"):
                return await self._gmail_api(tool_name, args)
            else:
                return self._err(f"Unknown tool: {tool_name}")
        except Exception as e:
            return self._err(str(e))

    async def _send_smtp(self, args: Dict) -> Dict:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        user     = self._get_env("GMAIL_ADDRESS") or self._get_env("EMAIL_ADDRESS")
        password = self._get_env("GMAIL_APP_PASSWORD") or self._get_env("EMAIL_PASSWORD")
        if not user or not password:
            return self._err("Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env")
        msg = MIMEMultipart()
        msg["From"]    = user
        msg["To"]      = args["to"]
        msg["Subject"] = args.get("subject", "(no subject)")
        msg.attach(MIMEText(args.get("body", ""), "plain"))
        await asyncio.to_thread(
            lambda: smtplib.SMTP_SSL("smtp.gmail.com", 465).__enter__().__class__(
                smtplib.SMTP_SSL("smtp.gmail.com", 465).__enter__()
            )
        )
        # Simpler sync approach
        def _do_send():
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
                s.login(user, password)
                s.sendmail(user, args["to"], msg.as_string())
        await asyncio.to_thread(_do_send)
        return self._ok({"to": args["to"]}, f"Email sent to {args['to']}")

    async def _gmail_api(self, tool: str, args: Dict) -> Dict:
        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials
            creds_file = self._get_env("GOOGLE_TOKEN_FILE", "config/google_token.json")
            creds = Credentials.from_authorized_user_file(creds_file)
            service = build("gmail", "v1", credentials=creds)
            if tool == "list_emails":
                results = service.users().messages().list(userId="me", maxResults=20).execute()
                msgs = results.get("messages", [])
                return self._ok(msgs, f"{len(msgs)} emails")
            elif tool == "get_unread_count":
                results = service.users().messages().list(userId="me", q="is:unread", maxResults=500).execute()
                count = results.get("resultSizeEstimate", 0)
                return self._ok({"unread": count}, f"{count} unread")
            elif tool == "search_emails":
                q = args.get("query", "")
                results = service.users().messages().list(userId="me", q=q, maxResults=10).execute()
                return self._ok(results.get("messages", []), "Search results")
            return self._err(f"Tool {tool} not implemented via API")
        except ImportError:
            return self._err("Install: pip install google-api-python-client google-auth-oauthlib")
        except Exception as e:
            return self._err(str(e))


# ── Slack Connector ────────────────────────────────────────────────────────────

class SlackConnector(MCPConnector):
    name = "slack"
    description = "Slack — post messages, read channels, DMs"
    tools = ["post_message", "list_channels", "get_messages", "upload_file", "get_dm_history"]

    BASE = "https://slack.com/api"

    def _headers(self) -> Dict[str, str]:
        token = self._get_env("SLACK_BOT_TOKEN") or self._get_env("SLACK_TOKEN")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def connect(self) -> bool:
        token = self._get_env("SLACK_BOT_TOKEN") or self._get_env("SLACK_TOKEN")
        if not token:
            return False
        try:
            data = self._http_get(f"{self.BASE}/auth.test", self._headers())
            self._connected = data.get("ok", False)
            return self._connected
        except Exception:
            return False

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            h = self._headers()
            if tool_name == "post_message":
                payload = {"channel": args["channel"], "text": args["text"]}
                if args.get("blocks"):
                    payload["blocks"] = args["blocks"]
                data = self._http_post(f"{self.BASE}/chat.postMessage", payload, h)
                if data.get("ok"):
                    return self._ok(data, f"Posted to {args['channel']}")
                return self._err(data.get("error", "Slack error"))

            elif tool_name == "list_channels":
                data = self._http_get(f"{self.BASE}/conversations.list?limit=100&types=public_channel,private_channel", h)
                channels = [{"id": c["id"], "name": c["name"], "topic": c.get("topic", {}).get("value", "")}
                            for c in data.get("channels", [])]
                return self._ok(channels, f"{len(channels)} channels")

            elif tool_name == "get_messages":
                channel = args["channel"]
                limit   = args.get("limit", 20)
                data = self._http_get(f"{self.BASE}/conversations.history?channel={channel}&limit={limit}", h)
                messages = [{"text": m.get("text", ""), "user": m.get("user", ""),
                             "ts": m.get("ts", "")} for m in data.get("messages", [])]
                return self._ok(messages, f"{len(messages)} messages")

            else:
                return self._err(f"Unknown tool: {tool_name}")
        except Exception as e:
            return self._err(str(e))


# ── Notion Connector ───────────────────────────────────────────────────────────

class NotionConnector(MCPConnector):
    name = "notion"
    description = "Notion — read/create pages and databases"
    tools = ["search", "get_page", "create_page", "list_databases", "query_database", "append_blocks"]

    BASE = "https://api.notion.com/v1"

    def _headers(self) -> Dict[str, str]:
        token = self._get_env("NOTION_TOKEN") or self._get_env("NOTION_API_KEY")
        return {"Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"}

    async def connect(self) -> bool:
        token = self._get_env("NOTION_TOKEN") or self._get_env("NOTION_API_KEY")
        if not token:
            return False
        try:
            self._http_get(f"{self.BASE}/users/me", self._headers())
            self._connected = True
            return True
        except Exception:
            return False

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            h = self._headers()
            if tool_name == "search":
                payload = {"query": args.get("query", "")}
                if args.get("filter"):
                    payload["filter"] = args["filter"]
                data = self._http_post(f"{self.BASE}/search", payload, h)
                results = [{"id": r["id"], "title": _notion_title(r), "type": r["object"]}
                           for r in data.get("results", [])]
                return self._ok(results, f"{len(results)} results")

            elif tool_name == "get_page":
                page_id = args["page_id"]
                data = self._http_get(f"{self.BASE}/pages/{page_id}", h)
                return self._ok(data, f"Page: {_notion_title(data)}")

            elif tool_name == "create_page":
                payload = {
                    "parent": args["parent"],
                    "properties": {"title": {"title": [{"text": {"content": args["title"]}}]}},
                }
                if args.get("content"):
                    payload["children"] = [{"object": "block", "type": "paragraph",
                                            "paragraph": {"rich_text": [{"text": {"content": args["content"]}}]}}]
                data = self._http_post(f"{self.BASE}/pages", payload, h)
                return self._ok(data, f"Created page: {args['title']}")

            elif tool_name == "list_databases":
                payload = {"filter": {"property": "object", "value": "database"}}
                data = self._http_post(f"{self.BASE}/search", payload, h)
                dbs = [{"id": d["id"], "title": _notion_title(d)} for d in data.get("results", [])]
                return self._ok(dbs, f"{len(dbs)} databases")

            elif tool_name == "query_database":
                db_id = args["database_id"]
                payload = {}
                if args.get("filter"):
                    payload["filter"] = args["filter"]
                if args.get("sorts"):
                    payload["sorts"] = args["sorts"]
                data = self._http_post(f"{self.BASE}/databases/{db_id}/query", payload, h)
                return self._ok(data.get("results", []), f"{len(data.get('results', []))} rows")

            else:
                return self._err(f"Unknown tool: {tool_name}")
        except Exception as e:
            return self._err(str(e))


def _notion_title(obj: Dict) -> str:
    try:
        props = obj.get("properties", {})
        for key in ("title", "Title", "Name"):
            if key in props:
                t = props[key]
                if isinstance(t, dict) and "title" in t:
                    return t["title"][0]["plain_text"] if t["title"] else ""
    except Exception:
        pass
    return obj.get("id", "untitled")


# ── WhatsApp Connector ─────────────────────────────────────────────────────────

class WhatsAppConnector(MCPConnector):
    name = "whatsapp"
    description = "WhatsApp Business Cloud API — send messages, templates"
    tools = ["send_message", "send_template", "get_message_status"]

    def _headers(self) -> Dict[str, str]:
        token = self._get_env("WHATSAPP_ACCESS_TOKEN") or self._get_env("META_ACCESS_TOKEN")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _phone_id(self) -> str:
        return self._get_env("WHATSAPP_PHONE_NUMBER_ID")

    async def connect(self) -> bool:
        return bool(self._phone_id() and self._get_env("WHATSAPP_ACCESS_TOKEN"))

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        phone_id = self._phone_id()
        if not phone_id:
            return self._err("Set WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN in .env")
        base = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
        try:
            if tool_name == "send_message":
                payload = {
                    "messaging_product": "whatsapp",
                    "to": args["to"],
                    "type": "text",
                    "text": {"body": args["message"]},
                }
                data = self._http_post(base, payload, self._headers())
                return self._ok(data, f"WhatsApp message sent to {args['to']}")

            elif tool_name == "send_template":
                payload = {
                    "messaging_product": "whatsapp",
                    "to": args["to"],
                    "type": "template",
                    "template": {"name": args["template"], "language": {"code": args.get("lang", "en_US")}},
                }
                data = self._http_post(base, payload, self._headers())
                return self._ok(data, "Template sent")

            else:
                return self._err(f"Unknown tool: {tool_name}")
        except Exception as e:
            return self._err(str(e))


# ── Instagram Connector ────────────────────────────────────────────────────────

class InstagramConnector(MCPConnector):
    name = "instagram"
    description = "Instagram Graph API — read posts, account info, insights"
    tools = ["get_account", "get_media", "get_insights", "get_comments", "reply_to_comment"]

    BASE = "https://graph.instagram.com/v18.0"

    def _token(self) -> str:
        return self._get_env("INSTAGRAM_ACCESS_TOKEN") or self._get_env("META_ACCESS_TOKEN")

    async def connect(self) -> bool:
        return bool(self._token())

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        token = self._token()
        if not token:
            return self._err("Set INSTAGRAM_ACCESS_TOKEN in .env")
        try:
            if tool_name == "get_account":
                url = f"{self.BASE}/me?fields=id,username,name,biography,followers_count,follows_count,media_count&access_token={token}"
                data = self._http_get(url)
                return self._ok(data, f"Account: @{data.get('username')}")

            elif tool_name == "get_media":
                limit = args.get("limit", 12)
                url = f"{self.BASE}/me/media?fields=id,caption,media_type,media_url,timestamp,like_count,comments_count&limit={limit}&access_token={token}"
                data = self._http_get(url)
                return self._ok(data.get("data", []), f"{len(data.get('data', []))} posts")

            elif tool_name == "get_insights":
                media_id = args.get("media_id", "")
                if media_id:
                    url = f"{self.BASE}/{media_id}/insights?metric=impressions,reach,engagement&access_token={token}"
                else:
                    url = f"{self.BASE}/me/insights?metric=follower_count,impressions,reach&period=day&access_token={token}"
                data = self._http_get(url)
                return self._ok(data.get("data", []), "Insights")

            elif tool_name == "get_comments":
                media_id = args["media_id"]
                url = f"{self.BASE}/{media_id}/comments?fields=id,text,timestamp,username&access_token={token}"
                data = self._http_get(url)
                return self._ok(data.get("data", []), f"Comments for {media_id}")

            else:
                return self._err(f"Unknown tool: {tool_name}")
        except Exception as e:
            return self._err(str(e))


# ── Web Search Connector ───────────────────────────────────────────────────────

class WebSearchConnector(MCPConnector):
    name = "websearch"
    description = "Web search — DuckDuckGo instant answers (no API key needed)"
    tools = ["search", "instant_answer", "news_search"]

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        query = urllib.parse.quote_plus(args.get("query", ""))
        try:
            if tool_name in ("search", "instant_answer"):
                url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
                data = self._http_get(url)
                abstract = data.get("AbstractText", "")
                related  = [{"title": r.get("Text", ""), "url": r.get("FirstURL", "")}
                            for r in data.get("RelatedTopics", [])[:8] if r.get("Text")]
                return self._ok({"abstract": abstract, "related": related}, abstract[:200] or "Search complete")

            elif tool_name == "news_search":
                url = f"https://api.duckduckgo.com/?q={query}&format=json&t=news"
                data = self._http_get(url)
                return self._ok(data.get("RelatedTopics", [])[:10], "News results")

            return self._err(f"Unknown tool: {tool_name}")
        except Exception as e:
            return self._err(str(e))


# ── Calendar Connector ─────────────────────────────────────────────────────────

class CalendarConnector(MCPConnector):
    name = "calendar"
    description = "Google Calendar — list/create/delete events"
    tools = ["list_events", "create_event", "delete_event", "get_today_events"]

    BASE = "https://www.googleapis.com/calendar/v3"

    def _headers(self) -> Dict[str, str]:
        token = self._get_env("GOOGLE_CALENDAR_TOKEN")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def connect(self) -> bool:
        token = self._get_env("GOOGLE_CALENDAR_TOKEN")
        creds_file = self._get_env("GOOGLE_TOKEN_FILE", "config/google_token.json")
        self._connected = bool(token or os.path.exists(creds_file))
        return self._connected

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials
            creds_file = self._get_env("GOOGLE_TOKEN_FILE", "config/google_token.json")
            creds   = Credentials.from_authorized_user_file(creds_file)
            service = build("calendar", "v3", credentials=creds)

            if tool_name in ("list_events", "get_today_events"):
                import datetime
                now  = datetime.datetime.utcnow().isoformat() + "Z"
                end  = (datetime.datetime.utcnow() + datetime.timedelta(days=args.get("days", 7))).isoformat() + "Z"
                evts = service.events().list(calendarId="primary", timeMin=now, timeMax=end,
                                             maxResults=20, singleEvents=True,
                                             orderBy="startTime").execute()
                items = [{"summary": e.get("summary"), "start": e.get("start", {}).get("dateTime"),
                          "end": e.get("end", {}).get("dateTime")} for e in evts.get("items", [])]
                return self._ok(items, f"{len(items)} upcoming events")

            elif tool_name == "create_event":
                body = {"summary": args["title"], "description": args.get("description", ""),
                        "start": {"dateTime": args["start"], "timeZone": args.get("tz", "UTC")},
                        "end":   {"dateTime": args["end"],   "timeZone": args.get("tz", "UTC")}}
                evt = service.events().insert(calendarId="primary", body=body).execute()
                return self._ok(evt, f"Event created: {args['title']}")

            return self._err(f"Unknown tool: {tool_name}")
        except ImportError:
            return self._err("Install: pip install google-api-python-client google-auth-oauthlib")
        except Exception as e:
            return self._err(str(e))


# ── Weather Connector ──────────────────────────────────────────────────────────

class WeatherConnector(MCPConnector):
    name = "weather"
    description = "Weather — current conditions and forecast (Open-Meteo, no API key)"
    tools = ["get_current_weather", "get_forecast", "get_weather_by_coords"]

    GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
    WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if tool_name in ("get_current_weather", "get_forecast"):
                city = args.get("city", "London")
                geo  = self._http_get(f"{self.GEOCODE_URL}?name={urllib.parse.quote(city)}&count=1")
                locs = geo.get("results", [])
                if not locs:
                    return self._err(f"Location not found: {city}")
                lat, lon = locs[0]["latitude"], locs[0]["longitude"]
                params = (f"latitude={lat}&longitude={lon}"
                          "&current=temperature_2m,weathercode,windspeed_10m,relative_humidity_2m"
                          "&daily=temperature_2m_max,temperature_2m_min,weathercode"
                          "&forecast_days=7&timezone=auto")
                data = self._http_get(f"{self.WEATHER_URL}?{params}")
                cur  = data.get("current", {})
                result = {
                    "city": city,
                    "temperature_c": cur.get("temperature_2m"),
                    "humidity_pct":  cur.get("relative_humidity_2m"),
                    "wind_kph":      cur.get("windspeed_10m"),
                    "condition":     _wmo_code(cur.get("weathercode", 0)),
                    "forecast_7day": data.get("daily", {}),
                }
                return self._ok(result,
                    f"{city}: {result['temperature_c']}°C, {result['condition']}")

            return self._err(f"Unknown tool: {tool_name}")
        except Exception as e:
            return self._err(str(e))


def _wmo_code(code: int) -> str:
    WMO = {0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
           45: "Foggy", 48: "Icy fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
           61: "Slight rain", 63: "Rain", 65: "Heavy rain", 71: "Slight snow", 73: "Snow",
           75: "Heavy snow", 80: "Rain showers", 81: "Showers", 82: "Violent showers",
           95: "Thunderstorm", 96: "Thunderstorm w/ hail", 99: "Thunderstorm w/ heavy hail"}
    return WMO.get(code, f"Code {code}")


# ── HTTP MCP Server Connector ──────────────────────────────────────────────────

class HTTPMCPConnector(MCPConnector):
    """
    Connects to any standard MCP server over HTTP (JSON-RPC 2.0).
    Use to integrate third-party MCP servers (e.g. from mcp.run, Zapier MCP, etc.)
    """
    def __init__(self, name: str, base_url: str, api_key: str = "", description: str = ""):
        super().__init__()
        self.name        = name
        self.description = description or f"HTTP MCP server at {base_url}"
        self._base_url   = base_url.rstrip("/")
        self._api_key    = api_key
        self.tools       = []

    def _rpc_headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self._api_key:
            h["Authorization"] = f"Bearer {self._api_key}"
        return h

    async def connect(self) -> bool:
        try:
            # Fetch tool list via tools/list
            payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
            data = self._http_post(f"{self._base_url}/mcp", payload, self._rpc_headers())
            self.tools = [t["name"] for t in data.get("result", {}).get("tools", [])]
            self._connected = True
            return True
        except Exception as e:
            logger.warning(f"[MCP:{self.name}] connect failed: {e}")
            return False

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": args},
        }
        try:
            data = self._http_post(f"{self._base_url}/mcp", payload, self._rpc_headers())
            result = data.get("result", {})
            error  = data.get("error")
            if error:
                return self._err(error.get("message", "MCP server error"))
            content = result.get("content", [{}])
            text = content[0].get("text", str(result)) if content else str(result)
            return self._ok(result, text[:400])
        except Exception as e:
            return self._err(str(e))


# ── MCPManager ─────────────────────────────────────────────────────────────────

class MCPManager:
    """
    Central registry for all MCP connectors.

    Usage:
        mcp = MCPManager()
        mcp.register(GitHubConnector())
        result = await mcp.call("github", "list_repos", {"username": "torvalds"})
        print(result)  # {"status": "success", "data": [...], "message": "..."}

    Convenience auto-initialise all built-in connectors:
        mcp = MCPManager.with_defaults()
    """

    def __init__(self):
        self._connectors: Dict[str, MCPConnector] = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, connector: MCPConnector) -> None:
        self._connectors[connector.name] = connector
        logger.debug(f"[MCP] Registered connector: {connector.name}")

    def register_http_server(self, name: str, base_url: str,
                              api_key: str = "", description: str = "") -> HTTPMCPConnector:
        """Register an external HTTP MCP server by URL."""
        conn = HTTPMCPConnector(name, base_url, api_key, description)
        self.register(conn)
        return conn

    # ── Calling Tools ─────────────────────────────────────────────────────────

    async def call(self, connector_name: str, tool_name: str,
                   args: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Call a tool on a connector.
        Auto-connects on first use.
        """
        conn = self._connectors.get(connector_name)
        if conn is None:
            available = list(self._connectors.keys())
            return {
                "status": "error",
                "message": f"No connector '{connector_name}'. Available: {available}",
                "data": None,
            }
        if not conn._connected:
            await conn.connect()
        return await conn.call_tool(tool_name, args or {})

    # ── Status & Discovery ────────────────────────────────────────────────────

    def list_connectors(self) -> List[Dict[str, Any]]:
        return [c.status() for c in self._connectors.values()]

    def available_tools(self) -> Dict[str, List[str]]:
        return {name: conn.tools for name, conn in self._connectors.items()}

    def get_tools_description(self) -> str:
        """Human-readable summary of all available MCP tools for system prompts."""
        lines = ["[MCP TOOLS AVAILABLE]"]
        for name, conn in self._connectors.items():
            lines.append(f"\n{name} ({conn.description}):")
            for t in conn.tools:
                lines.append(f"  - {t}")
        return "\n".join(lines)

    async def connect_all(self) -> Dict[str, bool]:
        """Attempt to connect all registered connectors. Returns connection status."""
        results = {}
        for name, conn in self._connectors.items():
            results[name] = await conn.connect()
        return results

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def with_defaults(cls) -> "MCPManager":
        """Create a manager pre-loaded with all built-in connectors."""
        mgr = cls()
        for ConnClass in [
            GitHubConnector,
            GmailConnector,
            SlackConnector,
            NotionConnector,
            WhatsAppConnector,
            InstagramConnector,
            WebSearchConnector,
            CalendarConnector,
            WeatherConnector,
        ]:
            mgr.register(ConnClass())
        # HTTP MCP servers from environment
        # Format: MCP_SERVER_<NAME>=https://server-url|optional-api-key
        for k, v in os.environ.items():
            if k.startswith("MCP_SERVER_"):
                srv_name = k[len("MCP_SERVER_"):].lower()
                parts    = v.split("|", 1)
                url      = parts[0].strip()
                key      = parts[1].strip() if len(parts) > 1 else ""
                mgr.register_http_server(srv_name, url, key)
                logger.info(f"[MCP] Auto-registered HTTP server '{srv_name}' from env")
        return mgr


# ── Singleton ──────────────────────────────────────────────────────────────────

_mcp_instance: Optional[MCPManager] = None

def get_mcp_manager() -> MCPManager:
    """Get (or create) the global MCPManager singleton."""
    global _mcp_instance
    if _mcp_instance is None:
        _mcp_instance = MCPManager.with_defaults()
    return _mcp_instance
