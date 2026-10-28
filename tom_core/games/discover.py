"""Find out which keys a game actually responds to, instead of assuming a control scheme.

A game's bindings are a fact about that game. Guessing "W moves forward" and being wrong is worse than
not knowing: the autopilot would hold a key that does nothing and report that it played. So on the first
session with an unfamiliar game, TOM presses each candidate key once, measures how much of the screen
changed because of it, and records the answer.

That is a real measurement, and it has real limits worth stating:

* Only *visible* reactions count. A key that opens an invisible state (crouch, walk) scores zero and is
  recorded as unresponsive — honest, not magic.
* Probing presses keys in a live game, so it is short and skips ESC/TAB/ENTER, which open menus and
  consoles rather than acting in the world.
* The result is saved per game, so it is paid for once and reused on every later session.
"""
from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional

from tom_core.games import perceive, profile as profile_mod

# Keys that navigate the game's UI rather than act in its world — never probed by pressing them blindly.
SKIP = {"ESC", "TAB", "ENTER"}
# A key whose press changed under this share of the screen did nothing visible.
MIN_EFFECT = 0.004


def probe(press: Callable[[str], bool], frame: Callable, keys: List[str], settle: float = 0.35,
          wait: Callable[[float], None] = time.sleep) -> Dict[str, float]:
    """Press each key once, measure the screen change it caused. Returns {key: activity}."""
    scores: Dict[str, float] = {}
    for key in keys:
        wait(settle)                                    # let the game settle before the "before" frame
        before = frame()
        if before is None:
            break                                       # window gone: stop and keep what was measured
        if not press(key):
            continue
        wait(settle)
        after = frame()
        if after is None:
            break
        scores[key] = round(perceive.frame_activity(before, after), 4)
    return scores


def learn(game: str, press: Callable[[str], bool], frame: Callable, keys: Optional[List[str]] = None,
          settle: float = 0.35, wait: Callable[[float], None] = time.sleep,
          save: bool = True) -> profile_mod.GameProfile:
    """Probe a game's keys and store what answered. The profile is returned even if nothing responded."""
    prof = profile_mod.load(game)
    wanted = [k for k in (keys or profile_mod.candidates_for(game)) if k.upper() not in SKIP]
    scores = probe(press, frame, wanted, settle=settle, wait=wait)
    prof.responsive = {k: v for k, v in scores.items() if v >= MIN_EFFECT}
    prof.controls = profile_mod.roles_from(scores)
    # only a game that answered counts as learned: if nothing responded we were probably still in a
    # menu or loading, so the next session should try again rather than trust a useless result
    prof.probed = bool(prof.responsive)
    prof.probes += 1
    dead = sorted(k for k, v in scores.items() if v < MIN_EFFECT)
    if prof.controls:
        prof.notes.append("found working keys: "
                          + ", ".join(f"{role}={key}" for role, key in prof.controls.items()))
    if dead:
        prof.notes.append("no visible effect: " + ", ".join(dead))
    prof.notes = prof.notes[-12:]
    if save:
        profile_mod.save(prof)
    return prof


def describe(prof: profile_mod.GameProfile) -> str:
    """What the probe found, in one checkable sentence."""
    if not prof.probes:
        return f"I haven't tested {prof.game}'s controls yet."
    if not prof.responsive:
        return (f"None of the keys I tried visibly did anything in {prof.game} — it may be a tapped "
                "game, or the game may need to be in its window and loaded first.")
    working = ", ".join(f"{key} ({score:g})" for key, score in
                        sorted(prof.responsive.items(), key=lambda kv: kv[1], reverse=True))
    return f"In {prof.game} these keys visibly did something: {working}."
