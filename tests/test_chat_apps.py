"""Slack / Discord / Telegram sending against a local fake of their HTTP APIs."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from tools.chat_apps import ChatApps

MEMBERS = [
    {"id": "U1", "name": "ravi", "real_name": "Ravi Kumar", "profile": {"display_name": "ravi"}},
    {"id": "U2", "name": "sam.a", "real_name": "Sam", "profile": {"display_name": "Sam"}},
    {"id": "U3", "name": "sam.b", "real_name": "Sam", "profile": {"display_name": "Sam"}},
    {"id": "U4", "name": "gone", "real_name": "Gone Person", "deleted": True, "profile": {}},
]


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _reply(self, code, body=None):
        raw = json.dumps(body).encode() if body is not None else b""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self.server.requests.append(("GET", self.path, None, dict(self.headers)))
        if self.path.startswith("/slack/users.list"):
            if self.headers.get("Authorization") != "Bearer xoxb-good":
                return self._reply(200, {"ok": False, "error": "invalid_auth"})
            if "cursor=page2" in self.path:                       # members are paginated
                return self._reply(200, {"ok": True, "members": MEMBERS[2:], "response_metadata": {"next_cursor": ""}})
            return self._reply(200, {"ok": True, "members": MEMBERS[:2], "response_metadata": {"next_cursor": "page2"}})
        self._reply(404, {})

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        self.server.requests.append(("POST", self.path, payload, dict(self.headers)))
        path = self.path
        if path.startswith("/slack/chat.postMessage"):
            if payload["channel"] == "#nochan":
                return self._reply(200, {"ok": False, "error": "channel_not_found"})
            return self._reply(200, {"ok": True, "ts": "1700000000.000100", "channel": payload["channel"]})
        if path.startswith("/discord/hook"):
            return self._reply(200, {"id": "777", "content": payload["content"]})
        if path.startswith("/discord/nocontent"):
            return self._reply(204)
        if path.startswith("/discord/gone"):
            return self._reply(404, {"message": "Unknown Webhook", "code": 10015})
        if "/sendMessage" in path:
            if payload["chat_id"] == 999:
                return self._reply(400, {"ok": False, "description": "Bad Request: chat not found"})
            return self._reply(200, {"ok": True, "result": {"message_id": 42, "text": payload["text"]}})
        self._reply(404, {})


@pytest.fixture
def api(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), Fake)
    server.requests = []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    for key in ("SLACK_BOT_TOKEN", "SLACK_TOKEN", "DISCORD_WEBHOOK_URL", "DISCORD_WEBHOOKS",
                "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHATS"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("SLACK_API_BASE", base + "/slack")
    monkeypatch.setenv("TELEGRAM_API_BASE", base)
    server.base = base
    yield server
    server.shutdown()
    server.server_close()


def send(app, target, text):
    return asyncio.run(ChatApps().send(app, target, text))


def test_unconfigured_apps_say_what_to_set_and_send_nothing(api):
    for app, needle in (("slack", "SLACK_BOT_TOKEN"), ("discord", "DISCORD_WEBHOOK"), ("telegram", "TELEGRAM_BOT_TOKEN")):
        result = send(app, "x", "hi")
        assert result["status"] == "unsupported" and needle in result["message"]
    assert api.requests == []


# ── Telegram ────────────────────────────────────────────────────────────────
def test_telegram_sends_and_reports_the_message_id(api, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHATS", json.dumps({"Ravi": 555, "team": "@teamchannel"}))
    result = send("telegram", "ravi", "running late")
    assert result["status"] == "success" and result["verified"] and result["id"] == 42, result
    method, path, payload, _ = api.requests[-1]
    assert path == "/bot123:abc/sendMessage" and payload == {"chat_id": 555, "text": "running late"}
    assert send("telegram", "team", "hello")["status"] == "success"
    assert api.requests[-1][2]["chat_id"] == "@teamchannel"


def test_telegram_unknown_name_and_api_errors_are_not_reported_as_sent(api, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHATS", json.dumps({"Ghost": 999}))
    unknown = send("telegram", "Nobody", "hi")
    assert unknown["status"] == "error" and "TELEGRAM_CHATS" in unknown["message"] and api.requests == []
    refused = send("telegram", "Ghost", "hi")
    assert refused["status"] == "error" and refused["sent"] is False and "chat not found" in refused["message"]


# ── Slack ───────────────────────────────────────────────────────────────────
def test_slack_channel_post(api, monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-good")
    result = send("slack", "#dev", "deploy done")
    assert result["status"] == "success" and result["id"] == "1700000000.000100", result
    _, path, payload, headers = api.requests[-1]
    assert path == "/slack/chat.postMessage" and payload == {"channel": "#dev", "text": "deploy done"}
    assert headers["Authorization"] == "Bearer xoxb-good"


def test_slack_person_is_resolved_by_name_across_pages(api, monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-good")
    result = send("slack", "Ravi Kumar", "lunch?")
    assert result["status"] == "success" and "Ravi Kumar" in result["message"]
    assert api.requests[-1][2]["channel"] == "U1"


def test_slack_ambiguous_or_unknown_people_are_never_messaged(api, monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-good")
    ambiguous = send("slack", "Sam", "hi")
    assert ambiguous["status"] == "error" and "2 people" in ambiguous["message"]
    assert send("slack", "Gone Person", "hi")["status"] == "error"          # deactivated account
    assert send("slack", "Zed", "hi")["status"] == "error"
    assert not any(r[1].startswith("/slack/chat.postMessage") for r in api.requests)


def test_slack_errors_are_explained(api, monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-good")
    missing = send("slack", "#nochan", "hi")
    assert missing["status"] == "error" and "channel_not_found" in missing["message"] and "invite" in missing["message"]
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-bad")
    assert "invalid_auth" in send("slack", "Ravi", "hi")["message"]


# ── Discord ─────────────────────────────────────────────────────────────────
def test_discord_named_and_default_webhooks(api, monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOKS", json.dumps({"dev": api.base + "/discord/hook?token=t"}))
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", api.base + "/discord/hook?token=default")
    named = send("discord", "#dev", "build green")
    assert named["status"] == "success" and named["id"] == "777", named
    assert api.requests[-1][1] == "/discord/hook?token=t&wait=true"
    assert api.requests[-1][2] == {"content": "build green"}
    assert send("discord", "team", "hello all")["status"] == "success"
    assert api.requests[-1][1] == "/discord/hook?token=default&wait=true"


def test_discord_cannot_dm_people_and_bad_webhooks_are_errors(api, monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOKS", json.dumps({"dev": api.base + "/discord/hook", "old": api.base + "/discord/gone"}))
    dm = send("discord", "Sam", "hi")
    assert dm["status"] == "error" and "can't DM" in dm["message"] and api.requests == []
    gone = send("discord", "old", "hi")
    assert gone["status"] == "error" and "Unknown Webhook" in gone["message"]


def test_message_length_limits_are_enforced_before_any_request(api, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "1:a")
    result = send("telegram", "123", "x" * 5000)
    assert result["status"] == "error" and "4096" in result["message"] and api.requests == []
    assert send("telegram", "123", "   ")["status"] == "error"
