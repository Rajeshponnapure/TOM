"""Instagram / LinkedIn messaging in the owner's Chrome profile (tools.social_web) — all fakes, no
real Chrome, no real send. The gate is exercised through the real policy engine."""
import asyncio
import json

import pytest

from tools import social_web
from tools.social_web import SocialWeb, normalize_app

CHROME = "Chrome_WidgetWin_1"


class Profiles:
    def __init__(self, user_data_dir="", ok=True):
        self.user_data_dir = user_data_dir
        self.chrome_executable = "chrome.exe"
        self.launched = []
        self.ok = ok

    def launch_profile(self, profile, url):
        self.launched.append((profile, url))
        return {"status": "success"} if self.ok else {"status": "error", "message": "no chrome"}


class Hardware:
    def __init__(self):
        self.typed = []
        self.keys = []

    def type_text(self, text, interval=0.0):
        self.typed.append(text)
        return {"status": "success"}

    def press_key(self, key):
        self.keys.append(key)
        return {"status": "success"}


class Windows:
    def __init__(self, *frames):
        self.frames = list(frames)

    def __call__(self):
        return self.frames.pop(0) if len(self.frames) > 1 else self.frames[0]


class FakeScreen:
    """OCR stand-in: `texts` is everything "on screen"; find() matches a substring (case-insensitive)."""
    def __init__(self, texts, usable=True):
        self.texts = [t.lower() for t in texts]
        self.usable = usable
        self.clicked = []
        self.typed = []

    def available(self):
        return (self.usable, "" if self.usable else "no OCR")

    def read(self, box=None):
        return self.texts

    def find(self, target, box=None, lines=None, min_score=0.8):
        t = (target or "").lower()
        return object() if any(t in line for line in self.texts) else None

    def click_text(self, target, box=None, double=False, kind=""):
        self.clicked.append(target)
        return {"status": "success"}


def _sw(screen, windows=None, foreground="Instagram • Chat - Google Chrome", profiles=None):
    focused = []
    sw = SocialWeb(profiles=profiles or Profiles(), hardware=Hardware(),
                   windows=windows or Windows([(1, CHROME, "Instagram • Chat - Google Chrome")]),
                   foreground=lambda: foreground, focus=focused.append, poll=0.001, screen=screen)
    sw.focused = focused
    return sw


def test_normalize_app():
    assert normalize_app("message him on insta") == "instagram"
    assert normalize_app("dm on LinkedIn") == "linkedin"
    assert normalize_app("whatsapp mom") == ""


def test_open_messaging_launches_last_profile_with_dm_url(tmp_path):
    (tmp_path / "Local State").write_text(json.dumps({"profile": {"last_used": "Profile 1"}}), encoding="utf-8")
    profiles = Profiles(str(tmp_path))
    sw = _sw(FakeScreen([]), profiles=profiles)
    res = asyncio.run(sw.open_messaging("instagram"))
    assert res["status"] == "success" and profiles.launched[0][0] == "Profile 1"
    assert profiles.launched[0][1] == "https://www.instagram.com/direct/inbox/"


def test_unknown_app_is_rejected():
    res = asyncio.run(_sw(FakeScreen([])).open_messaging("myspace"))
    assert res["status"] == "error"


def test_wait_for_app_detects_login_page():
    win = Windows([(1, CHROME, "Log in • Instagram - Google Chrome")])
    sw = _sw(FakeScreen([]), windows=win)
    res = asyncio.run(sw.wait_for_app("instagram", timeout=0.05))
    assert res["status"] == "login" and "log in" in res["message"].lower()


def test_compose_types_name_and_message():
    screen = FakeScreen(["Search", "John Doe", "Write a message", "hey there about tomorrow"])
    sw = _sw(screen)
    hw = sw._hw()
    res = asyncio.run(sw.compose("instagram", "John Doe", "hey there about tomorrow", hwnd=1))
    assert res["ok"] is True
    assert "John Doe" in hw.typed and "hey there about tomorrow" in hw.typed    # name then message typed
    assert "Search" in screen.clicked and "John Doe" in screen.clicked          # searched, opened result


def test_compose_reports_when_person_not_found():
    screen = FakeScreen(["Search", "someone else entirely"])
    res = asyncio.run(_sw(screen).compose("instagram", "John Doe", "hi", hwnd=1))
    assert res["ok"] is False and "couldn't see" in res["message"].lower()


def test_send_is_gated_and_blocked_without_approval(monkeypatch):
    import tom_core.tools.guard as guard
    monkeypatch.setattr(guard, "_approval_manager", None)      # no approval channel → blocked
    sw = _sw(FakeScreen(["hey there"]))
    hw = sw._hw()
    res = asyncio.run(sw.send("instagram", "John", "hey there", hwnd=1))
    assert res["status"] in ("blocked", "cancelled") and res["sent"] is False
    assert hw.keys == []                                       # nothing was ever pressed


def test_send_presses_enter_and_verifies_after_approval(monkeypatch):
    import tom_core.tools.guard as guard
    from tools.approval import ApprovalManager
    mgr = ApprovalManager()
    mgr.provider = lambda req: True
    monkeypatch.setattr(guard, "_approval_manager", mgr)
    screen = FakeScreen(["hey there about tomorrow"])          # the message is visible in the thread
    sw = _sw(screen, foreground="Instagram • Chat - Google Chrome")
    hw = sw._hw()
    res = asyncio.run(sw.send("instagram", "John", "hey there about tomorrow", hwnd=1))
    assert res["status"] == "success" and res["sent"] is True and res["verified"] is True
    assert hw.keys == ["enter"]


def test_send_refuses_when_front_window_is_not_the_app(monkeypatch):
    import tom_core.tools.guard as guard
    from tools.approval import ApprovalManager
    mgr = ApprovalManager()
    mgr.provider = lambda req: True
    monkeypatch.setattr(guard, "_approval_manager", mgr)
    sw = _sw(FakeScreen(["hey"]), foreground="Notepad - Untitled")   # focus slipped away
    hw = sw._hw()
    res = asyncio.run(sw.send("instagram", "John", "hey", hwnd=1))
    assert res["status"] == "blocked" and res["sent"] is False and hw.keys == []


def test_send_unverified_when_message_not_seen_back(monkeypatch):
    import tom_core.tools.guard as guard
    from tools.approval import ApprovalManager
    mgr = ApprovalManager()
    mgr.provider = lambda req: True
    monkeypatch.setattr(guard, "_approval_manager", mgr)
    sw = _sw(FakeScreen(["something unrelated"]))              # can't read the message back
    res = asyncio.run(sw.send("instagram", "John", "hey there", hwnd=1))
    assert res["status"] == "unverified" and res["sent"] is None


# ── the agent's parser ──────────────────────────────────────────────────
import agent as agent_mod


@pytest.mark.parametrize("cmd,app,person,msg", [
    ("message Sara on instagram: running late", "instagram", "Sara", "running late"),
    ("dm @john_doe on insta saying hey there", "instagram", "john_doe", "hey there"),
    ("text the recruiter on linkedin that I accept the offer", "linkedin", "recruiter", "I accept the offer"),
    ("send a message to Priya Sharma on instagram: hi", "instagram", "Priya Sharma", "hi"),
])
def test_parse_social(cmd, app, person, msg):
    p, m = agent_mod.TomAgent._parse_social(cmd, app)
    assert p == person and m == msg
