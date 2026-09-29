"""WhatsApp: desktop safety checks (faked Win32/pyautogui) and web logic (real Chromium, fake page)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest

from tools import whatsapp_tools as wt
from tools.whatsapp_tools import WhatsAppTools, normalize_number, resolve_number


# ── recipients ───────────────────────────────────────────────────────────────
def test_phone_numbers_are_normalised():
    assert normalize_number("+91 98765-43210") == "919876543210"
    assert normalize_number("(415) 555-0132") == "4155550132"
    assert normalize_number("Madhu") is None
    assert normalize_number("123") is None


def test_contacts_map_from_environment_and_file(tmp_path, monkeypatch):
    monkeypatch.setattr(wt, "project_path_str", lambda *p: str(tmp_path.joinpath(*p)))
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "whatsapp_contacts.json").write_text(json.dumps({"Mom": "+1 415 555 0100"}))
    monkeypatch.setenv("WHATSAPP_CONTACTS", json.dumps({"Madhu Sri": "+91 98765 43210", "bad": "abc"}))
    assert resolve_number("madhu sri") == "919876543210"
    assert resolve_number("MOM") == "14155550100"
    assert resolve_number("+44 20 7946 0958") == "442079460958"
    assert resolve_number("Nobody") is None


# ── desktop, with a fake keyboard and a fake window manager ─────────────────
class FakeKeys:
    def __init__(self):
        self.events = []

    def hotkey(self, *keys):
        self.events.append(("hotkey", keys))

    def press(self, key):
        self.events.append(("press", key))

    def write(self, text, interval=0):
        self.events.append(("write", text))

    def click(self, x, y):
        self.events.append(("click", (x, y)))


class Desktop(WhatsAppTools):
    """WhatsAppTools whose window title changes as scripted."""
    def __init__(self, titles, rect=(100, 50, 1100, 850), windows=True):
        super().__init__()
        self.titles = list(titles)      # consumed one per foreground query; the last one repeats
        self.rect = rect
        self.launched = []
        self.windows = windows

    @staticmethod
    def _is_windows():
        return True

    def _foreground_title(self):
        return self.titles.pop(0) if len(self.titles) > 1 else self.titles[0]

    def _foreground_rect(self):
        return self.rect

    def _launch_desktop(self, uri):
        self.launched.append(uri)


@pytest.fixture
def keys(monkeypatch):
    fake = FakeKeys()
    monkeypatch.setattr(wt, "pyautogui", fake)
    monkeypatch.setattr(wt, "_PYAUTOGUI_OK", True)
    monkeypatch.setattr(wt, "_PYPERCLIP_OK", False)
    monkeypatch.setattr(wt.asyncio, "sleep", _fast_sleep)
    monkeypatch.setenv("WHATSAPP_CONTACTS", json.dumps({"Madhu": "+91 98765 43210"}))
    return fake


_real_sleep = asyncio.sleep


async def _fast_sleep(_delay):
    await _real_sleep(0)


def test_known_number_opens_the_exact_chat_and_never_searches(keys):
    tools = Desktop(["WhatsApp"])
    result = asyncio.run(tools.send_message_native("Madhu", "hello there"))
    assert result["status"] == "unconfirmed" and result["sent"] is True       # never "success"
    assert tools.launched == ["whatsapp://send?phone=919876543210&text=hello%20there"]
    assert keys.events == [("press", "enter")]                                 # no search, no click
    assert "can't confirm" in result["message"] and "exact number" in result["message"]


def test_nothing_is_typed_when_whatsapp_is_not_in_front(keys):
    tools = Desktop(["Untitled - Notepad"])
    result = asyncio.run(tools.send_message_native("Madhu", "hello"))
    assert result["status"] == "error" and result["sent"] is False
    assert keys.events == []


def test_focus_stolen_mid_flow_stops_before_the_message_is_typed(keys):
    # In front for launch + search + select; then another app grabs focus.
    tools = Desktop(["WhatsApp"] * 5 + ["Slack"])
    result = asyncio.run(tools.send_message_native("Sam", "secret text"))       # name only -> search path
    assert result["status"] == "error" and result["sent"] is False
    assert ("write", "secret text") not in keys.events
    assert ("press", "enter") in keys.events                                  # only the contact selection
    assert sum(1 for e in keys.events if e[0] == "press") == 1


def test_name_search_clicks_inside_the_whatsapp_window_only(keys):
    tools = Desktop(["WhatsApp"], rect=(200, 100, 1000, 700))
    result = asyncio.run(tools.send_message_native("Sam", "hi"))
    assert result["status"] == "unconfirmed" and "first search match" in result["message"]
    clicks = [e[1] for e in keys.events if e[0] == "click"]
    assert clicks == [(600, 640)]
    left, top, right, bottom = 200, 100, 1000, 700
    assert left < clicks[0][0] < right and top < clicks[0][1] < bottom


def test_send_message_never_falls_back_to_web_after_keys_were_sent(keys, monkeypatch):
    tools = Desktop(["WhatsApp"])
    called = []

    async def web(*a):
        called.append(a)
        return {"status": "success"}
    monkeypatch.setattr(tools, "send_message_web", web)
    monkeypatch.setenv("WHATSAPP_MODE", "auto")
    result = asyncio.run(tools.send_message("Madhu", "hello"))
    assert result["status"] == "unconfirmed" and called == []


def test_send_message_uses_web_when_desktop_failed_before_sending(keys, monkeypatch):
    tools = Desktop(["Notepad"])
    called = []

    async def web(contact, message):
        called.append((contact, message))
        return {"status": "success", "sent": True, "message": "web ok"}
    monkeypatch.setattr(tools, "send_message_web", web)
    monkeypatch.setenv("WHATSAPP_MODE", "auto")
    result = asyncio.run(tools.send_message("Madhu", "hello"))
    assert called == [("Madhu", "hello")] and result["status"] == "success" and keys.events == []


def test_non_ascii_text_without_clipboard_support_is_refused_up_front(keys):
    tools = Desktop(["WhatsApp"])
    result = asyncio.run(tools.send_message_native("Madhu", "héllo 😀"))
    assert result["status"] == "error" and tools.launched == [] and keys.events == []


# ── web, in real Chromium against a fake WhatsApp-like page ─────────────────
PAGE = """
<div id="side"><div id="search" contenteditable="true" __SEARCH__></div>
  <div id="pane-side"></div></div>
<div id="main" style="display:none"><header><span id="hdr" dir="auto"></span></header>
  <div id="bubbles"></div>
  <footer><div id="composer" contenteditable="true" __COMPOSER__></div></footer></div>
<script>
const CHATS = __CHATS__, MODE = "__MODE__";
const pane = document.getElementById('pane-side'), search = document.getElementById('search');
function render(q){ pane.innerHTML=''; CHATS.filter(c=>c.toLowerCase().includes(q.toLowerCase())).forEach(c=>{
  const d=document.createElement('div'); const s=document.createElement('span'); s.setAttribute('title',c); s.textContent=c;
  s.onclick=()=>{ const h=document.getElementById('hdr'); const shown = MODE==='wrongchat' ? 'Somebody Else' : c;
    h.setAttribute('title', shown); h.textContent=shown; document.getElementById('main').style.display='block'; };
  d.appendChild(s); pane.appendChild(d); }); }
search.addEventListener('input', ()=>render(search.textContent)); render('');
const composer = document.getElementById('composer');
composer.addEventListener('keydown', e=>{ if(e.key==='Enter'){ e.preventDefault();
  const t=composer.textContent.trim(); if(!t) return; composer.textContent='';
  if(MODE==='silent') return;
  const b=document.createElement('div'); b.className='message-out'; const s=document.createElement('span');
  s.className='selectable-text'; s.textContent=t; b.appendChild(s); document.getElementById('bubbles').appendChild(b);} });
</script>"""

OLD = {"__SEARCH__": 'data-tab="3"', "__COMPOSER__": 'data-tab="10"'}
NEW = {"__SEARCH__": 'role="textbox" aria-label="Search input textbox"',
       "__COMPOSER__": 'role="textbox" aria-label="Type a message"'}


def _page_html(layout, chats, mode="ok"):
    html = PAGE.replace("__CHATS__", json.dumps(chats)).replace("__MODE__", mode)
    for key, value in layout.items():
        html = html.replace(key, value)
    return html


class WebDriver:
    """Run WhatsAppTools.send_message_web on a page that behaves like WhatsApp Web."""
    def __init__(self, layout, chats, mode="ok", prefill_from_url=False):
        self.layout, self.chats, self.mode, self.prefill = layout, chats, mode, prefill_from_url
        self.urls = []

    def run(self, contact, message):
        from playwright.async_api import async_playwright

        async def main():
            async with async_playwright() as pw:
                try:
                    exe = "/opt/pw-browsers/chromium"
                    browser = await pw.chromium.launch(executable_path=exe if os.path.exists(exe) else None,
                                                       args=["--no-sandbox"])
                except Exception as exc:
                    pytest.skip(f"Chromium not available: {str(exc)[:80]}")
                page = await browser.new_page()
                await page.set_content(_page_html(self.layout, self.chats, self.mode))
                tools = WhatsAppTools()
                driver = self

                async def ensure():
                    return page

                async def goto(_page, url):
                    driver.urls.append(url)
                    if driver.prefill:                       # /send?phone=..&text=.. opens the chat, text pre-filled
                        text = parse_qs(urlparse(url).query).get("text", [""])[0]
                        await page.evaluate("t => { document.getElementById('main').style.display='block';"
                                            "document.getElementById('composer').textContent=t; }", text)
                tools._ensure_browser = ensure
                tools._goto_web = goto
                try:
                    return await tools.send_message_web(contact, message), page
                finally:
                    self.outgoing = await page.eval_on_selector_all(
                        ".message-out span", "els => els.map(e => e.textContent)")
                    await browser.close()
        return asyncio.run(main())


@pytest.mark.parametrize("layout", [OLD, NEW], ids=["classic-layout", "aria-layout"])
def test_web_send_by_name_is_verified_by_reading_the_bubble_back(layout, monkeypatch):
    monkeypatch.delenv("WHATSAPP_CONTACTS", raising=False)
    driver = WebDriver(layout, ["Madhu Sri", "Ravi Kumar"])
    result, _ = driver.run("Madhu Sri", "see you at 5")
    assert result["status"] == "success" and result["verified"] is True, result
    assert driver.outgoing == ["see you at 5"]


def test_web_prefers_an_exact_name_over_longer_partial_matches(monkeypatch):
    monkeypatch.delenv("WHATSAPP_CONTACTS", raising=False)
    driver = WebDriver(OLD, ["Madhusudhan", "Madhu", "Madhu Sri"])
    result, _ = driver.run("madhu", "hi")
    assert result["status"] == "success" and "Madhu" in result["message"], result
    assert driver.outgoing == ["hi"]


def test_web_refuses_an_ambiguous_name_and_sends_nothing(monkeypatch):
    monkeypatch.delenv("WHATSAPP_CONTACTS", raising=False)
    driver = WebDriver(OLD, ["Madhu Sri", "Madhusudhan", "Ravi"])
    result, _ = driver.run("Madhu", "hi")
    assert result["status"] == "error" and result["sent"] is False
    assert "Madhu Sri" in result["message"] and "Madhusudhan" in result["message"]
    assert driver.outgoing == []


def test_web_unknown_contact_sends_nothing(monkeypatch):
    monkeypatch.delenv("WHATSAPP_CONTACTS", raising=False)
    driver = WebDriver(OLD, ["Ravi"])
    result, _ = driver.run("Zed", "hi")
    assert result["status"] == "error" and "couldn't find" in result["message"] and driver.outgoing == []


def test_web_aborts_if_the_opened_chat_is_not_the_requested_one(monkeypatch):
    monkeypatch.delenv("WHATSAPP_CONTACTS", raising=False)
    driver = WebDriver(OLD, ["Madhu Sri"], mode="wrongchat")
    result, _ = driver.run("Madhu Sri", "private text")
    assert result["status"] == "error" and "Somebody Else" in result["message"]
    assert driver.outgoing == []


def test_web_does_not_claim_success_when_the_message_never_appears(monkeypatch):
    monkeypatch.delenv("WHATSAPP_CONTACTS", raising=False)
    monkeypatch.setattr(WhatsAppTools, "_read_back", lambda self, page, message, timeout=10.0: _read_back_short(self, page, message))
    driver = WebDriver(OLD, ["Madhu Sri"], mode="silent")
    result, _ = driver.run("Madhu Sri", "hello")
    assert result["status"] == "unconfirmed" and result["verified"] is False


async def _read_back_short(self, page, message):
    texts = await page.eval_on_selector_all(wt.OUTGOING_TEXT, "els => els.map(e => e.innerText)")
    return bool(texts and message in texts[-1])


@pytest.mark.parametrize("layout", [OLD, NEW], ids=["classic-layout", "aria-layout"])
def test_web_send_to_a_number_uses_the_exact_chat_url(layout, monkeypatch):
    monkeypatch.setenv("WHATSAPP_CONTACTS", json.dumps({"Madhu": "+91 98765 43210"}))
    driver = WebDriver(layout, ["Someone"], prefill_from_url=True)
    result, _ = driver.run("Madhu", "hello & welcome")
    assert result["status"] == "success" and "+919876543210" in result["message"], result
    assert driver.urls == ["https://web.whatsapp.com/send?phone=919876543210&text=hello%20%26%20welcome"]
    assert driver.outgoing == ["hello & welcome"]
