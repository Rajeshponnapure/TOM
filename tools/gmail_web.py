"""Send an email the way the owner would: in Gmail, in their own Chrome profile.

Owner request 2026-10-27: "open my default profile in Chrome, open the mail, search for the person,
enter their email, type what I want, ask me if I want to send, and send it."

    1. find_contacts("Ravi")      — the person's address from the owner's own mail (Sent + Inbox, IMAP)
    2. open_compose(to, subj, b)  — Gmail's compose page, pre-filled, in the last-used Chrome profile
    3. wait_for_compose()         — the Gmail window is really there (or Gmail asks to sign in)
    4. (the agent asks the owner, showing the exact message — PRD FR-009)
    5. send_open_draft()          — the policy gate consumes that approval, the focused window is checked
                                    to be that Gmail compose, then Ctrl+Enter (Gmail's send shortcut)
    6. verify_sent()              — the message must appear in the Sent folder before "sent" is claimed

Why not Playwright on the real profile: since Chrome 136, --remote-debugging-port is ignored for the
default user-data directory, so automation can't attach to the owner's signed-in profile. Opening a
URL in it and pressing Gmail's own shortcut works with the session the owner already has.
"""
from __future__ import annotations

import asyncio
import email.utils
import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import quote

MAX_URL = 7000            # long bodies can exceed what Gmail accepts in a URL; those go through SMTP


def compose_url(to: str, subject: str, body: str, account: str = "") -> str:
    """https://mail.google.com/mail/u/<account>/?view=cm&fs=1&to=…&su=…&body=…"""
    who = quote(account) if account else "0"
    return (f"https://mail.google.com/mail/u/{who}/?view=cm&fs=1&tf=1"
            f"&to={quote(to)}&su={quote(subject or '')}&body={quote(body or '')}")


def _visible_window_titles() -> List[Tuple[int, str, str]]:
    """(hwnd, class name, title) of every visible top-level window (Windows only)."""
    if os.name != "nt" or os.environ.get("TOM_DISABLE_UI_AUTOMATION") == "1":
        return []
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    found: List[Tuple[int, str, str]] = []

    def cb(hwnd, _lp):
        if user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            if n:
                title = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, title, n + 1)
                cls = ctypes.create_unicode_buffer(128)
                user32.GetClassNameW(hwnd, cls, 128)
                found.append((int(hwnd), cls.value, title.value))
        return True

    user32.EnumWindows(ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(cb), 0)
    return found


def _foreground_title() -> str:
    if os.name != "nt":
        return ""
    import ctypes
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def _bring_to_front(hwnd: int) -> None:
    if os.name != "nt":
        return
    import ctypes
    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, 9)                      # SW_RESTORE
    user32.SetForegroundWindow(hwnd)


class GmailWeb:
    def __init__(self, email_tools=None, profiles=None, hardware=None,
                 windows: Optional[Callable[[], List[Tuple[int, str, str]]]] = None,
                 foreground: Optional[Callable[[], str]] = None,
                 focus: Optional[Callable[[int], None]] = None,
                 poll: float = 0.5):
        if profiles is None:
            from tools.chrome_profiles import ChromeProfileManager
            profiles = ChromeProfileManager()
        self.profiles = profiles
        self.email_tools = email_tools
        self._hardware = hardware
        self.windows = windows or _visible_window_titles
        self.foreground = foreground or _foreground_title
        self.focus = focus or _bring_to_front
        self.poll = poll
        self.account = os.environ.get("EMAIL_ADDRESS", "").strip()

    # ── Chrome ────────────────────────────────────────────────────────────

    def available(self) -> bool:
        if os.environ.get("TOM_DISABLE_UI_AUTOMATION") == "1":     # tests never drive the owner's Chrome
            return False
        exe = getattr(self.profiles, "chrome_executable", "")
        return bool(exe) and (exe == "chrome.exe" or os.path.isfile(exe)) and os.name == "nt"

    def last_used_profile(self) -> str:
        """The profile Chrome opens by default: Local State → profile.last_used (else "Default")."""
        try:
            with open(os.path.join(self.profiles.user_data_dir, "Local State"), encoding="utf-8") as fh:
                return str(json.load(fh).get("profile", {}).get("last_used") or "Default")
        except (OSError, ValueError, TypeError):
            return "Default"

    def _gmail_windows(self) -> List[Tuple[int, str]]:
        return [(h, t) for h, cls, t in self.windows()
                if cls.startswith("Chrome_WidgetWin") and re.search(r"gmail|compose|sign in|google accounts", t, re.I)]

    async def open_compose(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        from tom_core.policy.engine import ActionClass
        from tom_core.tools.guard import aenforce
        url = compose_url(to, subject, body, self.account)
        if len(url) > MAX_URL:
            return {"status": "too_long", "message": "The message is too long to open through a Gmail link."}
        gate = await aenforce("gmail_web.open_compose", ActionClass.REVERSIBLE, payload={"to": to, "subject": subject},
                              approval_action="open_browser")
        if not gate.allowed:
            return gate.refusal()
        before = set(self._gmail_windows())               # an inbox already open must not count as the draft
        profile = self.last_used_profile()
        launched = await asyncio.to_thread(self.profiles.launch_profile, profile, url)
        if launched.get("status") != "success":
            return launched
        return {"status": "success", "profile": profile, "url_length": len(url), "windows_before": before}

    async def wait_for_compose(self, subject: str = "", timeout: float = 25.0,
                               before: Optional[set] = None) -> Dict[str, Any]:
        """Wait until a Chrome window shows the new Gmail page (its title changes once the compose tab loads).
        `before` = the Gmail windows (hwnd, title) that existed before the draft was opened."""
        deadline = time.monotonic() + timeout
        before = before or set()
        while True:
            wins = [w for w in self._gmail_windows() if w not in before]
            signin = [(h, t) for h, t in wins if re.search(r"sign in|google accounts", t, re.I)]
            ready = [(h, t) for h, t in wins if re.search(r"gmail", t, re.I) and (h, t) not in signin]
            if subject:
                exact = [(h, t) for h, t in ready if subject[:25].lower() in t.lower()]
                ready = exact or ready
            if ready:
                return {"status": "ready", "hwnd": ready[0][0], "title": ready[0][1]}
            if signin:
                return {"status": "signin", "hwnd": signin[0][0], "title": signin[0][1],
                        "message": "Gmail in Chrome is asking you to sign in. Sign in there, then ask me again."}
            if time.monotonic() >= deadline:
                return {"status": "timeout", "message": "Gmail did not open in Chrome in time (no Gmail window)."}
            await asyncio.sleep(self.poll)

    async def send_open_draft(self, to: str, subject: str, hwnd: int) -> Dict[str, Any]:
        """Send the compose window that is open for (to, subject). Needs the owner's approval of exactly
        that recipient and subject (the same gate as every other email send)."""
        from tools.email_tools import EmailTools
        gate = await EmailTools._policy_gate(to, subject)
        if not gate.allowed:
            return gate.refusal()
        self.focus(hwnd)
        await asyncio.sleep(0.6)
        title = self.foreground()
        if not re.search(r"gmail", title, re.I) or re.search(r"sign in", title, re.I):
            # PRD §8.1: stop on an unexpected focus change instead of typing into another window.
            return {"status": "blocked", "sent": False,
                    "message": f"Not sent: the window in front is '{title or 'unknown'}', not the Gmail draft. "
                               "The draft is still open in Chrome."}
        hw = self._hardware
        if hw is None:
            from tools.hardware_control import HardwareControl
            hw = self._hardware = HardwareControl()
        pressed = await asyncio.to_thread(hw.hotkey, "ctrl", "enter")
        if pressed.get("status") != "success":
            return {"status": "error", "sent": False,
                    "message": f"Could not press Send in Gmail: {pressed.get('message', pressed)}"}
        return {"status": "pressed", "sent": None}

    # ── the owner's mailbox (IMAP) ────────────────────────────────────────

    async def _imap(self):
        if self.email_tools is None:
            return None
        try:
            return await self.email_tools._get_active_mail_connection()
        except Exception:
            return None

    @staticmethod
    def _sent_folder(mail) -> str:
        try:
            for flags, _delim, name in mail.list_folders():
                if any((f.decode() if isinstance(f, bytes) else str(f)).lower() == "\\sent" for f in flags):
                    return name
        except Exception:
            pass
        return "[Gmail]/Sent Mail"

    async def find_contacts(self, name: str, limit: int = 5) -> Optional[List[Dict[str, Any]]]:
        """People in the owner's own mail whose name or address matches `name`, most frequent first.
        None when the mailbox can't be read (so the caller asks for the address instead)."""
        mail = await self._imap()
        token = (name or "").strip()
        if mail is None or len(token) < 2:
            return None
        counts: Dict[str, Dict[str, Any]] = {}
        me = self.account.lower()

        def scan(folder: str) -> None:
            mail.select_folder(folder, readonly=True)
            ids = mail.search(["OR", "FROM", token, "TO", token])[-200:]
            if not ids:
                return
            for _id, data in mail.fetch(ids, ["BODY.PEEK[HEADER.FIELDS (FROM TO CC)]"]).items():
                raw = next((v for k, v in data.items() if b"HEADER" in k), b"")
                text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
                fields = re.findall(r"^(?:From|To|Cc):\s*(.+(?:\r?\n[ \t].+)*)", text, re.I | re.M)
                for display, addr in email.utils.getaddresses(fields):
                    addr = addr.strip().lower()
                    if not addr or addr == me or "noreply" in addr or "no-reply" in addr:
                        continue
                    display = _decode(display)
                    hay = f"{display} {addr.split('@')[0]}".lower()
                    if all(part in hay for part in token.lower().split()):
                        entry = counts.setdefault(addr, {"name": display, "address": addr, "count": 0})
                        entry["count"] += 1
                        if display and not entry["name"]:
                            entry["name"] = display

        try:
            await asyncio.to_thread(scan, "INBOX")
            await asyncio.to_thread(scan, self._sent_folder(mail))
        except Exception:
            return None
        return sorted(counts.values(), key=lambda e: -e["count"])[:limit]

    async def verify_sent(self, to: str, subject: str, since: float, timeout: float = 45.0) -> Optional[bool]:
        """True once a message to `to` with this subject is in Sent; False if it never appears;
        None when the mailbox can't be read (then the outcome is reported as unverified)."""
        mail = await self._imap()
        if mail is None:
            return None
        day = (datetime.fromtimestamp(since) - timedelta(days=1)).date()
        want = re.sub(r"\s+", " ", subject or "").strip().lower()

        def look() -> bool:
            mail.select_folder(self._sent_folder(mail), readonly=True)
            ids = mail.search(["SINCE", day, "TO", to])[-20:]
            if not ids:
                return False
            for _id, data in mail.fetch(ids, ["BODY.PEEK[HEADER.FIELDS (SUBJECT)]"]).items():
                raw = next((v for k, v in data.items() if b"HEADER" in k), b"")
                got = _decode(re.sub(r"(?is)^subject:\s*", "", (raw.decode("utf-8", "replace") if isinstance(raw, bytes)
                                                                 else str(raw)).strip()))
                if re.sub(r"\s+", " ", got).strip().lower() == want:
                    return True
            return False

        deadline = time.monotonic() + timeout
        while True:
            try:
                if await asyncio.to_thread(look):
                    return True
            except Exception:
                return None
            if time.monotonic() >= deadline:
                return False
            await asyncio.sleep(max(self.poll, 0.01) * 6)


def _decode(value: str) -> str:
    try:
        from email.header import decode_header, make_header
        return str(make_header(decode_header(value or ""))).strip().strip('"')
    except Exception:
        return (value or "").strip().strip('"')
