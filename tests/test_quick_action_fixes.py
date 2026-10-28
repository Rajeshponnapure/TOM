"""Fixes found by driving every quick action with real input on 2026-10-21 (no model, no network)."""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.engine_router import EngineRouter, humanize  # noqa: E402


# ── Word/Excel/PowerPoint/PDF: model JSON that used to become a placeholder document ──
@pytest.mark.parametrize("reply", [
    'Here is the document:\n```json\n{"title": "Plan", "sections": [{"type": "paragraph", "text": "Hi"},]}\n```',
    '{"title": "Plan", // the title\n "sections": []} Hope this helps!',
    'Sure! {"title": “Plan”, "sections": []}',
])
def test_model_json_is_repaired(reply):
    from agent import TomAgent
    assert TomAgent._parse_model_json(reply)["title"] == "Plan"


@pytest.mark.parametrize("reply,subject,body_start", [
    ("SUBJECT: Moving Tomorrow's Meeting\nBODY:\nDear Ravi,\nCan we move it?", "Moving Tomorrow's Meeting", "Dear Ravi"),
    ("SUBJECT: Moving Tomorrow's Meeting\nDear Ravi,\nCan we move it?", "Moving Tomorrow's Meeting", "Dear Ravi"),
    ("**Subject:** Leave on Friday\n\nHi Priya,", "Leave on Friday", "Hi Priya"),
    ("Dear Ravi, see you at 4.", "", "Dear Ravi"),
])
def test_email_subject_never_lands_in_the_body(reply, subject, body_start):
    from agent import TomAgent
    got_subject, body = TomAgent._split_subject_body(reply)
    assert got_subject == subject and body.startswith(body_start) and "SUBJECT" not in body.upper()


# ── engines answer in readable text, not Python dicts ─────────────────────
def test_humanize_reads_like_text():
    text = humanize({"status": "success", "info": {"os": "Windows", "ram_gb": 31.5, "on_battery": False},
                     "ports": [135, 445]})
    assert "{" not in text and "'" not in text
    assert "Os: Windows" in text and "Ram gb: 31.5" in text and "On battery: no" in text and "135, 445" in text


def test_iot_firmware_has_real_line_breaks_and_the_right_wifi_header():
    from tools.iot_engine import IoTEngine, fix_code_newlines
    assert fix_code_newlines('int a;\\nint b;\\nSerial.println("x\\ny");') == 'int a;\nint b;\nSerial.println("x\\ny");'
    esp32 = IoTEngine().generate_esp_code("esp32", ["dht11"], protocols=["mqtt"])["result"]
    esp8266 = IoTEngine().generate_esp_code("esp8266", ["dht11"], protocols=["mqtt"])["result"]
    assert "#include <WiFi.h>" in esp32 and "ESP8266WiFi.h" not in esp32
    assert "#include <ESP8266WiFi.h>" in esp8266
    assert esp32.count("\n") > 60


# ── ML: a question is never answered with a model trained on demo numbers ──
def test_ml_without_data_asks_for_data_instead_of_running_on_demo_numbers():
    r = EngineRouter()
    out = r._run_ml("how would I forecast monthly sales?")
    assert out["status"] == "needs_input" and "demo" in out["message"].lower()
    ok = r._run_ml("train a linear regression on X=[[1],[2],[3],[4]] y=[2,4,6,8]")
    assert ok["status"] == "success" and "Demo data" not in ok["message"]


@pytest.mark.parametrize("text,key", [
    ("is example.com safe to open?", "websafety"),
    ("is this a scam: http://bit.ly/x", "websafety"),
    ("which ports are open on this pc?", "network"),
    ("check that http://localhost:3999 loads", "webauto"),
    ("debug http://localhost:5173", "webauto"),
    ("check this project for dependency conflicts", "deps"),
    ("is it safe to eat raw eggs", None),
    ("check my meeting at 10:30", None),
])
def test_engine_detection(text, key):
    assert EngineRouter().detect(text.lower()) == key


def test_engines_that_need_more_input_say_so_instead_of_reporting_success():
    r = EngineRouter()
    assert r._run_hardware("do something with the computer")["status"] == "needs_input"


def test_blender_missing_is_an_error_not_a_success(monkeypatch):
    r = EngineRouter()
    fake = types.SimpleNamespace(is_available=lambda: False)
    monkeypatch.setattr(r, "_get", lambda key: fake)
    assert r._run_blender("a low-poly house")["status"] == "error"


# ── web search reads real results (Google News RSS + Wikipedia), offline here ──
RSS = """<?xml version="1.0"?><rss><channel>
<item><title>Best laptops under Rs 60,000 - NDTV Profit</title><link>https://news.example/a</link>
<pubDate>Wed, 21 Oct 2026 10:00:00 GMT</pubDate><description>&lt;a&gt;Acer, Lenovo and Dell picks&lt;/a&gt;</description>
<source url="https://ndtvprofit.com">NDTV Profit</source></item>
</channel></rss>"""


class _Resp:
    def __init__(self, text="", data=None):
        self.text, self._data = text, data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def test_web_search_parses_news_and_wikipedia(monkeypatch):
    pytest.importorskip("bs4")
    import requests
    from tools import web_search

    def fake_get(url, params=None, **kw):
        if "news.google" in url:
            return _Resp(RSS)
        if "w/api.php" in url:
            return _Resp(data={"query": {"search": [{"title": "Laptop"}]}})
        return _Resp(data={"extract": "A laptop is a portable computer.",
                           "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Laptop"}}})
    monkeypatch.setattr(requests, "get", fake_get)
    hits = web_search.search("best laptops under 60000 rupees")
    assert hits[0].title == "Best laptops under Rs 60,000" and hits[0].source == "NDTV Profit"
    assert hits[0].snippet == "Acer, Lenovo and Dell picks"
    assert any(h.kind == "wiki" and "portable computer" in h.snippet for h in hits)
    assert "[1] Best laptops under Rs 60,000 — NDTV Profit" in web_search.sources_text(hits)


def test_web_search_survives_a_dead_source(monkeypatch):
    pytest.importorskip("bs4")
    import requests
    from tools import web_search

    def boom(*a, **k):
        raise requests.ConnectionError("offline")
    monkeypatch.setattr(requests, "get", boom)
    assert web_search.search("anything") == []


# ── deliverables never land inside the TOM repository ─────────────────────
def test_game_projects_go_to_the_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("TOM_WORKSPACE_DIR", str(tmp_path))
    from tools.game_dev import GameDevEngine
    assert GameDevEngine().output_dir.startswith(str(tmp_path))
