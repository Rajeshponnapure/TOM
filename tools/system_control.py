"""Everyday Windows control: lock, sleep, restart / shut down (with a cancel window), brightness,
show the desktop, switch to or close an app, open a Settings page.

Every action passes the policy engine (emergency stop, audit log). Lock, brightness, desktop, switching
and Settings pages are reversible. Sleep, restart, shut down and closing an app can lose unsaved work,
so they need the owner's approval first (PRD FR-009). Results are checked where Windows lets us read
them back (brightness level, the window in front).
"""
from __future__ import annotations

import asyncio
import ctypes
import os
import re
import subprocess
from typing import Any, Callable, Dict, List, Optional, Tuple

SETTINGS_PAGES = {
    "wifi": "ms-settings:network-wifi", "wi-fi": "ms-settings:network-wifi", "network": "ms-settings:network-status",
    "bluetooth": "ms-settings:bluetooth", "display": "ms-settings:display", "screen": "ms-settings:display",
    "sound": "ms-settings:sound", "audio": "ms-settings:sound", "battery": "ms-settings:batterysaver",
    "power": "ms-settings:powersleep", "update": "ms-settings:windowsupdate", "windows update": "ms-settings:windowsupdate",
    "apps": "ms-settings:appsfeatures", "storage": "ms-settings:storagesense", "privacy": "ms-settings:privacy",
    "notifications": "ms-settings:notifications", "mouse": "ms-settings:mousetouchpad",
    "touchpad": "ms-settings:devices-touchpad", "keyboard": "ms-settings:typing",
    "personalization": "ms-settings:personalization", "background": "ms-settings:personalization-background",
    "default apps": "ms-settings:defaultapps", "night light": "ms-settings:nightlight",
    "date and time": "ms-settings:dateandtime", "language": "ms-settings:regionlanguage",
    "printers": "ms-settings:printers", "vpn": "ms-settings:network-vpn", "gaming": "ms-settings:gaming-gamebar",
}

_DEVICE = r"(?:my |the |this )?(?:pc|computer|laptop|system|machine|windows)"
_PATTERNS: List[Tuple[str, str]] = [
    ("cancel_shutdown", r"\b(?:cancel|abort|stop)\s+(?:the\s+)?(?:shut ?down|restart|reboot)\b"),
    ("lock", rf"\block\s+{_DEVICE}\b|\block\s+(?:my |the )?screen\b"),
    ("sleep", rf"\b(?:put|send)\s+{_DEVICE}\s+to\s+sleep\b|\bsleep\s+{_DEVICE}\b"),
    ("restart", rf"\b(?:restart|reboot)\s+{_DEVICE}\b"),
    ("shutdown", rf"\b(?:shut ?down|power off|turn off)\s+{_DEVICE}\b"),
    ("show_desktop", r"\b(?:show|go to)\s+(?:the\s+|my\s+)?desktop\b|\bminimi[sz]e\s+(?:all|everything)(?:\s+windows)?\b"),
]


def parse(command: str) -> Optional[Tuple[str, str]]:
    """(action, argument) for a system-control request, else None."""
    c = (command or "").lower().strip().rstrip(".!?")
    for action, rx in _PATTERNS:
        if re.search(rx, c):
            return action, ""
    if re.search(r"\bbrightness\b|\b(?:dim|brighten)\s+(?:the\s+)?screen\b", c):
        m = re.search(r"(\d{1,3})\s*%?", c)
        up = re.search(r"\b(?:up|increase|raise|higher|brighter|brighten)\b", c)
        down = re.search(r"\b(?:down|decrease|lower|reduce|dim|darker)\b", c)
        if m and (up or down) and re.search(r"\bby\s+\d", c):            # "increase brightness by 20"
            return "brightness", ("+" if up else "-") + m.group(1)
        if m:                                                             # "brightness 40%", "set brightness to 60"
            return "brightness", str(min(100, int(m.group(1))))
        if up:
            return "brightness", "+10"
        if down:
            return "brightness", "-10"
        if re.search(r"\b(?:what|current|check|show)\b", c):
            return "brightness", "?"
    m = re.match(r"^(?:please\s+)?open\s+(?:the\s+)?(?:windows\s+)?(.+?)\s+settings?$", c) or \
        re.match(r"^(?:please\s+)?(?:open\s+)?settings?\s+(?:for|of)\s+(.+)$", c)
    if m and m.group(1).strip() in SETTINGS_PAGES:
        return "settings", m.group(1).strip()
    m = re.match(r"^(?:please\s+)?switch\s+(?:back\s+)?to\s+(?:the\s+|my\s+)?(.+?)(?:\s+(?:window|app|application))?$", c)
    if m:
        return "switch", m.group(1).strip()
    m = re.match(r"^(?:please\s+)?(?:close|quit|exit)\s+(?:the\s+|my\s+)?([\w .+-]{2,40}?)(?:\s+(?:window|app|application))?$", c)
    if m and not re.search(r"\b(account|deal|ticket|issue|door|task|tab)\b", m.group(1)):
        return "close", m.group(1).strip()
    return None


def _windows() -> List[Tuple[int, str]]:
    if os.name != "nt" or os.environ.get("TOM_DISABLE_UI_AUTOMATION") == "1":
        return []
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    out: List[Tuple[int, str]] = []

    def cb(hwnd, _lp):
        if user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            if n:
                buf = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, buf, n + 1)
                out.append((int(hwnd), buf.value))
        return True

    user32.EnumWindows(ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(cb), 0)
    return out


def _match_window(name: str, windows: List[Tuple[int, str]]) -> List[Tuple[int, str]]:
    words = [w for w in re.split(r"\W+", name.lower()) if w]
    return [(h, t) for h, t in windows if words and all(w in t.lower() for w in words)]


def _powershell(script: str, timeout: int = 20) -> subprocess.CompletedProcess:
    return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                          capture_output=True, text=True, timeout=timeout)


class SystemControl:
    def __init__(self, windows: Optional[Callable[[], List[Tuple[int, str]]]] = None,
                 run: Optional[Callable[..., Any]] = None, hardware=None):
        self.windows = windows or _windows
        self._run = run                     # tests inject a fake for every OS call
        self._hardware = hardware

    # ── OS calls (replaced in tests) ─────────────────────────────────────
    def _os(self, op: str, *args):
        if self._run is not None:
            return self._run(op, *args)
        if os.name != "nt":
            raise OSError("Windows only")
        user32 = ctypes.windll.user32
        if op == "lock":
            return bool(user32.LockWorkStation())
        if op == "sleep":
            return bool(ctypes.windll.powrprof.SetSuspendState(False, False, False))
        if op == "shutdown":
            flag = "/r" if args[0] == "restart" else "/s"
            return subprocess.run(["shutdown", flag, "/t", "60"], capture_output=True, text=True, timeout=15).returncode == 0
        if op == "cancel_shutdown":
            return subprocess.run(["shutdown", "/a"], capture_output=True, text=True, timeout=15).returncode == 0
        if op == "get_brightness":
            r = _powershell("(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness | "
                            "Select-Object -First 1).CurrentBrightness")
            return int(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip().isdigit() else None
        if op == "set_brightness":
            r = _powershell("(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods | "
                            f"Select-Object -First 1) | Invoke-CimMethod -MethodName WmiSetBrightness "
                            f"-Arguments @{{Timeout=1; Brightness=[byte]{int(args[0])}}} | Out-Null")
            return r.returncode == 0
        if op == "close_window":
            return bool(user32.PostMessageW(args[0], 0x0010, 0, 0))          # WM_CLOSE: the app may ask to save
        if op == "foreground":
            hwnd = user32.GetForegroundWindow()
            n = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            return buf.value
        if op == "focus":
            user32.ShowWindow(args[0], 9)
            return bool(user32.SetForegroundWindow(args[0]))
        if op == "open_uri":
            os.startfile(args[0])                                             # type: ignore[attr-defined]
            return True
        raise ValueError(op)

    def _hw(self):
        if self._hardware is None:
            from tools.hardware_control import HardwareControl
            self._hardware = HardwareControl()
        return self._hardware

    async def _gate(self, action: str, target: str, needs_approval: bool, summary: str):
        from tom_core.policy.engine import ActionClass
        from tom_core.tools.guard import aenforce
        cls = ActionClass.DESTRUCTIVE_OR_EXTERNAL if needs_approval else ActionClass.REVERSIBLE
        return await aenforce(f"system.{action}", cls, payload={"action": action, "target": target},
                              approval_action=f"system_{action}", summary=summary)

    # ── actions ─────────────────────────────────────────────────────────
    async def run(self, action: str, arg: str = "") -> Dict[str, Any]:
        handler = getattr(self, f"_do_{action}", None)
        if handler is None:
            return {"status": "error", "message": f"Unknown system action: {action}"}
        approval = {"sleep": "Put this PC to sleep now? Unsaved work stays open but anything running pauses.",
                    "restart": "Restart this PC in 60 seconds? Save your work first — open apps will close.",
                    "shutdown": "Shut down this PC in 60 seconds? Save your work first — open apps will close.",
                    "close": f"Close '{arg}'? If it has unsaved work it may ask you to save, or the work may be lost."}
        gate = await self._gate(action, arg, action in approval, approval.get(action, f"{action} {arg}".strip()))
        if not gate.allowed:
            return {**gate.refusal(), "response_type": "system_control"}
        try:
            result = await handler(arg)
        except Exception as exc:                       # OS call failed (no WMI brightness on a desktop monitor …)
            result = {"status": "error", "message": f"Couldn't {action.replace('_', ' ')}: {type(exc).__name__}: {exc}"}
        result.setdefault("response_type", "system_control")
        result.setdefault("action", action)
        return result

    async def _do_lock(self, _arg):
        ok = await asyncio.to_thread(self._os, "lock")
        return {"status": "success" if ok else "error", "message": "Locked the PC." if ok else "Windows refused to lock."}

    async def _do_sleep(self, _arg):
        ok = await asyncio.to_thread(self._os, "sleep")
        return {"status": "success" if ok else "error",
                "message": "Putting the PC to sleep." if ok else "Windows did not allow sleep from here "
                           "(on some Modern Standby laptops only the power button or Start menu can do it)."}

    async def _do_restart(self, _arg):
        ok = await asyncio.to_thread(self._os, "shutdown", "restart")
        return {"status": "success" if ok else "error",
                "message": "Restarting in 60 seconds. Say \"cancel the restart\" to stop it." if ok
                else "Windows refused the restart."}

    async def _do_shutdown(self, _arg):
        ok = await asyncio.to_thread(self._os, "shutdown", "shutdown")
        return {"status": "success" if ok else "error",
                "message": "Shutting down in 60 seconds. Say \"cancel the shutdown\" to stop it." if ok
                else "Windows refused the shutdown."}

    async def _do_cancel_shutdown(self, _arg):
        ok = await asyncio.to_thread(self._os, "cancel_shutdown")
        return {"status": "success" if ok else "error",
                "message": "Cancelled — the PC will stay on." if ok else "There was no shutdown or restart to cancel."}

    async def _do_brightness(self, arg):
        now = await asyncio.to_thread(self._os, "get_brightness")
        if now is None:
            return {"status": "error", "message": "This display doesn't let Windows set brightness "
                                                  "(external monitors usually need their own buttons)."}
        if arg == "?":
            return {"status": "success", "level": now, "message": f"Brightness is {now}%."}
        target = max(0, min(100, now + int(arg))) if arg[0] in "+-" else int(arg)
        await asyncio.to_thread(self._os, "set_brightness", target)
        after = await asyncio.to_thread(self._os, "get_brightness")
        ok = after is not None and abs(after - target) <= 2
        return {"status": "success" if ok else "unverified", "level": after, "verified": ok,
                "message": f"Brightness set to {after}%." if ok else f"Asked for {target}%, but it reads {after}%."}

    async def _do_show_desktop(self, _arg):
        r = await asyncio.to_thread(self._hw().hotkey, "win", "d")
        ok = r.get("status") == "success"
        return {"status": "success" if ok else "error", "message": "Showing the desktop." if ok else r.get("message", "")}

    async def _do_switch(self, name):
        matches = _match_window(name, await asyncio.to_thread(self.windows))
        if not matches:
            return {"status": "error", "message": f"No open window matches '{name}'."}
        hwnd, title = matches[0]
        await asyncio.to_thread(self._os, "focus", hwnd)
        await asyncio.sleep(0.3)
        front = await asyncio.to_thread(self._os, "foreground")
        ok = front == title
        return {"status": "success" if ok else "unverified", "verified": ok,
                "message": f"Switched to {title}." if ok else f"Tried to bring '{title}' to the front, but "
                                                               f"'{front}' is in front (Windows can block focus changes)."}

    async def _do_close(self, name):
        matches = _match_window(name, await asyncio.to_thread(self.windows))
        if not matches:
            return {"status": "error", "message": f"No open window matches '{name}', so nothing was closed."}
        hwnd, title = matches[0]
        await asyncio.to_thread(self._os, "close_window", hwnd)
        await asyncio.sleep(1.5)
        still = any(h == hwnd for h, _t in await asyncio.to_thread(self.windows))
        return {"status": "unverified" if still else "success", "verified": not still,
                "message": (f"Asked '{title}' to close — it is still open (it may be asking you to save)."
                            if still else f"Closed {title}.")}

    async def _do_settings(self, page):
        uri = SETTINGS_PAGES[page]
        await asyncio.to_thread(self._os, "open_uri", uri)
        return {"status": "success", "message": f"Opened {page} settings."}
