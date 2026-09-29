"""Send chat messages in Slack, Discord and Telegram through their official APIs.

Unlike keyboard automation these calls come back with a confirmation (Slack `ts`,
Discord message `id`, Telegram `message_id`), so TOM reports "sent" only when the
service says it accepted the message.

Configuration (.env):
  Slack     SLACK_BOT_TOKEN                     target: #channel, @name / person name (needs users:read)
  Discord   DISCORD_WEBHOOK_URL                 default channel
            DISCORD_WEBHOOKS='{"dev": "https://discord.com/api/webhooks/..."}'   named channels
  Telegram  TELEGRAM_BOT_TOKEN
            TELEGRAM_CHATS='{"Ravi": 123456789, "team": "@teamchannel"}'         names -> chat id
Discord webhooks post to channels (not DMs); a Telegram bot can only message chats that
have started it or channels it belongs to.
"""
import asyncio
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

SETUP_HINTS = {
    "slack": "Set SLACK_BOT_TOKEN in .env (a bot token with chat:write; users:read to message people by name).",
    "discord": "Set DISCORD_WEBHOOK_URL (or DISCORD_WEBHOOKS='{\"name\": \"url\"}') in .env - "
               "create one under Channel Settings > Integrations > Webhooks.",
    "telegram": "Set TELEGRAM_BOT_TOKEN in .env (from @BotFather) and TELEGRAM_CHATS='{\"Name\": chat_id}'.",
}
MAX_LENGTH = {"slack": 40000, "discord": 2000, "telegram": 4096}


def _json_env(name: str) -> Dict[str, Any]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def _request(url: str, payload: Optional[dict] = None, headers: Optional[dict] = None,
             method: Optional[str] = None, timeout: int = 20) -> Dict[str, Any]:
    """HTTP call returning {'http': status, 'json': body-or-None}. HTTP errors are data, not exceptions."""
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method or ("POST" if data is not None else "GET"),
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            status = resp.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read().decode("utf-8", "replace"), exc.code
    except Exception as exc:                       # DNS failure, refused connection, timeout ...
        return {"http": 0, "json": None, "error": str(exc)}
    try:
        return {"http": status, "json": json.loads(raw) if raw.strip() else None}
    except ValueError:
        return {"http": status, "json": None}


class ChatApps:
    def missing_setup(self, app: str) -> str:
        """'' when the app can be used, else what to configure."""
        if app == "slack":
            ok = bool(os.environ.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_TOKEN"))
        elif app == "discord":
            ok = bool(os.environ.get("DISCORD_WEBHOOK_URL") or _json_env("DISCORD_WEBHOOKS"))
        elif app == "telegram":
            ok = bool(os.environ.get("TELEGRAM_BOT_TOKEN"))
        else:
            return f"'{app}' is not supported."
        return "" if ok else SETUP_HINTS[app]

    async def send(self, app: str, target: str, message: str) -> Dict[str, Any]:
        problem = self.missing_setup(app)
        if problem:
            return {"status": "unsupported", "sent": False, "message": problem}
        if not (message or "").strip():
            return {"status": "error", "sent": False, "message": "There is no message text to send."}
        if len(message) > MAX_LENGTH[app]:
            return {"status": "error", "sent": False,
                    "message": f"That message is {len(message)} characters; {app.title()} allows {MAX_LENGTH[app]}."}
        return await asyncio.to_thread(getattr(self, f"_send_{app}"), target.strip(), message)

    # ── Slack ────────────────────────────────────────────────────────────────
    def _slack_base(self) -> str:
        return os.environ.get("SLACK_API_BASE", "https://slack.com/api").rstrip("/")

    def _slack_headers(self) -> Dict[str, str]:
        token = os.environ.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_TOKEN", "")
        return {"Authorization": f"Bearer {token}"}

    def _slack_find_user(self, name: str) -> Dict[str, Any]:
        wanted = name.lstrip("@").strip().lower()
        matches, cursor = [], ""
        for _ in range(10):                                   # up to 10 pages of members
            query = "limit=200" + (f"&cursor={urllib.parse.quote(cursor)}" if cursor else "")
            res = _request(f"{self._slack_base()}/users.list?{query}", headers=self._slack_headers())
            body = res.get("json") or {}
            if not body.get("ok"):
                return {"error": f"I couldn't look up '{name}' in Slack ({body.get('error') or res.get('error') or res['http']}); "
                                 f"the bot needs the users:read scope, or use @username IDs / #channels."}
            for member in body.get("members", []):
                if member.get("deleted") or member.get("is_bot"):
                    continue
                profile = member.get("profile", {})
                names = {str(member.get("name", "")).lower(), str(member.get("real_name", "")).lower(),
                         str(profile.get("display_name", "")).lower(), str(profile.get("real_name", "")).lower()}
                if wanted in names:
                    matches.append(member)
            cursor = (body.get("response_metadata") or {}).get("next_cursor", "")
            if not cursor:
                break
        if not matches:
            return {"error": f"I couldn't find anyone called '{name}' in Slack."}
        if len(matches) > 1:
            return {"error": f"'{name}' matches {len(matches)} people in Slack; use their exact @username."}
        return {"id": matches[0]["id"], "label": matches[0].get("real_name") or matches[0].get("name")}

    def _send_slack(self, target: str, message: str) -> Dict[str, Any]:
        if not target:
            return {"status": "error", "sent": False, "message": "Tell me the #channel or person to message on Slack."}
        label = target
        if target.startswith("#") or (len(target) > 8 and target[0] in "CGUD" and target.isalnum() and target.isupper()):
            channel = target
        else:
            found = self._slack_find_user(target)
            if found.get("error"):
                return {"status": "error", "sent": False, "message": found["error"]}
            channel, label = found["id"], found["label"]
        res = _request(f"{self._slack_base()}/chat.postMessage", {"channel": channel, "text": message},
                       headers=self._slack_headers())
        body = res.get("json") or {}
        if body.get("ok") and body.get("ts"):
            return {"status": "success", "sent": True, "verified": True, "id": body["ts"], "via": "slack",
                    "message": f"Sent to {label} on Slack (message {body['ts']})."}
        reason = body.get("error") or res.get("error") or f"HTTP {res['http']}"
        hint = {"channel_not_found": " (check the channel name, and invite the bot to it)",
                "not_in_channel": " (invite the bot to that channel first)",
                "invalid_auth": " (the token is wrong)", "not_authed": " (no token)"}.get(reason, "")
        return {"status": "error", "sent": False, "message": f"Slack refused the message: {reason}{hint}."}

    # ── Discord (webhooks) ───────────────────────────────────────────────────
    def _send_discord(self, target: str, message: str) -> Dict[str, Any]:
        named = {k.lower().lstrip("#"): v for k, v in _json_env("DISCORD_WEBHOOKS").items()}
        key = target.lower().lstrip("#")
        default = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
        if key in named:
            url = named[key]
        elif default and key in ("", "general", "channel", "default", "team", "everyone", "the team"):
            url = default
        elif default and not named:
            url = default
        else:
            choices = ", ".join(sorted(named)) or "(none)"
            return {"status": "error", "sent": False,
                    "message": f"Discord webhooks post to channels, and I have none named '{target}'. "
                               f"Configured: {choices}. I can't DM people on Discord."}
        res = _request(url + ("&" if "?" in url else "?") + "wait=true", {"content": message})
        body = res.get("json") or {}
        if res["http"] == 200 and body.get("id"):
            return {"status": "success", "sent": True, "verified": True, "id": body["id"], "via": "discord",
                    "message": f"Posted to Discord channel {target or 'default'} (message {body['id']})."}
        if res["http"] in (200, 204):
            return {"status": "unconfirmed", "sent": True, "via": "discord",
                    "message": "Discord accepted the request but returned no message id."}
        reason = (body.get("message") if isinstance(body, dict) else "") or res.get("error") or f"HTTP {res['http']}"
        return {"status": "error", "sent": False, "message": f"Discord refused the message: {reason}."}

    # ── Telegram (bot API) ───────────────────────────────────────────────────
    def _send_telegram(self, target: str, message: str) -> Dict[str, Any]:
        chats = {k.lower(): v for k, v in _json_env("TELEGRAM_CHATS").items()}
        key = target.lower().lstrip("@")
        if key in chats:
            chat_id = chats[key]
        elif target.lstrip("-").isdigit():
            chat_id = int(target)
        elif target.startswith("@"):
            chat_id = target
        else:
            return {"status": "error", "sent": False,
                    "message": f"I don't have a Telegram chat id for '{target}'. Add it to TELEGRAM_CHATS "
                               f"(e.g. {{\"{target}\": 123456789}}). A bot can only message people who have started it."}
        base = os.environ.get("TELEGRAM_API_BASE", "https://api.telegram.org").rstrip("/")
        res = _request(f"{base}/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
                       {"chat_id": chat_id, "text": message})
        body = res.get("json") or {}
        message_id = (body.get("result") or {}).get("message_id")
        if body.get("ok") and message_id is not None:
            return {"status": "success", "sent": True, "verified": True, "id": message_id, "via": "telegram",
                    "message": f"Sent to {target} on Telegram (message {message_id})."}
        reason = body.get("description") or res.get("error") or f"HTTP {res['http']}"
        return {"status": "error", "sent": False, "message": f"Telegram refused the message: {reason}."}
