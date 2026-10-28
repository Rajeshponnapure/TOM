"""Read what state a game is in from the screen: loading, menu, paused, gameplay or dead.

Before this, the autopilot pressed the same keys whether the game was showing its main menu, a loading
screen or the death overlay. That is why it looked like it was playing but achieved nothing: most of a
session could be spent holding W at a menu.

Two cheap, independent signals do the work:

* **motion** — the share of pixels that changed since the last frame. A still screen is a menu, a
  loading screen or a freeze; a moving one is gameplay (or a cutscene).
* **on-screen words** — the game's own text, read with OCR. "You died", "Game over", "Press any key",
  "Resume", "Loading" are the game telling us its state in plain words.

Text wins when it is there (it is unambiguous); motion decides when a game has no readable text, which
is common in 3D games. Nothing here touches the game's memory or files — only its pixels.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

STATES = ("loading", "menu", "paused", "gameplay", "dead", "static")

# Checked in this order: a death screen also offers "Continue", so never let menu words win over death.
_DEAD = re.compile(
    r"\byou (?:died|are dead|have died|were killed)\b|\bgame over\b|\bwasted\b|\bmission failed\b"
    r"|\brespawn\b|\bdefeated\b|\bsee you in hell\b|\btry again\b|\bdead\.", re.IGNORECASE)
_PAUSE = re.compile(r"\bpaused\b|\bresume\b|\bquit to (?:menu|desktop|main menu)\b|\boptions\b",
                    re.IGNORECASE)
_MENU = re.compile(
    r"\bpress (?:any key|space|enter|to start)\b|\bmain menu\b|\bnew game\b|\bcontinue\b"
    r"|\bload game\b|\bsingle ?player\b|\bmultiplayer\b|\bstart game\b|\bplay\b|\bquit\b"
    r"|\bsettings\b|\bsign in\b|\bclick to (?:play|start)\b", re.IGNORECASE)
_LOADING = re.compile(r"\bloading\b|\bplease wait\b|\bconnecting\b|\bcompiling\b|\bpreparing\b"
                      r"|\bshader\b|\bsyncing\b", re.IGNORECASE)
# Words that mean the goal was reached, used by the play loop's success check.
WIN = re.compile(
    r"\byou (?:win|won)\b|\bvictory\b|\blevel complete\b|\blevel (?:passed|cleared)\b|\bwell done\b"
    r"|\bfinished (?:1st|first)\b|\b1st place\b|\bwinner\b|\bcongratulations\b|\bgoal!\b", re.IGNORECASE)

STILL = 0.004          # below this share of changed pixels the screen is not moving


@dataclass
class Observation:
    state: str
    activity: float
    text: str = ""
    detail: str = ""

    @property
    def moving(self) -> bool:
        return self.activity >= STILL


def frame_activity(prev, cur, step: int = 4, threshold: int = 24) -> float:
    """Share of sampled pixels that changed noticeably between two BGR frames (0.0 – 1.0)."""
    if prev is None or cur is None or getattr(prev, "shape", None) != getattr(cur, "shape", None):
        return 0.0
    import numpy as np
    a, b = prev[::step, ::step].astype(np.int16), cur[::step, ::step].astype(np.int16)
    return float(np.mean(np.max(np.abs(a - b), axis=2) > threshold))


def words(text: str) -> List[str]:
    return [w for w in re.split(r"[^a-z0-9']+", (text or "").lower()) if w]


def classify(text: str, activity: float) -> Observation:
    """The state, from on-screen words first and motion second."""
    t = text or ""
    if _DEAD.search(t):
        return Observation("dead", activity, t, "the game says the attempt is over")
    if _LOADING.search(t):
        return Observation("loading", activity, t, "the game says it is loading")
    if _PAUSE.search(t):
        return Observation("paused", activity, t, "a pause menu is showing")
    if _MENU.search(t):
        return Observation("menu", activity, t, "a menu is showing")
    if activity < STILL:
        return Observation("static", activity, t, "the screen is not moving and shows no state")
    return Observation("gameplay", activity, t, "")


class Perceiver:
    """Observes frames and reports the game's state. `read_text` is an OCR callable (slow — the loop
    only calls it now and then and reuses the last reading in between)."""

    def __init__(self, read_text: Optional[Callable[[], str]] = None, history: int = 4):
        self.read_text = read_text
        self.history = max(1, history)
        self._recent: List[float] = []
        self._last_frame = None

    def read(self) -> str:
        if self.read_text is None:
            return ""
        try:
            return self.read_text() or ""
        except Exception:
            return ""

    def observe(self, frame, text: Optional[str] = None) -> Observation:
        """One look. `text` lets the caller pass a cached OCR reading instead of paying for a new one."""
        activity = frame_activity(self._last_frame, frame)
        self._last_frame = frame
        self._recent = (self._recent + [activity])[-self.history:]
        # a single still frame can be a hitch; judge a menu only when the screen has been still for a bit
        quiet = sum(self._recent) / len(self._recent)
        obs = classify(self.read() if text is None else text, quiet)
        # report the smoothed value: one hitchy frame should not turn gameplay into a "frozen" screen
        obs.activity = round(quiet, 4)
        if obs.state == "gameplay" and not obs.moving:
            obs.state, obs.detail = "static", "the screen stopped moving"
        return obs

    def reset(self) -> None:
        self._recent, self._last_frame = [], None


def summarise(observations: List[Observation]) -> Dict[str, int]:
    """How many looks landed in each state — the evidence a session actually did something."""
    counts: Dict[str, int] = {}
    for o in observations:
        counts[o.state] = counts.get(o.state, 0) + 1
    return counts
