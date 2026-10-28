"""The game brain: look at the screen, understand it, decide, act, check what happened — toward a goal.

The older layers either react (play_loop: classify the screen as menu/dead/gameplay and apply a rule) or
ask a vision model for one key token with no context. Neither *understands an interface*: neither can
read "Play → Create New → World name → Create" off a menu and walk through it, type a world name, or
notice that the last click did nothing and try something else.

This module is that missing layer:

    observe (frame + every piece of text on it, with ids and positions)
      → think (vision model: what is this screen, what is the plan, what is the ONE next action — as JSON)
      → validate (deterministic: the element exists, the key is allowed, no buying/passwords, not a
                  repeat of something that just did nothing)
      → act (through a backend: a PC window, or an Android emulator over ADB)
      → check (did the screen change? what changed?) → remember → repeat

What it learns is kept per game ("on the 'Play / Settings' screen, clicking 'Play' led to the worlds
list"), so the next session starts with that knowledge.

Fast reflexes are not this layer's job. A vision model takes ~1-5 s per look, which is fine for menus,
building, navigating and turn-based play and far too slow for aiming in a firefight. For that the brain
can hand control to the reflex player for a few seconds (`autoplay`) or put the crosshair on a target it
sees (`aim`), then look again. It never claims to play a fast 3D shooter like a skilled person.

The model never decides policy: what may be clicked or typed is checked here, in code, every step.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from tom_core.games import perceive

Box = Tuple[int, int, int, int]            # x, y, w, h in frame pixels

PC_KEYS = ("W", "A", "S", "D", "SPACE", "SHIFT", "CTRL", "E", "Q", "R", "F", "TAB", "ESC", "ENTER",
           "1", "2", "3", "4", "UP", "DOWN", "LEFT", "RIGHT", "MOUSE_LEFT", "MOUSE_RIGHT", "T", "BACKSPACE")
TOUCH_KEYS = ("ENTER", "BACK", "ESC", "SPACE", "TAB", "UP", "DOWN", "LEFT", "RIGHT", "BACKSPACE", "HOME")

PC_ACTIONS = ("click", "double_click", "type", "key", "hold", "look", "aim", "autoplay", "wait", "done", "give_up")
TOUCH_ACTIONS = ("click", "double_click", "type", "key", "hold", "swipe", "aim", "wait", "done", "give_up")

MAX_TYPE = 80                    # characters per "type" action
MAX_HOLD = 6.0                   # seconds a key/touch may be held per step
MAX_WAIT = 10.0
MAX_AUTOPLAY = 30.0
MAX_LOOK = 900                   # pixels of mouse movement per look

# Things TOM never clicks on its own, whatever the model says: spending money, accounts, real-world
# consequences. The owner can do these by hand.
_FORBIDDEN_CLICK = re.compile(
    r"\b(?:buy|purchase|pay|checkout|subscribe|subscription|redeem|top ?up|recharge|unlock (?:now|for)|"
    r"get premium|go premium|add (?:a )?card|sign ?in|log ?in|sign ?up|register|create account|"
    r"delete (?:world|account|save)|reset (?:world|progress)|uninstall)\b"
    r"|[$€£₹]\s?\d|\d\s?(?:usd|inr|eur|gbp)\b|\bminecoins?\b",
    re.IGNORECASE)
# Screens where typing is refused (credentials, payment, human checks).
_SENSITIVE_SCREEN = re.compile(
    r"\bpassword\b|\bpasscode\b|\bcard number\b|\bcvv\b|\bcvc\b|\bexpiry\b|\bbilling\b|\bupi\b|\botp\b|"
    r"\bcaptcha\b|\bi'?m not a robot\b|\bverify (?:you|that you) are human\b",
    re.IGNORECASE)


# ── what is on the screen ─────────────────────────────────────────────────
@dataclass
class Element:
    id: int
    text: str
    box: Box

    @property
    def center(self) -> Tuple[int, int]:
        x, y, w, h = self.box
        return x + w // 2, y + h // 2


@dataclass
class Screen:
    """One look at the game: the image, the text on it, and the coarse state."""
    frame: Any                                  # BGR numpy array, or None in tests that only use text
    width: int
    height: int
    elements: List[Element] = field(default_factory=list)
    state: str = "static"
    activity: float = 0.0
    png: bytes = b""

    def text(self) -> str:
        return "\n".join(e.text for e in self.elements)

    def element(self, eid: Any) -> Optional[Element]:
        try:
            eid = int(eid)
        except (TypeError, ValueError):
            return None
        return next((e for e in self.elements if e.id == eid), None)

    def title(self, n: int = 3) -> str:
        """A short name for this screen: its first few words of text, top to bottom."""
        words = [e.text for e in self.elements[:n]]
        return " / ".join(words) if words else f"({self.state}, no text)"


def elements_from_lines(lines: Sequence[Any], max_elements: int = 40) -> List[Element]:
    """Turn OCR lines into clickable elements.

    Tesseract groups one screen row into one line, so a menu row "Play   Settings   Store" would be a
    single target. Words are split into separate elements wherever the gap between them is wider than
    the text is tall — the spacing that separates buttons, not words.
    """
    out: List[Element] = []
    for line in lines:
        words = [w for w in getattr(line, "words", []) if str(getattr(w, "text", "")).strip()]
        if not words:
            continue
        words.sort(key=lambda w: w.box[0])
        group = [words[0]]
        groups = []
        for w in words[1:]:
            prev = group[-1]
            gap = w.box[0] - (prev.box[0] + prev.box[2])
            height = max(prev.box[3], w.box[3], 8)
            if gap > max(14, 1.5 * height):
                groups.append(group)
                group = [w]
            else:
                group.append(w)
        groups.append(group)
        for g in groups:
            text = " ".join(str(w.text).strip() for w in g).strip()
            if len(text) < 2 and not text.isalnum():
                continue                              # OCR crumbs: stray punctuation
            if not re.search(r"[A-Za-z0-9]", text):
                continue
            x0 = min(w.box[0] for w in g)
            y0 = min(w.box[1] for w in g)
            x1 = max(w.box[0] + w.box[2] for w in g)
            y1 = max(w.box[1] + w.box[3] for w in g)
            out.append(Element(0, text[:60], (x0, y0, x1 - x0, y1 - y0)))
    out.sort(key=lambda e: (e.box[1] // 12, e.box[0]))
    out = out[:max_elements]
    for i, e in enumerate(out, 1):
        e.id = i
    return out


# ── what the brain may do ─────────────────────────────────────────────────
@dataclass
class Decision:
    action: Dict[str, Any]
    see: str = ""
    plan: str = ""
    expect: str = ""
    raw: str = ""


@dataclass
class Step:
    n: int
    screen: str                 # screen title before acting
    state: str
    action: str                 # human-readable
    ok: bool                    # the action was sent
    changed: bool               # the screen visibly changed afterwards
    note: str = ""

    def line(self) -> str:
        effect = "screen changed" if self.changed else "NO visible change"
        if not self.ok:
            effect = f"NOT DONE: {self.note}"
        return f"{self.n}. [{self.screen}] {self.action} -> {effect}"


def describe_action(action: Dict[str, Any], screen: Optional[Screen] = None) -> str:
    t = action.get("type", "?")
    if t in ("click", "double_click"):
        el = screen.element(action.get("element")) if screen is not None and "element" in action else None
        if el is not None:                          # by its text: ids are renumbered on every screen
            return f'{t} "{el.text}"'
        if "x" in action:
            return f"{t} at ({_pct(action.get('x'))}, {_pct(action.get('y'))})"
        return f"{t} element {action.get('element')}"
    if t == "type":
        return f'type "{action.get("text", "")}"'
    if t == "key":
        return f"press {action.get('key')}"
    if t == "hold":
        what = "+".join(action.get("keys") or []) or f"touch at ({_pct(action.get('x'))}, {_pct(action.get('y'))})"
        return f"hold {what} {action.get('seconds', 1)}s"
    if t == "look":
        return f"look dx={action.get('dx', 0)} dy={action.get('dy', 0)}"
    if t == "aim":
        return f"aim at ({_pct(action.get('x'))}, {_pct(action.get('y'))})" + (" and fire" if action.get("fire") else "")
    if t == "swipe":
        return (f"swipe ({_pct(action.get('x'))}, {_pct(action.get('y'))}) -> "
                f"({_pct(action.get('x2'))}, {_pct(action.get('y2'))})")
    if t in ("wait", "autoplay"):
        return f"{t} {action.get('seconds', 1)}s"
    if t == "done":
        return "done: " + str(action.get("evidence", ""))[:80]
    if t == "give_up":
        return "give up: " + str(action.get("reason", ""))[:80]
    return t


def _pct(v: Any) -> str:
    try:
        return f"{float(v) * 100:.0f}%"
    except (TypeError, ValueError):
        return "?"


def _frac(v: Any) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f > 1.0 and f <= 100.0:               # the model answered in percent
        f /= 100.0
    return f if 0.0 <= f <= 1.0 else None


def signature(action: Dict[str, Any], screen: Screen) -> str:
    """What makes two actions 'the same move' for repeat detection."""
    t = action.get("type")
    if t in ("click", "double_click"):
        el = screen.element(action.get("element"))
        if el is not None:
            return f"{t}:{el.text.lower()}"
        x, y = _frac(action.get("x")), _frac(action.get("y"))
        return f"{t}:{round((x or 0) * 20)}:{round((y or 0) * 20)}"
    if t == "key":
        return f"key:{str(action.get('key', '')).upper()}"
    if t == "type":
        return f"type:{action.get('text', '')}"
    if t == "hold":
        return "hold:" + "+".join(sorted(str(k).upper() for k in action.get("keys") or []))
    return str(t)


class Guard:
    """The rules the model cannot change. Returns (cleaned action, None) or (None, reason)."""

    def __init__(self, platform: str = "pc", allow: Sequence[str] = ()):
        self.platform = platform
        self.actions = PC_ACTIONS if platform == "pc" else TOUCH_ACTIONS
        self.keys = PC_KEYS if platform == "pc" else TOUCH_KEYS
        self.allow = {a for a in allow if a in self.actions}

    def check(self, action: Any, screen: Screen, banned: Sequence[str] = ()) -> Tuple[Optional[Dict[str, Any]], str]:
        if not isinstance(action, dict):
            return None, "the reply had no action object"
        t = str(action.get("type", "")).strip().lower()
        if t not in self.actions:
            return None, f"'{t or '?'}' is not an action I can do here (allowed: {', '.join(self.actions)})"
        a: Dict[str, Any] = {"type": t}

        needs_point = t in ("click", "double_click", "aim", "swipe") or (t == "hold" and self.platform != "pc")
        if needs_point:
            target = self._point(action, screen)
            if isinstance(target, str):
                return None, target
            a.update(target)
            if t in ("click", "double_click"):
                reason = self._forbidden_at(a, screen)
                if reason:
                    return None, reason
        if t == "aim":
            a["fire"] = bool(action.get("fire", True))
        if t == "swipe":
            x2, y2 = _frac(action.get("x2")), _frac(action.get("y2"))
            if x2 is None or y2 is None:
                return None, "a swipe needs x2 and y2 between 0 and 1"
            a.update(x2=x2, y2=y2, seconds=_clamp(action.get("seconds", 0.4), 0.05, 3.0))
        if t == "type":
            text = str(action.get("text", ""))
            if not text or len(text) > MAX_TYPE or any(ord(c) < 32 for c in text):
                return None, f"text to type must be 1-{MAX_TYPE} printable characters on one line"
            if _SENSITIVE_SCREEN.search(screen.text()):
                return None, "this screen asks for a password, payment or a human check — I don't type there"
            a["text"] = text
        if t == "key":
            key = _norm_key(action.get("key"))
            if key not in self.keys:
                return None, f"key '{action.get('key')}' isn't allowed (keys: {', '.join(self.keys)})"
            a["key"] = key
        if t == "hold":
            a["seconds"] = _clamp(action.get("seconds", 1.0), 0.05, MAX_HOLD)
            if self.platform == "pc":
                keys = [_norm_key(k) for k in (action.get("keys") or ([action["key"]] if action.get("key") else []))]
                if not keys or any(k not in self.keys for k in keys) or len(keys) > 3:
                    return None, f"hold needs 1-3 keys from: {', '.join(self.keys)}"
                a["keys"] = keys
        if t == "look":
            a["dx"] = int(_clamp(action.get("dx", 0), -MAX_LOOK, MAX_LOOK))
            a["dy"] = int(_clamp(action.get("dy", 0), -MAX_LOOK, MAX_LOOK))
            if not a["dx"] and not a["dy"]:
                return None, "look needs a non-zero dx or dy"
        if t == "wait":
            a["seconds"] = _clamp(action.get("seconds", 1.0), 0.2, MAX_WAIT)
        if t == "autoplay":
            if "autoplay" not in self.allow:
                return None, "the fast reflex player isn't available for this game"
            a["seconds"] = _clamp(action.get("seconds", 8.0), 2.0, MAX_AUTOPLAY)
        if t == "done":
            a["evidence"] = str(action.get("evidence", ""))[:200]
        if t == "give_up":
            a["reason"] = str(action.get("reason", ""))[:200]
        if signature(a, screen) in banned:
            return None, "that exact move did nothing the last times — choose a different one"
        return a, ""

    @staticmethod
    def _point(action: Dict[str, Any], screen: Screen):
        if action.get("element") not in (None, ""):
            el = screen.element(action.get("element"))
            if el is None:
                return f"there is no element #{action.get('element')} on this screen"
            cx, cy = el.center
            return {"element": el.id, "x": cx / max(1, screen.width), "y": cy / max(1, screen.height)}
        x, y = _frac(action.get("x")), _frac(action.get("y"))
        if x is None or y is None:
            return "give an element id, or x and y as fractions of the screen (0-1)"
        return {"x": x, "y": y}

    @staticmethod
    def _forbidden_at(a: Dict[str, Any], screen: Screen) -> str:
        px, py = a["x"] * screen.width, a["y"] * screen.height
        for el in screen.elements:
            x, y, w, h = el.box
            pad = max(6, h // 2)
            inside = (x - pad <= px <= x + w + pad) and (y - pad <= py <= y + h + pad)
            if (inside or el.id == a.get("element")) and _FORBIDDEN_CLICK.search(el.text):
                return (f'I don\'t click "{el.text}" myself (money, accounts or deleting progress) — '
                        "that's yours to do by hand")
        return ""


def _norm_key(k: Any) -> str:
    key = str(k or "").strip().upper().replace(" ", "_")
    return {"RETURN": "ENTER", "ESCAPE": "ESC", "SPACEBAR": "SPACE", "LMB": "MOUSE_LEFT", "LEFT_CLICK": "MOUSE_LEFT",
            "RMB": "MOUSE_RIGHT", "RIGHT_CLICK": "MOUSE_RIGHT", "LSHIFT": "SHIFT", "CONTROL": "CTRL",
            "ARROWUP": "UP", "ARROWDOWN": "DOWN", "ARROWLEFT": "LEFT", "ARROWRIGHT": "RIGHT",
            "ARROW_UP": "UP", "ARROW_DOWN": "DOWN", "ARROW_LEFT": "LEFT", "ARROW_RIGHT": "RIGHT",
            "DELETE": "BACKSPACE", "DEL": "BACKSPACE"}.get(key, key)


def _clamp(v: Any, lo: float, hi: float) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        f = lo
    return max(lo, min(hi, f))


# ── the model's view of the moment ────────────────────────────────────────
def build_prompt(game: str, goal: str, screen: Screen, history: Sequence[Step], platform: str,
                 lessons: Sequence[str] = (), controls: Optional[Dict[str, str]] = None,
                 warning: str = "", allow_autoplay: bool = False) -> str:
    keys = PC_KEYS if platform == "pc" else TOUCH_KEYS
    lines = [f'You are TOM, playing the game "{game}" on {"a PC" if platform == "pc" else "an Android touch screen"}.',
             f"GOAL: {goal}",
             "Work toward the goal one action at a time. Understand the screen first: is it a menu, a "
             "loading screen, a dialog, a text field, or gameplay? Read the buttons and pick the one that "
             "leads toward the goal."]
    if lessons:
        lines.append("What you learned about this game before:")
        lines += [f"  - {x}" for x in list(lessons)[-10:]]
    if controls:
        lines.append("Controls that answered in this game: " + ", ".join(f"{r}={k}" for r, k in controls.items()))
    if history:
        lines.append("Your recent steps (oldest first):")
        lines += [f"  {s.line()}" for s in list(history)[-8:]]
    if warning:
        lines.append(f"WARNING: {warning}")
    lines.append(f"The screen looks like: {screen.state}. Text on it (id: text @ position as % of width, height):")
    if screen.elements:
        for e in screen.elements:
            cx, cy = e.center
            lines.append(f'  #{e.id} "{e.text}" @ ({100 * cx / max(1, screen.width):.0f}%, '
                         f"{100 * cy / max(1, screen.height):.0f}%)")
    else:
        lines.append("  (no readable text — use the image)")
    acts = [
        '{"type":"click","element":3}  click a button/text by its id',
        '{"type":"click","x":0.52,"y":0.31}  click a point (fractions 0-1) — icons without text',
        '{"type":"type","text":"My World"}  type into the field that has focus (click the field first)',
        '{"type":"key","key":"ENTER"}  press one key. Keys: ' + ", ".join(keys),
    ]
    if platform == "pc":
        acts += ['{"type":"hold","keys":["W"],"seconds":2}  hold keys to move or act (max 6s)',
                 '{"type":"look","dx":300,"dy":0}  turn the camera with the mouse',
                 '{"type":"aim","x":0.6,"y":0.45,"fire":true}  put the crosshair on a target you can see and attack']
        if allow_autoplay:
            acts.append('{"type":"autoplay","seconds":10}  let the fast reflex player move/fight, then look again')
    else:
        acts += ['{"type":"hold","x":0.15,"y":0.8,"seconds":2}  press and hold a point (joystick, use button)',
                 '{"type":"swipe","x":0.6,"y":0.5,"x2":0.8,"y2":0.5,"seconds":0.4}  swipe (turn the camera, scroll)',
                 '{"type":"aim","x":0.6,"y":0.45}  tap on a target you can see']
    acts += ['{"type":"wait","seconds":3}  wait (loading, animations)',
             '{"type":"done","evidence":"what on screen proves the goal is met"}',
             '{"type":"give_up","reason":"why it cannot be done"}']
    lines.append("Actions:")
    lines += [f"  {a}" for a in acts]
    lines.append("Rules: never buy anything, sign in, or type passwords or payment details — give_up instead. "
                 "If an action did nothing, do something different. Only say done when the screen shows it.")
    lines.append('Reply with ONLY this JSON: {"see":"what the screen shows","plan":"your next 2-3 steps",'
                 '"action":{...},"expect":"what should change"}')
    return "\n".join(lines)


def parse_decision(text: str) -> Optional[Decision]:
    """The model's reply as a Decision, or None when it isn't usable."""
    from tom_core.llm_json import parse_model_json
    try:
        data = parse_model_json(text or "")
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    action = data.get("action")
    if isinstance(action, str):                      # {"action":"click","element":2}
        action = {k: v for k, v in data.items() if k not in ("see", "plan", "expect")}
        action["type"] = data["action"]
    if not isinstance(action, dict) and "type" in data:
        action = {k: v for k, v in data.items() if k not in ("see", "plan", "expect")}
    if not isinstance(action, dict):
        return None
    return Decision(action=action, see=str(data.get("see", ""))[:300], plan=str(data.get("plan", ""))[:300],
                    expect=str(data.get("expect", ""))[:200], raw=(text or "")[:1000])


# ── the backend: eyes and hands ───────────────────────────────────────────
class BrainBackend:
    """What the brain needs from the outside world. Real ones wrap a PC window or an ADB device; tests
    wrap a scripted fake game, so the whole loop runs with no game, no model and no display."""

    platform = "pc"
    can_autoplay = False                 # True when autoplay() hands over to a fast reflex player

    def ready(self) -> bool:
        return True

    def observe(self) -> Optional[Screen]:
        raise NotImplementedError

    def act(self, action: Dict[str, Any], screen: Screen) -> Tuple[bool, str]:
        """Do one validated action. (sent, note)."""
        raise NotImplementedError

    def autoplay(self, seconds: float) -> str:
        return "not available"

    def close(self) -> None:
        pass

    def wait(self, seconds: float) -> None:
        time.sleep(seconds)


def changed_between(before: Screen, after: Screen) -> bool:
    """Whether an action had a visible effect: pixels moved, or the text on screen is different."""
    if before.frame is not None and after.frame is not None:
        try:
            if perceive.frame_activity(before.frame, after.frame) > perceive.STILL:
                return True
        except Exception:
            pass
    a = {e.text.lower() for e in before.elements}
    b = {e.text.lower() for e in after.elements}
    if a != b and (a or b):
        diff = len(a ^ b) / max(1, len(a | b))
        return diff >= 0.25
    return False


# ── the session ───────────────────────────────────────────────────────────
@dataclass
class BrainResult:
    game: str
    goal: str
    steps: List[Step] = field(default_factory=list)
    outcome: str = "stopped"             # done | gave_up | stuck | time | steps | stopped | model | lost
    goal_met: bool = False               # the model said done AND something was actually done
    verified: bool = False               # an independent check (the screen's own words) confirmed it
    evidence: str = ""
    evidence_path: str = ""
    model_calls: int = 0
    invalid: int = 0
    seconds: float = 0.0
    lessons: List[str] = field(default_factory=list)
    last_see: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {"game": self.game, "goal": self.goal, "outcome": self.outcome, "goal_met": self.goal_met,
                "verified": self.verified, "evidence": self.evidence, "evidence_path": self.evidence_path,
                "steps": [s.line() for s in self.steps], "model_calls": self.model_calls,
                "invalid_replies": self.invalid, "seconds": round(self.seconds, 1), "lessons": self.lessons}


Think = Callable[[str, bytes], str]


class GameBrain:
    """Plays toward a goal by understanding each screen. `think(prompt, png) -> reply text` is the
    vision model; injectable so tests and other providers plug in."""

    def __init__(self, backend: BrainBackend, think: Think, game: str, goal: str, *,
                 lessons: Sequence[str] = (), controls: Optional[Dict[str, str]] = None,
                 max_steps: int = 60, seconds: float = 300.0, stop=None,
                 check_goal: Optional[Callable[[Screen, float], bool]] = None,
                 on_step: Optional[Callable[[Step, Decision], None]] = None,
                 evidence_dir: str = ""):
        self.backend = backend
        self.think = think
        self.game = game
        self.goal = goal or "play the game"
        self.lessons = list(lessons)
        self.controls = controls or {}
        self.max_steps = max_steps
        self.seconds = seconds
        self.stop = stop
        self.check_goal = check_goal
        self.on_step = on_step
        self.evidence_dir = evidence_dir
        allow = ("autoplay",) if getattr(backend, "can_autoplay", False) else ()
        self.guard = Guard(backend.platform, allow=allow)

    def _stopped(self) -> bool:
        return bool(self.stop is not None and self.stop.is_set())

    def run(self) -> BrainResult:
        res = BrainResult(self.game, self.goal)
        start = time.monotonic()
        history: List[Step] = []
        banned: Dict[str, int] = {}             # signature -> steps it stays banned
        repeats: Dict[str, int] = {}            # signature -> consecutive no-effect uses
        idle = 0                                # consecutive steps with no visible change
        bad_replies = 0
        warning = ""
        not_ready = 0
        screen: Optional[Screen] = None
        try:
            for n in range(1, self.max_steps + 1):
                if self._stopped():
                    res.outcome = "stopped"
                    break
                if time.monotonic() - start > self.seconds:
                    res.outcome = "time"
                    break
                if not self.backend.ready():
                    not_ready += 1
                    if not_ready > 20:
                        res.outcome = "lost"
                        break
                    self.backend.wait(0.5)
                    continue
                not_ready = 0
                screen = self.backend.observe()
                if screen is None:
                    res.outcome = "lost"
                    break
                if self.check_goal is not None and self.check_goal(screen, time.monotonic() - start):
                    res.outcome, res.goal_met, res.verified = "done", True, True
                    res.evidence = "the screen itself shows the goal: " + screen.title(5)
                    break

                prompt = build_prompt(self.game, self.goal, screen, history, self.backend.platform,
                                      self.lessons + res.lessons, self.controls, warning,
                                      allow_autoplay="autoplay" in self.guard.allow)
                res.model_calls += 1
                try:
                    reply = self.think(prompt, screen.png)
                except Exception as exc:
                    reply = ""
                    warning = f"(the last look failed: {exc})"
                decision = parse_decision(reply)
                if decision is None:
                    res.invalid += 1
                    bad_replies += 1
                    if bad_replies >= 4:
                        res.outcome = "model"
                        break
                    warning = "your last reply was not the JSON asked for. Reply with ONLY the JSON object."
                    continue
                bad_replies = 0
                res.last_see = decision.see or res.last_see

                action, why = self.guard.check(decision.action, screen, [s for s, left in banned.items() if left > 0])
                for sig in list(banned):
                    banned[sig] -= 1
                    if banned[sig] <= 0:
                        del banned[sig]
                if action is None:
                    res.invalid += 1
                    step = Step(n, screen.title(), screen.state, describe_action(decision.action, screen), False, False, why)
                    history.append(step)
                    res.steps.append(step)
                    warning = why
                    if self.on_step:
                        self.on_step(step, decision)
                    continue
                warning = ""

                kind = action["type"]
                if kind == "done":
                    res.outcome = "done"
                    res.goal_met = any(s.ok for s in res.steps)      # credit only for work actually done
                    res.evidence = action.get("evidence", "") or decision.see
                    res.evidence_path = self._save_evidence(screen)
                    res.steps.append(Step(n, screen.title(), screen.state, describe_action(action), True, False))
                    break
                if kind == "give_up":
                    res.outcome = "gave_up"
                    res.evidence = action.get("reason", "")
                    res.evidence_path = self._save_evidence(screen)
                    res.steps.append(Step(n, screen.title(), screen.state, describe_action(action), True, False))
                    break

                desc = describe_action(action, screen)
                if kind == "autoplay":
                    note = self.backend.autoplay(action["seconds"])
                    ok = True
                elif kind == "wait":
                    self.backend.wait(action["seconds"])
                    ok, note = True, ""
                else:
                    try:
                        ok, note = self.backend.act(action, screen)
                    except Exception as exc:
                        ok, note = False, f"input failed: {exc}"
                self.backend.wait(0.35 if kind in ("click", "double_click", "key", "type") else 0.1)
                after = self.backend.observe() if ok else None
                changed = bool(after is not None and changed_between(screen, after))
                step = Step(n, screen.title(), screen.state, desc, ok, changed, note)
                history.append(step)
                res.steps.append(step)
                if self.on_step:
                    self.on_step(step, decision)

                sig = signature(action, screen)
                if ok and not changed and kind not in ("wait", "autoplay", "hold", "look", "aim"):
                    repeats[sig] = repeats.get(sig, 0) + 1
                    if repeats[sig] >= 2:
                        banned[sig] = 4
                        repeats[sig] = 0
                        warning = f'"{desc}" did nothing twice, so it is blocked for a few steps. Try another way.'
                else:
                    repeats.pop(sig, None)
                idle = 0 if changed else idle + 1
                if idle >= 10:
                    res.outcome = "stuck"
                    break
                if changed and after is not None and kind in ("click", "double_click", "key", "type"):
                    self._learn(res, screen, after, desc)
            else:
                res.outcome = "steps"
        finally:
            res.seconds = time.monotonic() - start
            self.backend.close()
        if res.outcome == "done" and not res.verified and self.check_goal is not None and screen is not None:
            res.verified = bool(self.check_goal(screen, res.seconds))
        return res

    def _learn(self, res: BrainResult, before: Screen, after: Screen, desc: str) -> None:
        if before.title() == after.title() and before.state == after.state:
            return
        lesson = f'On "{before.title()}": {desc} led to "{after.title()}"'
        if lesson not in res.lessons and lesson not in self.lessons:
            res.lessons.append(lesson)

    def _save_evidence(self, screen: Screen) -> str:
        if not self.evidence_dir or not screen.png:
            return ""
        try:
            os.makedirs(self.evidence_dir, exist_ok=True)
            slug = re.sub(r"[^a-z0-9]+", "-", self.game.lower()).strip("-") or "game"
            path = os.path.join(self.evidence_dir, f"{slug}-{time.strftime('%Y%m%d-%H%M%S')}.png")
            with open(path, "wb") as fh:
                fh.write(screen.png)
            return path
        except OSError:
            return ""


def report(res: BrainResult) -> str:
    """What TOM tells the owner: what it did, whether the goal was met, and how sure that is."""
    acted = [s for s in res.steps if s.ok]
    head = {
        "done": ("I reached the goal" if res.goal_met else
                 "The vision model says the goal was already met before I did anything"),
        "gave_up": "I stopped: " + (res.evidence or "it can't be done from here"),
        "stuck": "I stopped: ten moves in a row changed nothing on screen",
        "time": "Time ran out before the goal",
        "steps": "I used all my moves before the goal",
        "stopped": "Stopped as you asked",
        "model": "I stopped: the vision model wasn't giving usable answers (is a vision model installed in Ollama?)",
        "lost": "I stopped: the game window went away or wouldn't stay in front",
    }.get(res.outcome, res.outcome)
    msg = f'{head} — "{res.goal}" in {res.game}: {len(acted)} action(s) in {res.seconds:.0f}s.'
    if res.outcome == "done" and res.goal_met:
        msg += (" Confirmed by the game's own on-screen words." if res.verified else
                f" This is the vision model's reading of the screen ({res.evidence or 'no detail given'}), "
                "not an independent check — glance at the game to confirm.")
    if res.evidence_path:
        msg += f" Screenshot: {res.evidence_path}."
    if acted:
        tail = "; ".join(s.action for s in acted[-4:])
        msg += f" Last moves: {tail}."
    if res.lessons:
        msg += f" I learned {len(res.lessons)} thing(s) about its screens for next time."
    return msg


def save_lessons(profile, lessons: Sequence[str], keep: int = 30) -> None:
    """Merge new lessons into a GameProfile (newest kept)."""
    current = list(getattr(profile, "lessons", []) or [])
    for x in lessons:
        if x in current:
            current.remove(x)
        current.append(x)
    profile.lessons = current[-keep:]


VISION_MODELS = ("qwen3.5:9b", "qwen3.5:4b", "qwen2.5vl:7b", "qwen2.5vl:3b", "gemma3:12b", "gemma3:4b",
                 "llama3.2-vision", "minicpm-v", "llava")


def pick_vision_model(installed: Sequence[str], preferred: str = "") -> str:
    """The best installed vision model: TOM_VISION_MODEL / `preferred` if installed, else the first of
    VISION_MODELS that is. '' when none is."""
    names = [n.lower() for n in installed]

    def have(want: str) -> str:
        want = want.lower()
        return next((n for n in names if n == want or n.startswith(want + ":") or n.split(":")[0] == want), "")
    for want in [m for m in (os.environ.get("TOM_VISION_MODEL", ""), preferred) if m] + list(VISION_MODELS):
        got = have(want)
        if got:
            return got
    return ""


def installed_models(base: str = "", timeout: float = 5.0) -> Optional[List[str]]:
    """Models Ollama has installed, or None when Ollama isn't reachable."""
    import urllib.request
    url = (base or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/") + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except Exception:
        return None
    return [m.get("name", "") for m in data.get("models", []) if m.get("name")]


def vision_ready(model: str = "", installed: Optional[Sequence[str]] = None) -> Tuple[bool, str]:
    """(True, model) when a vision model can be used, else (False, what to do about it)."""
    names = installed if installed is not None else installed_models()
    if names is None:
        return False, "Ollama isn't running, so I have no vision model to understand the game's screen. Start Ollama and ask again."
    chosen = pick_vision_model(names, model)
    if not chosen:
        return False, ("To understand a game's screen I need a vision model in Ollama, and none is installed. "
                       "Install one, e.g.  ollama pull qwen2.5vl:7b  (or qwen2.5vl:3b on a smaller GPU), and ask again.")
    return True, chosen


def ollama_think(model: str, base: str = "", timeout: float = 120.0, max_width: int = 1024) -> Think:
    """A `think` function backed by a local Ollama vision model, asked for JSON."""
    import base64
    import urllib.request
    url = (base or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/") + "/api/generate"

    def think(prompt: str, png: bytes) -> str:
        body: Dict[str, Any] = {"model": model, "prompt": prompt, "stream": False, "format": "json",
                                "options": {"temperature": 0.2, "num_predict": 320}}
        if png:
            body["images"] = [base64.b64encode(_shrink_png(png, max_width)).decode()]
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read()).get("response", "")
    return think


def _shrink_png(png: bytes, max_width: int) -> bytes:
    """Smaller images make a local vision model several times faster; text stays readable at ~1024 px."""
    try:
        import cv2
        import numpy as np
        img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
        if img is None or img.shape[1] <= max_width:
            return png
        scale = max_width / img.shape[1]
        img = cv2.resize(img, (max_width, int(img.shape[0] * scale)), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".png", img)
        return buf.tobytes() if ok else png
    except Exception:
        return png


def screen_from_frame(frame, read_lines: Optional[Callable[[Any], Sequence[Any]]] = None,
                      prev=None, ocr_text: Optional[str] = None) -> Screen:
    """Build a Screen from a BGR frame: OCR elements (frame-relative), coarse state, PNG for the model."""
    h, w = (frame.shape[0], frame.shape[1]) if frame is not None else (0, 0)
    elements: List[Element] = []
    if read_lines is not None and frame is not None:
        try:
            elements = elements_from_lines(read_lines(frame))
        except Exception:
            elements = []
    activity = perceive.frame_activity(prev, frame) if prev is not None and frame is not None else 0.0
    text = ocr_text if ocr_text is not None else "\n".join(e.text for e in elements)
    state = perceive.classify(text, activity).state
    png = b""
    if frame is not None:
        try:
            import cv2
            ok, buf = cv2.imencode(".png", frame)
            png = buf.tobytes() if ok else b""
        except Exception:
            png = b""
    return Screen(frame, w, h, elements, state, activity, png)


def ocr_reader():
    """read_lines(frame) using TOM's Tesseract OCR, with boxes relative to the frame."""
    from tom_core.screen_control import ScreenControl
    holder: Dict[str, Any] = {}

    def grab(_region):
        from PIL import Image
        f = holder["frame"]
        return Image.fromarray(f[:, :, ::-1].copy())       # BGR -> RGB

    sc = ScreenControl(grab=grab)

    def read(frame):
        ok, _why = sc.available()
        if not ok:
            return []
        holder["frame"] = frame
        return sc.read(None)
    return read
