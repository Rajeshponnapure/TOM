"""What TOM remembers about each game — so the second session starts where the first one ended.

There is no way to "just know" how an arbitrary game works. A game's controls, the keys that actually do
something, the words its menus and death screen use — those are facts about *that* game, and the only
honest way to get them is to look and try. This module is where those facts live between runs:

    controls    the keys that visibly did something when pressed, and what role they play
    states      how often each screen state was seen (menu, gameplay, dead …)
    sessions    how many times it has been played, how many attempts died, and the best result
    notes       short factual observations ("the menu needs ENTER", "screen froze after 40s")

A profile is plain JSON in the workspace, so it can be read, edited or deleted by the owner. Nothing is
invented: the profile starts empty and only records what a session actually measured.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

KINDS = ("action", "survival", "driving", "turnbased", "command", "unknown")

# What is known before ever running a game: its window, which kind of game it is (that decides HOW it is
# played), and the keys worth testing first. The bindings themselves are deliberately NOT listed — they
# are discovered, because guessing them and being wrong is worse than not knowing.
KNOWN: Dict[str, Dict[str, Any]] = {
    "spider man 2": {"window": "Spider-Man", "kind": "action",
                     "candidates": ["W", "A", "S", "D", "SPACE", "SHIFT", "E", "F", "R", "V", "TAB",
                                    "1", "2", "MOUSE_LEFT", "MOUSE_RIGHT"]},
    "green hell": {"window": "Green Hell", "kind": "survival",
                   "candidates": ["W", "A", "S", "D", "SPACE", "SHIFT", "E", "F", "Q", "TAB",
                                  "1", "2", "3", "MOUSE_LEFT", "MOUSE_RIGHT"]},
    "over the hill": {"window": "over the hill", "kind": "driving",
                      "candidates": ["W", "A", "S", "D", "SPACE", "SHIFT", "CTRL", "E", "1", "2"]},
    # BlueStacks games are tapped, not typed: the only controls are on-screen buttons.
    "ludo king": {"window": "BlueStacks App Player", "kind": "turnbased", "candidates": [],
                  "click_words": ["roll", "roll dice", "play", "continue", "ok", "collect", "next",
                                  "yes", "spin", "confirm"]},
    "minecraft": {"window": "BlueStacks App Player", "kind": "command",
                  "candidates": ["W", "A", "S", "D", "SPACE", "SHIFT", "E", "TAB", "1", "2",
                                 "MOUSE_LEFT"]},
}

DEFAULT_CANDIDATES = ["W", "A", "S", "D", "SPACE", "SHIFT", "E", "F", "ENTER", "ESC", "TAB",
                      "1", "2", "MOUSE_LEFT"]
MOVEMENT = {"W", "A", "S", "D", "UP", "DOWN", "LEFT", "RIGHT"}


def _norm(text: str) -> str:
    text = re.sub(r"[™®©]", "", text or "").lower()
    text = re.sub(r"\b(marvel'?s|the)\b", " ", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def known_for(game: str) -> Dict[str, Any]:
    """Built-in knowledge for a game, matched loosely ("Marvel's Spider-Man 2" → "spider man 2")."""
    n = _norm(game)
    for key, info in KNOWN.items():
        k = _norm(key)                       # "over the hill" normalises to "over hill", same as the query
        if k == n or (k and all(w in n.split() for w in k.split())):
            return info
    return {}


def candidates_for(game: str) -> List[str]:
    return list(known_for(game).get("candidates") or DEFAULT_CANDIDATES)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "game").lower()).strip("-") or "game"


def _dir() -> str:
    explicit = os.environ.get("TOM_GAME_PROFILE_DIR")
    if explicit:
        return explicit
    from tools.project_paths import workspace_path
    return str(workspace_path("game_profiles"))


def path_for(game: str) -> str:
    return os.path.join(_dir(), f"{slug(game)}.json")


@dataclass
class GameProfile:
    game: str
    window: str = ""
    kind: str = "unknown"
    controls: Dict[str, str] = field(default_factory=dict)          # role → key, learned
    responsive: Dict[str, float] = field(default_factory=dict)      # key → how much the screen changed
    click_words: List[str] = field(default_factory=list)            # on-screen buttons, for tapped games
    colors: Dict[str, List[int]] = field(default_factory=dict)      # role → RGB, learned from the screen
    genre: str = ""                                                 # learned type (breakout/shooter/…)
    states: Dict[str, int] = field(default_factory=dict)            # state → times seen
    sessions: int = 0
    deaths: int = 0
    goal_met: int = 0
    best: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    probed: bool = False
    probes: int = 0                                                 # how many times keys were tried
    updated: str = ""

    def forward(self) -> Optional[str]:
        return self.controls.get("forward")

    def to_dict(self) -> Dict[str, Any]:
        return {**self.__dict__}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameProfile":
        keep = {k: v for k, v in (data or {}).items() if k in cls.__dataclass_fields__}
        return cls(**keep)


def load(game: str) -> GameProfile:
    """The saved profile for `game`, or a fresh one seeded with what is known about that game."""
    info = known_for(game)
    profile = GameProfile(game=game, window=info.get("window", ""), kind=info.get("kind", "unknown"),
                          click_words=list(info.get("click_words") or []))
    try:
        with open(path_for(game), encoding="utf-8") as fh:
            saved = json.load(fh)
    except (OSError, ValueError):
        return profile
    if not isinstance(saved, dict):
        return profile
    stored = GameProfile.from_dict(saved)
    stored.game = game
    # built-in knowledge fills the gaps; the game's own measurements always win
    stored.window = stored.window or profile.window
    stored.kind = stored.kind if stored.kind in KINDS and stored.kind != "unknown" else profile.kind
    stored.click_words = stored.click_words or profile.click_words
    return stored


def save(profile: GameProfile) -> str:
    profile.updated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path = path_for(profile.game)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(profile.to_dict(), fh, indent=2)
    os.replace(tmp, path)
    return path


def roles_from(responsive: Dict[str, float], threshold: float = 0.004,
               relative: float = 0.25) -> Dict[str, str]:
    """Turn "these keys changed the screen" into roles. Only what the measurements support: the movement
    key with the strongest effect is forward, the most responsive other key is the interact key.

    `relative` matters: a small window or a sparse game changes far fewer pixels than a full-screen 3D
    game, so a fixed cutoff found nothing in a real window (measured 2026-10-28: Viper scored 0.012-0.019
    for every key that worked). A key counts if it is within a quarter of the best one."""
    if not responsive:
        return {}
    top = max(responsive.values())
    floor = max(threshold, top * relative)
    ranked = sorted(((k, v) for k, v in responsive.items() if v >= floor),
                    key=lambda kv: kv[1], reverse=True)
    roles: Dict[str, str] = {}
    move = [k for k, _ in ranked if k in MOVEMENT]
    if move:
        roles["forward"] = move[0]
    rest = [k for k, _ in ranked if k not in MOVEMENT and k not in ("ENTER", "ESC", "TAB")]
    for role, key in zip(("action", "interact", "secondary"), rest):
        roles[role] = key
    return roles


def record(game: str, result: Dict[str, Any]) -> GameProfile:
    """Fold one session's measured result into the profile and save it."""
    profile = load(game)
    profile.sessions += 1
    states = result.get("states") or {}
    for state, count in states.items():
        profile.states[state] = profile.states.get(state, 0) + int(count)
    profile.deaths += int(result.get("deaths") or 0)
    if result.get("goal_met"):
        profile.goal_met += 1
    seconds = float(result.get("seconds_played") or 0.0)
    if seconds > float(profile.best.get("seconds") or 0):
        profile.best["seconds"] = round(seconds, 1)
    if result.get("goal") and result.get("goal_met"):
        profile.best["goal"] = result["goal"]
    for note in (result.get("notes") or [])[-4:]:
        if note not in profile.notes:
            profile.notes.append(note)
    profile.notes = profile.notes[-12:]
    save(profile)
    return profile


def describe(profile: GameProfile) -> str:
    """One sentence a person can check: what TOM actually knows about this game so far."""
    bits = []
    if profile.controls:
        bits.append("keys that work: " + ", ".join(f"{role}={key}" for role, key in profile.controls.items()))
    else:
        bits.append("controls not discovered yet")
    if profile.sessions:
        bits.append(f"played {profile.sessions} time(s), {profile.deaths} death(s), "
                    f"{profile.goal_met} goal(s) met")
    if profile.best.get("seconds"):
        bits.append(f"best session {profile.best['seconds']:g}s")
    return f"{profile.game} ({profile.kind}): " + "; ".join(bits)
