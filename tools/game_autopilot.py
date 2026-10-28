"""Experimental: let TOM play an installed game by looking at the screen and driving the mouse + keys.

What "professional scale" means here, honestly: the *pipeline* is built like a real game bot —
high-FPS screen capture (mss), fast computer-vision perception (OpenCV: template, colour and motion),
and real low-latency DirectInput (relative mouse aiming + scan-code keys), with the slow vision model
used only to set high-level goals a few times a second. The reflex layer runs at capture speed, which
is what makes quick reactions possible; `benchmark()` measures the real frame rate so the number is
never guessed. What this does NOT magically give is competitive, human-level play of an arbitrary
game — that still needs per-game perception/logic or a trained model. So the engine gives fast,
measured, reliable control; winning a specific game is then a matter of tuning a strategy for it.

The owner's warnings still hold and are shown before it runs:
  * Anti-cheat on online games treats synthetic input as cheating → can BAN the account.
  * It drives the mouse/keyboard of the focused window. Start and focus the game first.
  * Stop any time ("stop" / emergency stop). The loop is time-bounded regardless.

No network beyond the local model, and no input at all until the owner approves the exact game.
"""
from __future__ import annotations

import base64
import json
import os
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# DirectInput scan codes (set 1) — what games actually read, unlike virtual-key events.
SCAN = {
    "W": 0x11, "A": 0x1E, "S": 0x1F, "D": 0x20, "SPACE": 0x39, "SHIFT": 0x2A, "CTRL": 0x1D,
    "E": 0x12, "Q": 0x10, "R": 0x13, "F": 0x21, "TAB": 0x0F, "ESC": 0x01, "ENTER": 0x1C,
    "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05,
    "UP": 0xC8, "DOWN": 0xD0, "LEFT": 0xCB, "RIGHT": 0xCD,
}
MOUSE = {"MOUSE_LEFT", "MOUSE_RIGHT"}
ACTIONS = list(SCAN) + list(MOUSE) + ["NONE"]


# ── DirectInput input via SendInput (Windows) ──────────────────────────────
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


def _send_mouse_button(button: str, down: bool) -> None:
    import ctypes
    flags = {("MOUSE_LEFT", True): 0x0002, ("MOUSE_LEFT", False): 0x0004,
             ("MOUSE_RIGHT", True): 0x0008, ("MOUSE_RIGHT", False): 0x0010}[(button, down)]
    ctypes.windll.user32.mouse_event(flags, 0, 0, 0, 0)


def foreground_region() -> Optional[Tuple[int, int, int, int]]:
    """(left, top, width, height) of the focused window — so capture grabs the game, not the whole
    desktop (region capture is several times faster). None off Windows or on failure."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w, h = rect.right - rect.left, rect.bottom - rect.top
        if w <= 0 or h <= 0:
            return None
        return (rect.left, rect.top, w, h)
    except Exception:
        return None


def move_mouse_rel(dx: int, dy: int) -> None:
    """Relative mouse move (aiming) via SendInput — the raw motion games read, not SetCursorPos."""
    import ctypes
    ctypes.windll.user32.mouse_event(0x0001, int(dx), int(dy), 0, 0)   # MOUSEEVENTF_MOVE


def hold_key(action: str, down: bool) -> bool:
    """Press or release a key/mouse button and keep it held (for strafing, sprint, aim-down-sights)."""
    action = (action or "").strip().upper()
    if action in SCAN:
        _send_scancode(SCAN[action], down)
        return True
    if action in MOUSE:
        _send_mouse_button(action, down)
        return True
    return False


def press_action(action: str, hold: float = 0.12) -> bool:
    """Send one action as real DirectInput (tap). Returns True if it was a known action."""
    action = (action or "").strip().upper()
    if action in SCAN:
        _send_scancode(SCAN[action], True)
        time.sleep(hold)
        _send_scancode(SCAN[action], False)
        return True
    if action in MOUSE:
        _send_mouse_button(action, True)
        time.sleep(0.05)
        _send_mouse_button(action, False)
        return True
    return action == "NONE"


# ── fast screen capture (mss) + OpenCV perception ──────────────────────────
class FastCapture:
    """Grab frames as BGR numpy arrays with mss (tens-to-hundreds of fps), falling back to pyautogui.
    `region` is (left, top, width, height); None = primary monitor."""

    def __init__(self, region: Optional[Tuple[int, int, int, int]] = None):
        self.region = region
        self._sct = None
        self._mon = None

    def _ensure(self):
        if self._sct is not None:
            return
        import mss
        self._sct = mss.mss()
        if self.region:
            l, t, w, h = self.region
            self._mon = {"left": l, "top": t, "width": w, "height": h}
        else:
            self._mon = self._sct.monitors[1]

    def grab_bgr(self):
        """A BGR numpy array of the current frame (H, W, 3). mss returns BGRA natively, so we slice the
        first three channels with no colour conversion or reverse — the fast path for OpenCV."""
        import numpy as np
        self._ensure()
        assert self._sct is not None and self._mon is not None
        raw = self._sct.grab(self._mon)
        arr = np.frombuffer(raw.raw, dtype=np.uint8).reshape(raw.height, raw.width, 4)
        return arr[:, :, :3]                                # BGRA → BGR (view; OpenCV copies as needed)

    def grab_png(self) -> bytes:
        """PNG bytes of the current frame (for the vision model)."""
        import cv2
        ok, buf = cv2.imencode(".png", self.grab_bgr())
        return buf.tobytes() if ok else b""

    def close(self):
        try:
            if self._sct is not None:
                self._sct.close()
        except Exception:
            pass


class Perception:
    """Fast, model-free vision for reflex decisions — real OpenCV, works on numpy BGR frames."""

    @staticmethod
    def find_template(frame_bgr, template_bgr, threshold: float = 0.8) -> Optional[Tuple[int, int, float]]:
        """Best match of `template` in `frame`; returns (center_x, center_y, score) or None."""
        import cv2
        res = cv2.matchTemplate(frame_bgr, template_bgr, cv2.TM_CCOEFF_NORMED)
        import numpy as np
        _min, score, _minloc, maxloc = cv2.minMaxLoc(res)
        if score < threshold:
            return None
        th, tw = template_bgr.shape[:2]
        return (maxloc[0] + tw // 2, maxloc[1] + th // 2, float(score))

    @staticmethod
    def motion_center(prev_bgr, cur_bgr, min_area: int = 400) -> Optional[Tuple[int, int, float]]:
        """Centroid of the largest moving region between two frames (x, y, area) or None."""
        import cv2
        import numpy as np
        a = cv2.cvtColor(prev_bgr, cv2.COLOR_BGR2GRAY)
        b = cv2.cvtColor(cur_bgr, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(a, b)
        _t, mask = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=2)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return None
        c = max(cnts, key=cv2.contourArea)
        area = cv2.contourArea(c)
        if area < min_area:
            return None
        m = cv2.moments(c)
        if m["m00"] == 0:
            return None
        return (int(m["m10"] / m["m00"]), int(m["m01"] / m["m00"]), float(area))

    @staticmethod
    def color_mask_center(frame_bgr, lower_hsv, upper_hsv, min_area: int = 200):
        """Centroid of the largest region matching an HSV colour range (e.g. an enemy marker)."""
        import cv2
        import numpy as np
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array(lower_hsv), np.array(upper_hsv))
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return None
        c = max(cnts, key=cv2.contourArea)
        if cv2.contourArea(c) < min_area:
            return None
        m = cv2.moments(c)
        if m["m00"] == 0:
            return None
        return (int(m["m10"] / m["m00"]), int(m["m01"] / m["m00"]), float(cv2.contourArea(c)))


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
    fps: float = 0.0
    strategy_calls: int = 0


class GameAutopilot:
    """Observation (capture) is free; driving the game is the gated, warned action.

    Two layers, both optional and injectable (so tests need no game, model or display):
      * reflex(frame_bgr, prev_bgr) -> action|None — fast, runs every frame (CV-based).
      * decide(frame_png, game)     -> action      — the vision model, run every `strategy_every`s.
    With neither supplied, it uses the local vision model each frame (the original behaviour).
    """

    def __init__(self, hardware=None, decide: Optional[Callable] = None,
                 send: Optional[Callable[[str], bool]] = None, grab: Optional[Callable] = None,
                 reflex: Optional[Callable] = None, capture: Optional[FastCapture] = None,
                 model: str = "qwen3.5:4b"):
        self._hardware = hardware
        self._decide = decide
        self._send = send or press_action
        self._grab = grab
        self._reflex = reflex
        self._capture = capture
        self._model = model
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def available(self) -> bool:
        return os.name == "nt" and os.environ.get("TOM_DISABLE_UI_AUTOMATION") != "1"

    # ── capture ────────────────────────────────────────────────────────────
    def _fast(self) -> FastCapture:
        if self._capture is None:
            # capture the focused game window when we can — several times faster than the whole desktop
            self._capture = FastCapture(region=foreground_region())
        return self._capture

    def _grab_frame(self) -> Optional[bytes]:
        """PNG bytes for the vision model — mss first, then pyautogui/hardware."""
        if self._grab is not None:
            return self._grab()
        try:
            png = self._fast().grab_png()
            if png:
                return png
        except Exception:
            pass
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

    def _grab_bgr(self):
        """A BGR numpy frame for the reflex layer, or None if capture isn't available."""
        try:
            return self._fast().grab_bgr()
        except Exception:
            return None

    def _decide_action(self, frame: bytes, game: str) -> str:
        if self._decide is not None:
            return self._decide(frame, game)
        try:
            return _ollama_vision(frame, game, self._model)
        except Exception:
            return "NONE"

    # ── benchmark: measure the real achieved frame rate ────────────────────
    def benchmark(self, seconds: float = 2.0, with_reflex: bool = True) -> Dict[str, Any]:
        """Measure capture (and optional reflex) FPS on this machine — honest, no guessing."""
        frames, prev = 0, None
        end = time.monotonic() + max(0.3, seconds)
        t0 = time.monotonic()
        err = ""
        while time.monotonic() < end:
            bgr = self._grab_bgr()
            if bgr is None:
                err = "fast capture unavailable (mss/numpy); falling back to slow screenshots"
                break
            if with_reflex and self._reflex and prev is not None:
                try:
                    self._reflex(bgr, prev)
                except Exception:
                    pass
            prev = bgr
            frames += 1
        elapsed = max(1e-6, time.monotonic() - t0)
        fps = frames / elapsed
        return {"fps": round(fps, 1), "frames": frames, "seconds": round(elapsed, 2), "error": err}

    # ── the loop ─────────────────────────────────────────────────────────
    def play(self, game: str, seconds: float = 20.0, fps: float = 1.5, max_fail: int = 6,
             strategy_every: float = 1.0) -> AutopilotRun:
        """Bounded, stoppable game loop. If a reflex layer is set it runs every frame at capture speed,
        and the vision model (if any) only every `strategy_every` seconds to set the current goal."""
        from tom_core.policy.engine import get_policy
        run = AutopilotRun(game=game, seconds=seconds)
        self._stop.clear()
        hybrid = self._reflex is not None
        end = time.monotonic() + max(1.0, seconds)
        interval = 1.0 / max(0.2, (30.0 if hybrid else fps))
        fails = 0
        prev_bgr = None
        last_strategy = 0.0
        goal_action = "NONE"
        t0 = time.monotonic()
        while time.monotonic() < end:
            if self._stop.is_set():
                run.stopped_reason = "stopped by request"
                break
            if get_policy().halted:
                run.stopped_reason = "emergency stop"
                break
            if hybrid:
                bgr = self._grab_bgr()
                if bgr is None:
                    fails += 1
                    if fails >= max_fail:
                        run.stopped_reason = "could not capture the screen"
                        break
                    time.sleep(interval)
                    continue
                fails = 0
                run.frames += 1
                # reflex: fast, every frame
                reflex = self._reflex
                try:
                    act = reflex(bgr, prev_bgr) if reflex is not None else None
                except Exception:
                    act = None
                prev_bgr = bgr
                if act:
                    self._send(act)
                    run.actions.append(act)
                # strategy: the slow model, occasionally, to pick a standing goal
                now = time.monotonic()
                if (self._decide is not None or True) and now - last_strategy >= strategy_every:
                    last_strategy = now
                    try:
                        import cv2
                        ok, buf = cv2.imencode(".png", bgr)
                        if ok:
                            goal_action = self._decide_action(buf.tobytes(), game) or "NONE"
                            run.strategy_calls += 1
                            if goal_action != "NONE":
                                self._send(goal_action)
                                run.actions.append(goal_action)
                    except Exception:
                        pass
                time.sleep(interval)
            else:
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
        run.fps = round(run.frames / max(1e-6, time.monotonic() - t0), 1)
        if not run.stopped_reason:
            run.stopped_reason = "time elapsed"
        return run

    def start(self, game: str, seconds: float = 20.0, fps: float = 1.5) -> Dict[str, Any]:
        """Warn, get the owner's approval for this exact game, then run the loop and report honestly —
        including the measured frame rate, so "professional scale" is a number, not a claim."""
        if not self.available():
            return {"status": "error", "response_type": "game_autopilot",
                    "message": "The autopilot needs Windows with UI automation enabled."}
        bench = self.benchmark(1.0)
        from tom_core.policy.engine import ActionClass
        from tom_core.tools.guard import enforce
        warning = (
            f"Experimental game autopilot for '{game}'. Before you say yes, know:\n"
            f"  • Capture + perception run at ~{bench.get('fps', 0):g} fps here; the vision model sets "
            "goals a few times a second. Fast reflexes come from the CV layer, not the model.\n"
            "  • If this game has anti-cheat (most online games do), synthetic input can get your "
            "account BANNED.\n"
            f"  • It will drive the mouse/keyboard of the focused window for {seconds:g}s. Start and "
            "click into the game first.\n"
            "  • It won't magically play at a champion level — a generic engine gives fast, reliable "
            "control; winning a specific game needs tuning for it.\n"
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
                "fps": run.fps, "capture_fps": bench.get("fps", 0), "strategy_calls": run.strategy_calls,
                "message": (f"Autopilot for '{game}' finished ({run.stopped_reason}). Ran at ~{run.fps:g} "
                            f"fps, sent {did} input(s) over {run.frames} frame(s). Capture alone measured "
                            f"~{bench.get('fps', 0):g} fps. Experimental — tell me to stop any time, and "
                            "name the game if you want me to tune a strategy for it.")}
