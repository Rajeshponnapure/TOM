"""Experimental: let TOM play an installed game by looking at the screen and pressing keys.

The owner asked for this knowing the limits, and they are real, so TOM says them plainly before it
starts:
  * A local vision model decides a move from a screenshot a few times a second — that is far slower
    than human reflexes, so it will not play a fast action game well. Slow, turn-based or
    builder-style games fare better.
  * Many online games run anti-cheat that treats synthetic input as cheating; using this on one can
    get the account banned. TOM warns and only runs after the owner confirms that exact game.
  * It presses keys into whatever window is in front. The owner starts and focuses the game first.

How it works: capture the screen → ask a local vision model (Ollama, qwen3.5 has vision) for ONE
action from a fixed list → send it as a DirectInput scan code (the virtual keys pyautogui sends are
ignored by most games) → repeat, for a bounded time, stoppable at any moment. No network, no input
until the owner approves, and the policy emergency-stop halts it like anything else.
"""
from __future__ import annotations

import base64
import json
import os
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

# DirectInput scan codes (set 1) — what games actually read, unlike virtual-key events.
SCAN = {
    "W": 0x11, "A": 0x1E, "S": 0x1F, "D": 0x20, "SPACE": 0x39, "SHIFT": 0x2A, "CTRL": 0x1D,
    "E": 0x12, "Q": 0x10, "R": 0x13, "F": 0x21, "TAB": 0x0F, "ESC": 0x01, "ENTER": 0x1C,
    "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05,
    "UP": 0xC8, "DOWN": 0xD0, "LEFT": 0xCB, "RIGHT": 0xCD,
}
MOUSE = {"MOUSE_LEFT", "MOUSE_RIGHT"}
ACTIONS = list(SCAN) + list(MOUSE) + ["NONE"]


# ── DirectInput key send via SendInput (Windows) ───────────────────────────
def _send_scancode(code: int, down: bool) -> None:
    import ctypes
    from ctypes import wintypes
    KEYEVENTF_SCANCODE = 0x0008
    KEYEVENTF_KEYUP = 0x0002
    extended = 0x0001 if code in (0xC8, 0xD0, 0xCB, 0xCD) else 0

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

    class INPUT(ctypes.Structure):
        class _I(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]
        _anonymous_ = ("i",)
        _fields_ = [("type", wintypes.DWORD), ("i", _I)]

    flags = KEYEVENTF_SCANCODE | extended | (KEYEVENTF_KEYUP if not down else 0)
    inp = INPUT(type=1, ki=KEYBDINPUT(0, code, flags, 0, None))
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def _send_mouse(button: str, down: bool) -> None:
    import ctypes
    flags = {("MOUSE_LEFT", True): 0x0002, ("MOUSE_LEFT", False): 0x0004,
             ("MOUSE_RIGHT", True): 0x0008, ("MOUSE_RIGHT", False): 0x0010}[(button, down)]
    ctypes.windll.user32.mouse_event(flags, 0, 0, 0, 0)


def press_action(action: str, hold: float = 0.12) -> bool:
    """Send one action as real DirectInput. Returns True if it was a known action."""
    action = (action or "").strip().upper()
    if action in SCAN:
        _send_scancode(SCAN[action], True)
        time.sleep(hold)
        _send_scancode(SCAN[action], False)
        return True
    if action in MOUSE:
        _send_mouse(action, True)
        time.sleep(0.05)
        _send_mouse(action, False)
        return True
    return action == "NONE"


# ── vision decision via a local Ollama model ───────────────────────────────
def _ollama_vision(image_bytes: bytes, game: str, model: str) -> str:
    base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    prompt = (f"You are playing the video game '{game}'. Look at this frame and choose the single best "
              f"next action to make progress or survive. Reply with ONLY one token from this list: "
              f"{', '.join(ACTIONS)}. No explanation.")
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "images": [base64.b64encode(image_bytes).decode()],
                       "options": {"temperature": 0.2, "num_predict": 8}}).encode()
    req = urllib.request.Request(f"{base}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        out = json.loads(resp.read()).get("response", "")
    token = (out or "").strip().upper().split()[0] if out.strip() else "NONE"
    token = "".join(c for c in token if c.isalnum() or c == "_")
    return token if token in (a.upper() for a in ACTIONS) else "NONE"


@dataclass
class AutopilotRun:
    game: str
    seconds: float
    frames: int = 0
    actions: List[str] = field(default_factory=list)
    stopped_reason: str = ""


class GameAutopilot:
    """Observation (screenshots) is free; sending input to the game is the gated, warned action."""

    def __init__(self, hardware=None, decide: Optional[Callable] = None,
                 send: Optional[Callable[[str], bool]] = None, grab: Optional[Callable] = None,
                 model: str = "qwen3.5:4b"):
        self._hardware = hardware
        self._decide = decide
        self._send = send or press_action
        self._grab = grab
        self._model = model
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def available(self) -> bool:
        return os.name == "nt" and os.environ.get("TOM_DISABLE_UI_AUTOMATION") != "1"

    def _grab_frame(self) -> Optional[bytes]:
        if self._grab is not None:
            return self._grab()
        hw = self._hardware
        if hw is None:
            from tools.hardware_control import HardwareControl
            hw = self._hardware = HardwareControl()
        shot = hw.screenshot()
        if shot.get("status") != "success":
            return None
        try:
            with open(shot["path"], "rb") as fh:
                return fh.read()
        except OSError:
            return None

    def _decide_action(self, frame: bytes, game: str) -> str:
        if self._decide is not None:
            return self._decide(frame, game)
        try:
            return _ollama_vision(frame, game, self._model)
        except Exception:
            return "NONE"

    def play(self, game: str, seconds: float = 20.0, fps: float = 1.5,
             max_fail: int = 6) -> AutopilotRun:
        """The loop itself (no approval here — start() gates it). Bounded by `seconds`, stoppable via
        stop(), and halted by the policy emergency-stop."""
        from tom_core.policy.engine import get_policy
        run = AutopilotRun(game=game, seconds=seconds)
        self._stop.clear()
        end = time.monotonic() + max(1.0, seconds)
        interval = 1.0 / max(0.2, fps)
        fails = 0
        while time.monotonic() < end:
            if self._stop.is_set():
                run.stopped_reason = "stopped by request"
                break
            if get_policy().halted:
                run.stopped_reason = "emergency stop"
                break
            frame = self._grab_frame()
            if frame is None:
                fails += 1
                if fails >= max_fail:
                    run.stopped_reason = "could not capture the screen"
                    break
                time.sleep(interval)
                continue
            fails = 0
            action = self._decide_action(frame, game) or "NONE"
            run.frames += 1
            if action != "NONE":
                self._send(action)
                run.actions.append(action)
            time.sleep(interval)
        if not run.stopped_reason:
            run.stopped_reason = "time elapsed"
        return run

    def start(self, game: str, seconds: float = 20.0, fps: float = 1.5) -> Dict[str, object]:
        """Warn, get the owner's approval for this exact game, then run the loop and report honestly."""
        if not self.available():
            return {"status": "error", "response_type": "game_autopilot",
                    "message": "The autopilot needs Windows with UI automation enabled."}
        from tom_core.policy.engine import ActionClass
        from tom_core.tools.guard import enforce
        warning = (
            f"Experimental game autopilot for '{game}'. Before you say yes, know:\n"
            f"  • A local vision model picks moves ~{fps:g} times/second — it will NOT play a fast "
            "action game well.\n"
            "  • If this game has anti-cheat (most online games do), synthetic input can get your "
            "account BANNED.\n"
            f"  • It will press keys into the focused window for {seconds:g}s. Start and click into the "
            "game first.\n"
            "Stop any time by saying \"stop\" or with the emergency stop.")
        dec = enforce("game.autopilot", ActionClass.DESTRUCTIVE_OR_EXTERNAL,
                      payload={"game": game, "seconds": str(seconds)},
                      approval_action="game_autopilot", summary=warning, risk_level="high")
        if not dec.allowed:
            return dec.refusal({"response_type": "game_autopilot"})
        run = self.play(game, seconds=seconds, fps=fps)
        did = len(run.actions)
        return {"status": "success", "response_type": "game_autopilot",
                "frames": run.frames, "actions_sent": did, "stopped": run.stopped_reason,
                "message": (f"Autopilot for '{game}' finished ({run.stopped_reason}). I read {run.frames} "
                            f"frame(s) and sent {did} input(s). This is experimental — if it played "
                            "badly, that's the local vision model's speed, not a bug. Tell me to stop "
                            "any time.")}
