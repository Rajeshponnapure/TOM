"""Message someone on Instagram or LinkedIn the way the owner would: in their own, already-signed-in
Chrome profile, driven by sight (Tesseract OCR + mouse/keyboard), with the owner's approval of the
exact recipient and text before anything is sent.

Same design as tools/gmail_web.py, and the same reason for it: since Chrome 136 automation cannot
attach to the signed-in default profile, so TOM opens the site's messaging page in that profile and
acts on what it sees — it never handles the owner's password and opens no network port.

    1. open_messaging(app)            — the DM page in the last-used Chrome profile
    2. wait_for_app(app)              — a real Instagram/LinkedIn window is up (or it wants a login)
    3. compose(app, person, message)  — find search, type the name, open the first match, type the text
    4. (the agent shows the owner the exact person + message and asks — PRD FR-009)
    5. send(app, hwnd)                — the policy gate consumes that approval, the focused window is
                                        re-checked, then Enter; the sent text is read back on screen
                                        before "sent" is claimed

There is no out-of-band confirmation (no API), so the only proof a message went is that its text now
shows in the open conversation — send() reports `verified` only when it reads it back there.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from tools.gmail_web import _bring_to_front, _foreground_title, _visible_window_titles

APPS = ("instagram", "linkedin")

_DM_URL = {
    "instagram": "https://www.instagram.com/direct/inbox/",
    "linkedin": "https://www.linkedin.com/messaging/",
}
# title words that mean the window is that app, and that it is asking to log in
_TITLE_RX = {
    "instagram": re.compile(r"instagram", re.I),
    "linkedin": re.compile(r"linkedin|messaging", re.I),
}
_LOGIN_RX = re.compile(r"log in|login|sign in|sign up", re.I)
# where the search box's placeholder text sits, so OCR can find it
_SEARCH_HINT = {"instagram": "Search", "linkedin": "Search messages"}
# the send keystroke each site uses from the message box
_SEND_KEYS = {"instagram": ("enter",), "linkedin": ("enter",)}


def normalize_app(text: str) -> str:
    t = (text or "").lower()
    if "instagram" in t or re.search(r"\binsta\b|\big\b", t):
        return "instagram"
    if "linkedin" in t:
        return "linkedin"
    return ""


class SocialWeb:
    def __init__(self, profiles=None, hardware=None,
                 windows: Optional[Callable[[], List[Tuple[int, str, str]]]] = None,
                 foreground: Optional[Callable[[], str]] = None,
                 focus: Optional[Callable[[int], None]] = None,
                 poll: float = 0.5, screen=None):
        if profiles is None:
            from tools.chrome_profiles import ChromeProfileManager
            profiles = ChromeProfileManager()
        self.profiles = profiles
        self._hardware = hardware
        self.windows = windows or _visible_window_titles
        self.foreground = foreground or _foreground_title
        self.focus = focus or _bring_to_front
        self.poll = poll
        self._screen_tool = screen

    # ── Chrome ────────────────────────────────────────────────────────────
    def available(self) -> bool:
        if os.environ.get("TOM_DISABLE_UI_AUTOMATION") == "1":
            return False
        exe = getattr(self.profiles, "chrome_executable", "")
        return bool(exe) and (exe == "chrome.exe" or os.path.isfile(exe)) and os.name == "nt"

    def last_used_profile(self) -> str:
        try:
            with open(os.path.join(self.profiles.user_data_dir, "Local State"), encoding="utf-8") as fh:
                return str(json.load(fh).get("profile", {}).get("last_used") or "Default")
        except (OSError, ValueError, TypeError):
            return "Default"

    def _app_windows(self, app: str) -> List[Tuple[int, str]]:
        rx = _TITLE_RX[app]
        return [(h, t) for h, cls, t in self.windows()
                if cls.startswith("Chrome_WidgetWin") and rx.search(t)]

    async def open_messaging(self, app: str) -> Dict[str, Any]:
        from tom_core.policy.engine import ActionClass
        from tom_core.tools.guard import aenforce
        if app not in APPS:
            return {"status": "error", "message": f"I can message on {', '.join(APPS)} — not '{app}'."}
        gate = await aenforce("social_web.open", ActionClass.REVERSIBLE, payload={"app": app},
                              approval_action="open_browser")
        if not gate.allowed:
            return gate.refusal()
        before = set(self._app_windows(app))
        profile = self.last_used_profile()
        launched = await asyncio.to_thread(self.profiles.launch_profile, profile, _DM_URL[app])
        if launched.get("status") != "success":
            return launched
        return {"status": "success", "app": app, "profile": profile, "windows_before": before}

    async def wait_for_app(self, app: str, timeout: float = 25.0,
                           before: Optional[set] = None) -> Dict[str, Any]:
        deadline = time.monotonic() + timeout
        before = before or set()
        while True:
            wins = [w for w in self._app_windows(app) if w not in before] or self._app_windows(app)
            login = [(h, t) for h, t in wins if _LOGIN_RX.search(t)]
            ready = [(h, t) for h, t in wins if not _LOGIN_RX.search(t)]
            if ready:
                return {"status": "ready", "hwnd": ready[0][0], "title": ready[0][1]}
            if login:
                return {"status": "login", "hwnd": login[0][0], "title": login[0][1],
                        "message": f"{app.title()} in Chrome is asking you to log in. Sign in there, "
                                   "then ask me again."}
            if time.monotonic() >= deadline:
                return {"status": "timeout",
                        "message": f"{app.title()} did not open in Chrome in time."}
            await asyncio.sleep(self.poll)

    def _screen(self):
        if getattr(self, "_screen_tool", None) is None:
            if os.environ.get("TOM_DISABLE_UI_AUTOMATION") == "1":
                from tools.gmail_web import _NoScreen
                self._screen_tool = _NoScreen()
            else:
                from tom_core.screen_control import ScreenControl
                self._screen_tool = ScreenControl(hardware=self._hardware)
        return self._screen_tool

    def _hw(self):
        if self._hardware is None:
            from tools.hardware_control import HardwareControl
            self._hardware = HardwareControl()
        return self._hardware

    async def compose(self, app: str, person: str, message: str, hwnd: int,
                      timeout: float = 18.0) -> Dict[str, Any]:
        """Open the chat with `person` and type `message` into the message box (nothing is sent yet).
        Returns {"ok": bool|None, "message": ...}; ok=None when OCR isn't available."""
        from tom_core.screen_control import window_box
        sc = self._screen()
        usable, why = sc.available()
        if not usable:
            return {"ok": None, "message": why}
        box = window_box(hwnd)
        self.focus(hwnd)
        await asyncio.sleep(1.0)
        hw = self._hw()
        # 1) the search field — click its placeholder, type the name
        hint = _SEARCH_HINT[app]
        deadline = time.monotonic() + timeout
        found_search = None
        while time.monotonic() < deadline:
            found_search = await asyncio.to_thread(sc.find, hint, box)
            if found_search:
                break
            await asyncio.sleep(0.8)
        if not found_search:
            return {"ok": False, "message": f"I couldn't find the search box on {app.title()} to look "
                                            f"up {person}. The page may still be loading or looks different."}
        clicked = await asyncio.to_thread(sc.click_text, hint, box, False, "")
        if clicked.get("status") == "blocked":
            return {"ok": False, "message": clicked.get("message", "Blocked.")}
        await asyncio.sleep(0.5)
        await asyncio.to_thread(hw.type_text, person)
        await asyncio.sleep(1.8)                      # results load
        # 2) open the first matching result
        hit = await asyncio.to_thread(sc.find, person, box, None, 0.7)
        if not hit:
            return {"ok": False, "message": f"I searched {app.title()} for \"{person}\" but couldn't see a "
                                           "matching person in the results. Check the name or open the chat "
                                           "yourself, then ask me to type the message."}
        await asyncio.to_thread(sc.click_text, person, box, False, "")
        await asyncio.sleep(1.5)
        # 3) type the message into the composer (the message box has focus after the chat opens;
        #    Instagram/LinkedIn both put the caret in the "Write a message" field)
        await asyncio.to_thread(hw.type_text, message)
        await asyncio.sleep(0.5)
        probe = " ".join(re.sub(r"[^\w ]", " ", message).split()[:5])
        seen = bool(probe) and await asyncio.to_thread(sc.find, probe, box, None, 0.8) is not None
        return {"ok": True, "hwnd": hwnd, "typed_seen": seen,
                "message": f"Opened the chat with {person} on {app.title()} and typed the message"
                           + (" — I can see it in the box." if seen else ".")}

    async def send(self, app: str, person: str, message: str, hwnd: int) -> Dict[str, Any]:
        """Send the message now. Gated on the owner's approval of this exact (app, person, message)."""
        from tom_core.policy.engine import ActionClass
        from tom_core.tools.guard import aenforce
        gate = await aenforce("social_web.send", ActionClass.DESTRUCTIVE_OR_EXTERNAL,
                              payload={"app": app, "to": person, "message": message},
                              approval_action="social_message",
                              summary=f"Send this {app.title()} message to {person}:\n\"{message[:300]}\"")
        if not gate.allowed:
            return gate.refusal({"response_type": "social_message", "sent": False})
        self.focus(hwnd)
        await asyncio.sleep(0.6)
        title = self.foreground()
        if not _TITLE_RX[app].search(title) or _LOGIN_RX.search(title):
            return {"status": "blocked", "sent": False, "response_type": "social_message",
                    "message": f"Not sent: the window in front is '{title or 'unknown'}', not the "
                               f"{app.title()} chat. The message is still typed, not sent."}
        hw = self._hw()
        pressed = await asyncio.to_thread(hw.press_key, _SEND_KEYS[app][0])
        if pressed.get("status") != "success":
            return {"status": "error", "sent": False, "response_type": "social_message",
                    "message": f"Could not press send on {app.title()}: {pressed.get('message', pressed)}"}
        # verify: the message text now appears in the open conversation thread
        verified = None
        sc = self._screen()
        if sc.available()[0]:
            from tom_core.screen_control import window_box
            await asyncio.sleep(1.5)
            probe = " ".join(re.sub(r"[^\w ]", " ", message).split()[:6])
            verified = bool(probe) and await asyncio.to_thread(sc.find, probe, window_box(hwnd)) is not None
        if verified:
            return {"status": "success", "sent": True, "verified": True, "response_type": "social_message",
                    "message": f"Sent to {person} on {app.title()} — I can see it in the conversation."}
        return {"status": "unverified", "sent": None, "verified": False, "response_type": "social_message",
                "message": f"I pressed send on the {app.title()} chat with {person}, but couldn't read the "
                           "message back in the thread to confirm. Check the chat."}
