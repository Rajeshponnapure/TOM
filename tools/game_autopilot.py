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

The state-aware loop that does the actual playing now lives in `tom_core/games` — perceive (what state is
this?), profile (what did this game do last time?), play_loop (act for that state, retry deaths) and
discover (which keys does it answer to?) — wired to a real window by `tools/game_play`. What remains
here is the plumbing those build on: capture, DirectInput, window focus, the KeyState holder, and the
strategy players used for games TOM made itself.
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

# Hardware scan codes (set 1) — what games read. Arrow keys are the E0-prefixed codes, sent with
# KEYEVENTF_EXTENDEDKEY. (The DirectInput DIK_ numbers 0xC8/0xD0/0xCB/0xCD are NOT scan codes; sending
# them made Windows drop the arrows.)
SCAN = {
    "W": 0x11, "A": 0x1E, "S": 0x1F, "D": 0x20, "SPACE": 0x39, "SHIFT": 0x2A, "CTRL": 0x1D,
    "E": 0x12, "Q": 0x10, "R": 0x13, "F": 0x21, "TAB": 0x0F, "ESC": 0x01, "ENTER": 0x1C,
    "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05,
    "UP": 0x48, "DOWN": 0x50, "LEFT": 0x4B, "RIGHT": 0x4D,
    "BACKSPACE": 0x0E, "END": 0x4F, "HOME": 0x47, "DELETE": 0x53, "T": 0x14, "SLASH": 0x35,
}
EXTENDED = {"UP", "DOWN", "LEFT", "RIGHT", "END", "HOME", "DELETE"}
MOUSE = {"MOUSE_LEFT", "MOUSE_RIGHT"}
ACTIONS = list(SCAN) + list(MOUSE) + ["NONE"]
# The actions TOM's own games use (tom_core.games) -> keys.
GAME_KEYS = {"up": "UP", "down": "DOWN", "left": "LEFT", "right": "RIGHT", "action": "SPACE", "restart": "ENTER"}


# ── input via SendInput (Windows) ──────────────────────────────────────────
_INPUT_TYPES: Dict[str, Any] = {}


def _input_types():
    """ctypes INPUT with the full union (MOUSEINPUT is the largest member). SendInput rejects a call
    whose cbSize isn't sizeof(INPUT) — 40 bytes on 64-bit — so a struct with only KEYBDINPUT sends
    nothing at all."""
    if _INPUT_TYPES:
        return _INPUT_TYPES
    import ctypes
    from ctypes import wintypes
    ulong_ptr = ctypes.c_size_t

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ulong_ptr)]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ulong_ptr)]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]

    class _U(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", _U)]

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    user32.SendInput.restype = wintypes.UINT
    _INPUT_TYPES.update(INPUT=INPUT, MOUSEINPUT=MOUSEINPUT, KEYBDINPUT=KEYBDINPUT, user32=user32, ctypes=ctypes)
    return _INPUT_TYPES


def _send(inp) -> bool:
    t = _input_types()
    sent = t["user32"].SendInput(1, t["ctypes"].byref(inp), t["ctypes"].sizeof(t["INPUT"]))
    return sent == 1


def _send_scancode(code: int, down: bool, extended: bool = False) -> bool:
    t = _input_types()
    flags = 0x0008 | (0x0001 if extended else 0) | (0 if down else 0x0002)   # SCANCODE | EXTENDED | KEYUP
    return _send(t["INPUT"](type=1, ki=t["KEYBDINPUT"](0, code, flags, 0, 0)))


def _send_mouse(flags: int, dx: int = 0, dy: int = 0) -> bool:
    t = _input_types()
    return _send(t["INPUT"](type=0, mi=t["MOUSEINPUT"](int(dx), int(dy), 0, flags, 0, 0)))


def scroll_wheel(notches: int) -> bool:
    """Mouse-wheel scroll at the cursor: negative = down. One notch = 120 (WHEEL_DELTA)."""
    t = _input_types()
    import ctypes
    data = ctypes.c_ulong(int(notches) * 120 & 0xFFFFFFFF).value
    return _send(t["INPUT"](type=0, mi=t["MOUSEINPUT"](0, 0, data, 0x0800, 0, 0)))


def _send_mouse_button(button: str, down: bool) -> bool:
    flags = {("MOUSE_LEFT", True): 0x0002, ("MOUSE_LEFT", False): 0x0004,
             ("MOUSE_RIGHT", True): 0x0008, ("MOUSE_RIGHT", False): 0x0010}[(button, down)]
    return _send_mouse(flags)


def set_dpi_aware() -> None:
    """Window rectangles and mss captures must use the same (physical) pixels on a scaled display."""
    if os.name != "nt":
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


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


def move_mouse_rel(dx: int, dy: int) -> bool:
    """Relative mouse move (aiming) via SendInput — the raw motion games read, not SetCursorPos."""
    return _send_mouse(0x0001, dx, dy)                                     # MOUSEEVENTF_MOVE


def hold_key(action: str, down: bool) -> bool:
    """Press or release a key/mouse button and keep it held (for strafing, sprint, aim-down-sights)."""
    action = (action or "").strip().upper()
    if action in SCAN:
        return _send_scancode(SCAN[action], down, action in EXTENDED)
    if action in MOUSE:
        return _send_mouse_button(action, down)
    return False


def press_action(action: str, hold: float = 0.12) -> bool:
    """Send one action as real input (tap). Returns True if it was a known action Windows accepted."""
    action = (action or "").strip().upper()
    if action in SCAN or action in MOUSE:
        ok = hold_key(action, True)
        time.sleep(hold if action in SCAN else 0.05)
        return hold_key(action, False) and ok
    return action == "NONE"


# ── the game's window ──────────────────────────────────────────────────────
def find_window(title: str) -> Optional[Tuple[int, str]]:
    """The visible top-level window whose title contains every word of `title` (best = shortest)."""
    if os.name != "nt":
        return None
    from tools.system_control import _match_window, _windows
    matches = _match_window(title, _windows())
    return min(matches, key=lambda m: len(m[1])) if matches else None


def focus_window(hwnd: int) -> bool:
    """Bring a window to the front. Windows blocks focus stealing unless the caller just had input, so
    tap Alt first (the standard workaround) and restore it if minimised."""
    if os.name != "nt":
        return False
    import ctypes
    user32 = ctypes.windll.user32
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)                                         # SW_RESTORE
    user32.keybd_event(0x12, 0, 0, 0)
    user32.SetForegroundWindow(hwnd)
    user32.keybd_event(0x12, 0, 2, 0)
    time.sleep(0.15)
    if int(user32.GetForegroundWindow() or 0) == int(hwnd):
        return True
    # second way: join the input queue of the window in front, then hand focus over
    kernel32 = ctypes.windll.kernel32
    front = user32.GetForegroundWindow()
    theirs = user32.GetWindowThreadProcessId(front, None) if front else 0
    ours = kernel32.GetCurrentThreadId()
    attached = bool(theirs) and theirs != ours and bool(user32.AttachThreadInput(ours, theirs, True))
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetFocus(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(ours, theirs, False)
    time.sleep(0.15)
    return int(user32.GetForegroundWindow() or 0) == int(hwnd)


def is_foreground(hwnd: int) -> bool:
    if os.name != "nt":
        return False
    import ctypes
    return int(ctypes.windll.user32.GetForegroundWindow() or 0) == int(hwnd)


def client_region(hwnd: int) -> Optional[Tuple[int, int, int, int]]:
    """Screen (left, top, width, height) of the window's drawing area — no title bar or borders."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None
    origin = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(origin))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    return (origin.x, origin.y, w, h) if w > 0 and h > 0 else None


class KeyState:
    """Holds exactly the keys a strategy asks for: presses new ones, releases dropped ones, taps taps.
    release_all() lets go of everything (on stop, focus loss or error) so no key is left stuck down."""

    def __init__(self, send: Optional[Callable[[str, bool], bool]] = None, keymap: Optional[Dict[str, str]] = None):
        self._send = send or hold_key
        self.keymap = keymap or GAME_KEYS
        self.down: set = set()
        self.sent = 0

    def apply(self, hold, tap=()) -> None:
        want = {self.keymap[a] for a in hold if a in self.keymap}
        for key in sorted(self.down - want):
            self._send(key, False)
        for key in sorted(want - self.down):
            self._send(key, True)
            self.sent += 1
        self.down = want
        for action in tap:
            key = self.keymap.get(action)
            if key and key not in self.down:
                self._send(key, True)
                time.sleep(0.03)
                self._send(key, False)
                self.sent += 1

    def release_all(self) -> None:
        for key in sorted(self.down):
            self._send(key, False)
        self.down = set()


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
def _ollama_vision(image_bytes: bytes, game: str, model: str, goal: str = "") -> str:
    base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    aim = f"Your task: {goal}. Choose the single best next action toward that task." if goal else \
        "Choose the single best next action to make progress or survive."
    prompt = (f"You are playing the video game '{game}'. Look at this frame. {aim} "
              f"Reply with ONLY one token from this list: "
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


# ── playing a real game window ─────────────────────────────────────────────
class VisionExplorer:
    """For games TOM didn't make (no manifest): the local vision model picks a key every `every`
    seconds — asked in the background so the loop never stalls — and the key is held until the next
    decision, with a slow look-around on the mouse. Honest about what it is: exploration, not mastery."""

    def __init__(self, game: str, decide: Callable[[bytes, str], str], every: float = 1.0):
        from concurrent.futures import ThreadPoolExecutor
        self.game, self.decide, self.every = game, decide, every
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.pending: Any = None
        self.current = "W"
        self.asked_at = 0.0
        self.decisions: List[str] = []
        self.turn = 0

    def act(self, frame):
        from tom_core.games.strategies import Move
        now = time.monotonic()
        if self.pending is not None and self.pending.done():
            try:
                token = (self.pending.result() or "NONE").upper()
            except Exception:
                token = "NONE"
            self.pending = None
            self.current = token if token != "NONE" else "W"
            self.decisions.append(token)
        if self.pending is None and now - self.asked_at >= self.every:
            self.asked_at = now
            try:
                import cv2
                ok, buf = cv2.imencode(".jpg", frame[::2, ::2], [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ok:
                    self.pending = self.pool.submit(self.decide, buf.tobytes(), self.game)
            except Exception:
                pass
        self.turn += 1
        move = Move(hold={self.current} if self.current in SCAN or self.current in MOUSE else set())
        move.look = (6 if (self.turn // 90) % 2 == 0 else -6, 0)
        return move

    def close(self):
        self.pool.shutdown(wait=False, cancel_futures=True)


def _activity(prev, cur) -> float:
    """Share of pixels that changed noticeably between two frames (cheap: every 4th pixel)."""
    import numpy as np
    if prev is None or cur is None or prev.shape != cur.shape:
        return 0.0
    a, b = prev[::4, ::4].astype(np.int16), cur[::4, ::4].astype(np.int16)
    return float(np.mean(np.max(np.abs(a - b), axis=2) > 24))


def wait_for_window(title: str, timeout: float = 20.0, poll: float = 0.5) -> Optional[Tuple[int, str]]:
    end = time.monotonic() + timeout
    while True:
        hit = find_window(title)
        if hit or time.monotonic() >= end:
            return hit
        time.sleep(poll)


def _window_alive(hwnd: int) -> bool:
    if os.name != "nt":
        return False
    import ctypes
    return bool(ctypes.windll.user32.IsWindow(hwnd))


def play_window(hwnd: int, player, seconds: float, keys: KeyState, stop: Optional[threading.Event] = None,
                max_fps: float = 60.0) -> Dict[str, Any]:
    """Drive one window: capture its client area, ask `player.act(frame)` what to press, press it.

    Input goes ONLY to this window: if anything else comes to the front, every key is released and the
    loop pauses (re-focusing at most once a second) — so the autopilot never types into another app.
    Ends on time, stop, the emergency stop, or the window closing. Keys are always released at the end."""
    from tom_core.policy.engine import get_policy
    set_dpi_aware()
    stop = stop or threading.Event()
    stats: Dict[str, Any] = {"frames": 0, "paused_s": 0.0, "refocus": 0, "activity": 0.0, "stopped": "time elapsed"}
    cap: Optional[FastCapture] = None
    region = None
    region_at = 0.0
    prev = None
    activity_sum = 0.0
    last_refocus = 0.0
    interval = 1.0 / max_fps
    t0 = time.monotonic()
    end = t0 + max(1.0, seconds)
    try:
        while time.monotonic() < end:
            tick = time.monotonic()
            if stop.is_set():
                stats["stopped"] = "stopped by request"
                break
            if get_policy().halted:
                stats["stopped"] = "emergency stop"
                break
            if not _window_alive(hwnd):
                stats["stopped"] = "the game window closed"
                break
            if not is_foreground(hwnd):
                keys.release_all()
                if tick - last_refocus > 1.0:
                    last_refocus = tick
                    stats["refocus"] += 1
                    focus_window(hwnd)
                time.sleep(0.1)
                stats["paused_s"] += time.monotonic() - tick
                continue
            if cap is None or tick - region_at > 1.0:             # follow the window if it moves
                now_region = client_region(hwnd)
                region_at = tick
                if now_region and now_region != region:
                    if cap is not None:
                        cap.close()
                    region, cap = now_region, FastCapture(region=now_region)
            if cap is None:
                time.sleep(0.1)
                continue
            frame = cap.grab_bgr()
            stats["frames"] += 1
            activity_sum += _activity(prev, frame)
            prev = frame.copy()
            move = player.act(frame)
            if not is_foreground(hwnd):                             # focus changed while we were looking
                continue
            keys.apply(move.hold, move.tap)
            look = getattr(move, "look", None)
            if look:
                move_mouse_rel(*look)
            spare = interval - (time.monotonic() - tick)
            if spare > 0:
                time.sleep(spare)
    finally:
        keys.release_all()
        if cap is not None:
            cap.close()
    elapsed = max(1e-6, time.monotonic() - t0)
    stats.update(seconds=round(elapsed, 1), fps=round(stats["frames"] / elapsed, 1), inputs=keys.sent,
                 activity=round(activity_sum / max(1, stats["frames"] - 1), 3), paused_s=round(stats["paused_s"], 1))
    return stats


def _read_stats(path: str) -> Dict[str, Any]:
    try:
        with open(os.path.join(path, "stats.json"), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def play_made_game(manifest: Dict[str, Any], seconds: float = 30.0, stop: Optional[threading.Event] = None,
                   launch: Optional[Callable[[str], Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Play a game TOM made: start it if it isn't open, focus it, play by sight with the game's own
    strategy, then read the score the game itself recorded (stats.json) — the proof of how it went."""
    from tom_core.games import strategies, studio
    title, path = manifest.get("window_title") or manifest["title"], manifest.get("path", "")
    player = strategies.for_manifest(manifest)
    if player is None:
        return {"status": "error", "response_type": "game_autopilot",
                "message": f"I don't have a playing strategy for '{manifest.get('genre')}' games yet."}
    hit = find_window(title)
    started = False
    if hit is None:
        res = (launch or studio.GameStudio.launch)(path)
        if res.get("status") != "success":
            return {"status": "error", "response_type": "game_autopilot",
                    "message": res.get("message", f"Couldn't start {title}.")}
        started = True
        hit = wait_for_window(title, 25.0)
        if hit is None:
            return {"status": "error", "response_type": "game_autopilot",
                    "message": f"Started {title}, but its window never appeared."}
    hwnd = hit[0]
    if not focus_window(hwnd):
        time.sleep(0.5)
        focus_window(hwnd)
    before = _read_stats(path) if path else {}
    run = play_window(hwnd, player, seconds, KeyState(), stop=stop)
    time.sleep(2.2)                                                  # the game saves stats every ~2 s
    after = _read_stats(path) if path else {}
    fresh = after.get("updated", 0) > before.get("updated", 0)
    played = {k: after.get(k) for k in ("score", "best", "rounds")} if fresh else {}
    ok = run["frames"] > 0 and run["inputs"] > 0
    msg = (f"Played {title} for {run['seconds']:g}s at ~{run['fps']:g} fps by sight, pressing keys {run['inputs']} "
           f"time(s)" + (f". The game recorded score {played['score']}, best {played['best']} over "
                         f"{played['rounds']} round(s)." if played else ".")
           + (f" Paused {run['paused_s']:g}s while another window was in front." if run["paused_s"] else "")
           + f" Stopped: {run['stopped']}.")
    return {"status": "success" if ok else "error", "response_type": "game_autopilot", "game": title,
            "started": started, "run": run, "game_stats": played, "verified": bool(played) and ok, "message": msg}

def play_installed_game(name: str, seconds: float = 30.0, stop: Optional[threading.Event] = None,
                        model: str = "qwen3.5:4b", decide: Optional[Callable[..., str]] = None,
                        launch_wait: float = 150.0, goal: str = "", **options) -> Dict[str, Any]:
    """Play a game TOM didn't make, toward a goal, using the state-aware loop.

    Kept as the stable entry point the agent calls; the loop itself — perception, per-game memory,
    control discovery and retries — lives in tom_core/games so it can be tested with no window at all.
    """
    from tools.game_play import play_live
    return play_live(name, seconds, stop, model, decide, launch_wait, goal, **options)
