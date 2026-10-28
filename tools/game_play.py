"""Playing a real, installed game: the window, the input, and the goal loop wired together.

`tom_core/games/play_loop.py` decides *what* to do; this module is the part that touches the machine —
capture the game's window, press its keys, click its on-screen buttons, and first find out which keys it
even answers to. The safety rule is the same one the older explorer had, and it is the important one:
input goes only to the game's own window. If anything else comes to the front, keys are released and the
loop pauses until the game is in front again; nothing is ever typed into another app.
"""
from __future__ import annotations

import asyncio
import re
import time
from typing import Any, Callable, Dict, Optional, Tuple

from tom_core.games import brain as brain_mod
from tom_core.games import discover, learn_colors, play_loop
from tom_core.games import profile as profile_mod

# Keys probed on the first session with an unfamiliar game — a few, so the test is quick and reversible.
PROBE_LIMIT = 6
# Frames captured for the colour-learning pass, and how long to hold each direction.
LEARN_FRAMES = 40
LEARN_GAP = 0.05
LEARN_BLOCK = 5                 # taps per direction before swapping: a game that glides (snake, runner)
#                 dies if driven one way for whole phase, so directions alternate in blocks.
LEARN_STILL = 2e-4              # share of pixels that may change between captures and still count as still
LEARN_STILL_RUNS = 3            # consecutive still captures before the pass tries to revive the game
LEARN_REVIVES = 6               # revive attempts before giving up: a game that freezes in ~1s needs more


def learning_keys(prof) -> Tuple[str, str]:
    """The two keys to hold while learning which colour TOM controls.

    Left/right is what makes the answer unambiguous: the thing that moves left when left is held and
    right when right is held is the player. Prefers A/D when they answered the probe, then the two most
    responsive keys the game did answer to.
    """
    known = [k for k in ("A", "D") if k in (prof.responsive or {})]
    if len(known) == 2:
        return known[0], known[1]
    ranked = [k for k, _ in sorted((prof.responsive or {}).items(), key=lambda kv: kv[1], reverse=True)
              if k not in ("ENTER", "ESC", "TAB")]
    if len(ranked) >= 2:
        return ranked[0], ranked[1]
    if known:
        return known[0], known[0]
    return ("A", "D")


def revive_keys_for(left: str, right: str, prof) -> Tuple[str, ...]:
    """Keys to tap when the learning pass finds a frozen screen (dead, paused, a menu).

    Ordered most-restart-like first. Movement keys are excluded — tapping them cannot revive a death.
    """
    rank = ["R", "ENTER", "SPACE", "E", "Q", "F", "TAB", "SHIFT", "CTRL", "1", "2", "3", "4"]
    responsive = [k for k in (getattr(prof, "responsive", None) or {})
                  if k not in (left, right, "ESC", "UP", "DOWN", "W", "S")]
    ordered = [k for k in rank if k in responsive]
    ordered += sorted(set(responsive) - set(ordered), key=str)
    if not ordered:
        return ("R", "ENTER")                     # nothing known: the two safe restart keys only
    return tuple(ordered + [k for k in rank if k not in ordered])[:4]


def pairs_for_learning(prof, left: str, right: str) -> Tuple[Tuple[str, str, str], ...]:
    """The probe pairs for the colour-learning pass: a horizontal pair, then a vertical one.

    Both axes are needed because a game can be built so that one of them never answers: measured live
    on Viper (2026-10-28), the snake glides right from spawn and rejects the left key (that would mean
    reversing) while the right key changes nothing — its turns answer only the vertical pair. The
    vertical pair prefers the most responsive vertical keys the probe found, else W/S.
    """
    vertical = sorted(((k, v) for k, v in (getattr(prof, "responsive", None) or {}).items()
                       if k in ("W", "S", "UP", "DOWN") and k not in (left, right)),
                      key=lambda kv: kv[1], reverse=True)
    if len(vertical) >= 2:
        up, down = vertical[0][0], vertical[1][0]
    else:
        up, down = "W", "S"
    return ((left, right, "x"), (up, down, "y"))


def collect_for_learning(backend, press, frames: int = LEARN_FRAMES,
                         gap: float = LEARN_GAP, left: str = "A", right: str = "D",
                         tap: float = 0.03, revive: Tuple[str, ...] = ("R", "ENTER"),
                         pairs: Optional[Tuple[Tuple[str, str, str], ...]] = None):
    """Capture frames while probing key pairs alternating by blocks, so the player colour can be
    identified by response.

    `pairs` is an ordered list of (key_neg, key_pos, axis) — axis "x" or "y". Omitted: one left/right
    pass, labelled as plain ints (the original behaviour). Later pairs are labelled ("y", ±1) tuples,
    which the response statistic reads back.

    Four behaviours this pass needed on a real game, all discovered live on Viper (2026-10-28):

    * *Taps, not a continuous hold*: in a game where holding a direction walks into a wall, a two-second
      hold killed the avatar halfway through the pass and the rest of the frames were a death screen.
    *    * *Reviving a frozen screen*: the pass often starts in the middle of a death (the game was already
      playing itself before TOM began — Viper freezes about 1.1 s after launch). Restart-ish keys are
      tried *one at a time*, and only the next one if the screen is still frozen: on Viper the first key
      (R) revived it, and tapping a second key afterwards killed the round again.
    * *Both axes*: the snake rejected left/right entirely (see tom_core.games.learn_colors) — its turns
      answer W/S, so probing one axis produces the false conclusion "nothing answers the keys".
    """
    import numpy as np
    shots, pressed = [], []
    prev = None

    def changed(a, b):
        if a is None or b is None:
            return 1.0
        return float((np.max(np.abs(b.astype(np.int16) - a.astype(np.int16)), axis=2) > 25).mean())

    still = 0
    revived = 0
    if not pairs:
        pairs = ((left, right, "x"),)
    per_pair = max(LEARN_BLOCK, frames // max(1, len(pairs)))
    try:
        for i in range(frames):
            key_neg, key_pos, axis = pairs[min(i // per_pair, len(pairs) - 1)]
            direction = -1 if (i // LEARN_BLOCK) % 2 == 0 else 1
            key = key_neg if direction < 0 else key_pos
            press({key})
            time.sleep(tap)
            press(set())
            time.sleep(gap)
            shot = backend.frame()
            if shot is None:
                break
            if changed(prev, shot) <= LEARN_STILL:
                still += 1
            else:
                still = 0
            prev = shot
            if still >= LEARN_STILL_RUNS and revived < LEARN_REVIVES and i < frames - LEARN_STILL_RUNS:
                revived += 1
                wake = False
                for rk in revive:
                    press({rk})
                    time.sleep(tap)
                    press(set())
                    # give the game a moment; frames observed here are labelled 0: unknown input.
                    # A death *flash* changes one capture and freezes again, so only two consecutive
                    # changing captures count as revived — measured live, one-change tests false-wake.
                    last, runs = prev, 0
                    wake = False
                    for _ in range(6):
                        time.sleep(gap)
                        after = backend.frame()
                        if after is None:
                            break
                        runs = runs + 1 if changed(last, after) > 20 * LEARN_STILL else 0
                        last = after
                        shots.append(after)
                        pressed.append(0)
                        if runs >= 2:
                            wake = True                # still moving — stop tapping keys: on Viper R
                            break                      # revived it and then tapping ENTER re-froze it
                    if wake or after is None:
                        break
                still = 0
                prev = shots[-1]                       # judge the next captures fresh, not against the
            else:                                      # screen we just revived past
                shots.append(shot)
                pressed.append(direction if axis == "x" else (axis, direction))
    finally:
        press(set())
    return shots, pressed


def click_at(x: int, y: int) -> bool:
    """Move the pointer and left-click there (for games whose controls are on-screen buttons)."""
    import ctypes
    try:
        ctypes.windll.user32.SetCursorPos(int(x), int(y))
    except Exception:
        return False
    time.sleep(0.04)
    from tools.game_autopilot import press_action
    return press_action("MOUSE_LEFT", 0.08)


class WindowBackend(play_loop.Backend):
    """One game window as the loop's eyes and hands."""

    def __init__(self, hwnd: int, keys, screen=None, max_fps: float = 30.0):
        from tools import game_autopilot as ga
        self._ga = ga
        self.hwnd = hwnd
        self.keys = keys
        self.screen = screen                       # a ScreenControl, created on first use if needed
        self.interval = 1.0 / max(1.0, max_fps)
        self._cap = None
        self._region = None
        self._region_at = 0.0
        self.refocuses = 0
        self.clicks = 0
        self.last_frame = None

    # ── eyes ───────────────────────────────────────────────────────────────
    def _screen(self):
        if self.screen is None:
            from tom_core.screen_control import ScreenControl
            self.screen = ScreenControl()
        return self.screen

    def ready(self) -> bool:
        if not self._ga._window_alive(self.hwnd):
            return False
        if self._ga.is_foreground(self.hwnd):
            return True
        self.keys.release_all()                    # never leave a key held while we're not the ones typing
        self.refocuses += 1
        self._ga.focus_window(self.hwnd)
        time.sleep(0.15)
        return self._ga.is_foreground(self.hwnd)

    def frame(self):
        if not self._ga._window_alive(self.hwnd):
            return None
        now = time.monotonic()
        if self._cap is None or now - self._region_at > 1.0:     # follow the window if it moves
            region = self._ga.client_region(self.hwnd)
            self._region_at = now
            if region and region != self._region:
                if self._cap is not None:
                    self._cap.close()
                self._region, self._cap = region, self._ga.FastCapture(region=region)
        if self._cap is None:
            time.sleep(0.1)
            return self.last_frame
        try:
            self.last_frame = self._cap.grab_bgr()
        except Exception:
            return self.last_frame
        return self.last_frame

    def text(self) -> str:
        """Read the window's on-screen words (OCR). Slow, so the loop calls it about once a second."""
        region = self._ga.client_region(self.hwnd)
        if region is None:
            return ""
        try:
            return self._screen().text(region)
        except Exception:
            return ""

    # ── hands ──────────────────────────────────────────────────────────────
    def send(self, action: play_loop.Action) -> bool:
        if not self._ga.is_foreground(self.hwnd):
            return False
        if action.click and self.click(action.click):
            return True                     # the button was the action; don't also press its fallback key
        did = False
        if action.hold or action.tap:
            self.keys.apply(action.hold, action.tap)
            did = True
        if action.look:
            self._ga.move_mouse_rel(*action.look)
            did = True
        return did

    def click(self, label: str) -> bool:
        region = self._ga.client_region(self.hwnd)
        if region is None or not self._ga.is_foreground(self.hwnd):
            return False
        left, top, width, height = region
        if label.strip().lower() in ("centre", "center"):
            x, y = left + width // 2, top + height // 2
        else:
            match = None
            try:
                match = self._screen().find(label, region)
            except Exception:
                match = None
            if match is None:
                return False
            x, y = match.center
        ok = click_at(x, y)
        self.clicks += int(ok)
        return ok

    def close(self) -> None:
        self.keys.release_all()
        if self._cap is not None:
            self._cap.close()
            self._cap = None


def play_live(name: str, seconds: float = 30.0, stop=None, model: str = "qwen3.5:4b",
              decide: Optional[Callable[[bytes, str, str], str]] = None,
              launch_wait: float = 150.0, goal: str = "", *, learn: Optional[bool] = None,
              max_attempts: int = 3, think=None) -> Dict[str, Any]:
    """Start the game if needed, find out how it responds, then play toward `goal`, retrying deaths.

    A game TOM made is played by its own strategy player, which reads the game's colours and plays it
    properly (Viper: score 26 in one life). That path is checked first so a made game never falls into
    the generic explorer — measured 2026-10-28: the explorer died three times in six seconds on the
    same game the strategy survived for a full round.
    """
    from tools import game_autopilot as ga, game_library
    from tom_core.games import studio
    made = studio.find_made_game(name)
    if made is not None:
        played = ga.play_made_game(made, seconds=seconds, stop=stop)
        played.setdefault("response_type", "game_autopilot")
        played["played_by"] = "its own strategy"
        return played
    info = game_library.find_game(name)
    window = (info.window or info.name) if info is not None else name
    hit = ga.find_window(window)
    started = False
    if hit is None:
        if info is None:
            return {"status": "error", "response_type": "game_autopilot",
                    "message": f"'{name}' isn't open and I couldn't find it installed."}
        res = asyncio.run(game_library.launch(info))
        if res.get("status") != "success":
            return {"status": "error", "response_type": "game_autopilot",
                    "message": res.get("message", f"Couldn't start {info.name}.")}
        started = True
        hit = ga.wait_for_window(window, launch_wait, poll=2.0)
        if hit is None:
            return {"status": "error", "response_type": "game_autopilot",
                    "message": f"Started {info.name}, but no window with that name appeared within "
                               f"{launch_wait:g}s (it may still be loading, or a launcher may be waiting "
                               "for you)."}
        time.sleep(3.0)
    hwnd = hit[0]
    ga.set_dpi_aware()
    ga.focus_window(hwnd)

    key = info.name if info is not None else hit[1]
    prof = profile_mod.load(key)
    keymap = {k: k for k in list(ga.SCAN) + list(ga.MOUSE)}
    brain_note = ""
    if use_brain(prof, goal):
        # Understand the screen and work toward the goal (menus, worlds, dialogs, building, fighting).
        if info is not None and info.launcher == "BlueStacks":
            out = play_android(key, goal, seconds, stop, model, package=getattr(info, "package", ""), think=think)
            if out.get("adb") or out.get("brain_unavailable"):
                out["started"] = started
                if not out.get("brain_unavailable"):
                    return out
            else:
                brain_note = (" ADB wasn't available, so I used the BlueStacks window instead: "
                              + out.get("message", ""))
        window = WindowBackend(hwnd, ga.KeyState(keymap=keymap))
        decide_fn = decide or (lambda img, gname, gl: ga._ollama_vision(img, gname, model, gl))

        def autoplay(sec: float) -> str:
            # hand the fast reflex player the controls for a few seconds, then the brain looks again
            fast = play_loop.play(key, window, play_loop.Goal(seconds=sec), prof=profile_mod.load(key),
                                  decide=decide_fn, max_attempts=1, stop=stop, seconds=sec,
                                  tick=1.0 / 30.0, async_ocr=True)
            return f"reflex play {sec:g}s: {fast.ticks} looks, {fast.actions_sent} inputs, {fast.deaths} death(s)"

        out = play_with_brain(key, BrainWindowBackend(window, autoplay=autoplay), brain_goal(goal, key),
                              seconds=seconds, stop=stop, model=model, think=think, prof=prof)
        if not out.get("brain_unavailable"):
            out["started"] = started
            out["message"] += brain_note
            return out
        brain_note = " " + out["message"] + " So I used the simpler reflex player instead."
    backend = WindowBackend(hwnd, ga.KeyState(keymap=keymap))
    learned = brain_note.strip()
    try:
        # a tapped game has no keys to learn, and probing a live game is disruptive — do it once per game
        want_learn = learn if learn is not None else not (prof.probed or prof.responsive)
        if want_learn and prof.kind != "turnbased":
            candidates = profile_mod.candidates_for(key)[:PROBE_LIMIT]
            if candidates:
                prof = discover.learn(key, lambda k: backend.ready() and ga.press_action(k, 0.12),
                                      backend.frame, keys=candidates, save=True)
                learned = discover.describe(prof)
        # which colours are the player and the goal? Learned once, from the screen, by watching what
        # answers the keys; then a real strategy player can take over instead of exploring
        # Pairs: both axes are probed — a gliding game can reject one axis entirely (measured live)
        if prof.kind != "turnbased" and not prof.colors and prof.responsive:
            left, right = learning_keys(prof)
            shots, pressed = collect_for_learning(
                backend, lambda held: backend.send(play_loop.Action(hold=set(held))),
                left=left, right=right, revive=revive_keys_for(left, right, prof),
                pairs=pairs_for_learning(prof, left, right))
            model = learn_colors.infer(shots, pressed)
            if model.learned():
                prof.colors, prof.genre = model.colors(), model.genre or ""
                prof.notes = (prof.notes + [learn_colors.describe(model)])[-12:]
                profile_mod.save(prof)
            learned = (learned + " " + learn_colors.describe(model)).strip()
        strategy = None
        if prof.colors and prof.genre and prof.kind != "turnbased":
            first = backend.frame()
            height, width = (first.shape[0], first.shape[1]) if first is not None else (0, 0)
            manifest = learn_colors.manifest_from(prof.colors, prof.genre, width, height)
            if manifest is not None:
                from tom_core.games import strategies
                strategy = strategies.for_manifest(manifest)
                if strategy is not None:
                    learned = (learned + f" Its colours say it plays like a {prof.genre} game, so I'm using "
                               "that strategy rather than exploring.").strip()
        parsed = play_loop.parse_goal(goal, default_seconds=seconds)
        decide_fn = decide or (lambda img, gname, gl: ga._ollama_vision(img, gname, model, gl))
        # 30 looks/presses a second with OCR on a background thread: the reflex loop is the latency budget,
        # so the slow reading of the screen must never sit in front of it
        result = play_loop.play(key, backend, parsed, prof=prof, decide=decide_fn,
                                max_attempts=max_attempts, stop=stop, seconds=seconds,
                                tick=1.0 / 30.0, async_ocr=True, strategy=strategy)
        prof = profile_mod.load(key)
    finally:
        backend.close()

    ok = result.ticks > 0 and result.actions_sent > 0
    message = play_loop.report(result, prof)
    if learned:
        message += " " + learned
    refocuses = getattr(backend, "refocuses", 0)
    if refocuses:
        message += f" I brought the game back to the front {refocuses} time(s) to keep typing only there."
    message += (" I can read the state, work the menus, come back from deaths and keep trying your goal — "
                "but I won't claim to play a big 3D game like an expert.")
    return {"status": "success" if ok else "error", "response_type": "game_autopilot", "game": key,
            "started": started, "goal": parsed.text, "goal_kind": parsed.kind,
            "goal_met": result.goal_met, "session": result.as_dict(),
            "played_by": "strategy" if strategy is not None else "state loop",
            "genre": prof.genre, "colors": prof.colors,
            "profile": prof.to_dict(), "profile_path": profile_mod.path_for(key),
            "clicks": getattr(backend, "clicks", 0), "refocuses": refocuses,
            "verified": bool(ok), "message": message}


# ── the game brain on a PC window or an Android emulator ──────────────────────
class BrainWindowBackend(brain_mod.BrainBackend):
    """A game window as the game brain's backend (tom_core.games.brain).

    Built on WindowBackend, so the same safety rule holds: input only while the game's window is in
    front, keys released whenever it isn't. Coordinates the brain gives are fractions of the game's
    client area, turned into screen pixels here.
    """

    platform = "pc"

    def __init__(self, window: WindowBackend, read_lines=None, autoplay=None, typer=None):
        self.w = window
        self._brain = brain_mod
        self.read_lines = read_lines if read_lines is not None else brain_mod.ocr_reader()
        self._autoplay = autoplay
        self._typer = typer
        self._prev = None

    @property
    def can_autoplay(self) -> bool:
        return self._autoplay is not None

    def ready(self) -> bool:
        return self.w.ready()

    def observe(self):
        frame = self.w.frame()
        if frame is None:
            return None
        screen = self._brain.screen_from_frame(frame, self.read_lines, self._prev)
        self._prev = frame
        return screen

    def wait(self, seconds: float) -> None:
        time.sleep(seconds)

    def _point(self, x: float, y: float) -> Optional[Tuple[int, int]]:
        region = self.w._ga.client_region(self.w.hwnd)
        if region is None:
            return None
        left, top, width, height = region
        return left + int(x * width), top + int(y * height)

    def act(self, action: Dict[str, Any], screen) -> Tuple[bool, str]:
        ga = self.w._ga
        if not ga.is_foreground(self.w.hwnd):
            return False, "the game wasn't in front, so I didn't touch anything"
        t = action["type"]
        if t in ("click", "double_click"):
            pt = self._point(action["x"], action["y"])
            if pt is None:
                return False, "couldn't find the game window"
            ok = click_at(*pt)
            if ok and t == "double_click":
                time.sleep(0.06)
                ok = click_at(*pt)
            self.w.clicks += int(ok)
            return ok, ""
        if t == "type":
            text = action["text"]
            if not text.isascii():
                return False, "games only take plain keyboard text here (no emoji or non-Latin letters)"
            (self._typer or _type_into_game)(text)
            return True, ""
        if t == "key":
            return bool(ga.press_action(action["key"], 0.06)), ""
        if t == "hold":
            self.w.keys.apply(set(action["keys"]), set())
            try:
                time.sleep(action["seconds"])
            finally:
                self.w.keys.apply(set(), set())
            return True, ""
        if t == "look":
            return bool(ga.move_mouse_rel(action["dx"], action["dy"])), ""
        if t == "aim":
            # Relative mouse moves turn the camera in 3D games: move by the target's offset from the
            # crosshair (screen centre). Mouse sensitivity differs per game, so the brain looks again and
            # corrects on the next step rather than trusting one move.
            region = ga.client_region(self.w.hwnd)
            if region is None:
                return False, "couldn't find the game window"
            _, _, width, height = region
            ok = ga.move_mouse_rel(int((action["x"] - 0.5) * width), int((action["y"] - 0.5) * height))
            if ok and action.get("fire", True):
                time.sleep(0.03)
                ok = ga.press_action("MOUSE_LEFT", 0.08)
            return bool(ok), ""
        return False, f"{t} isn't available in a PC window"

    def autoplay(self, seconds: float) -> str:
        if self._autoplay is None:
            return "not available"
        return self._autoplay(seconds)

    def close(self) -> None:
        self.w.close()


def _type_into_game(text: str) -> None:
    from tools.game_tasks import type_text
    type_text(text)


def use_brain(prof, goal: str, env: Optional[Dict[str, str]] = None) -> bool:
    """Whether a session should be driven by the game brain rather than the reflex state loop.

    The brain understands screens (menus, worlds, dialogs, text fields, what to build or where to go);
    the reflex loop is faster but only knows menu/dead/gameplay. A game whose colours TOM already
    learned, with no specific task, keeps its measured strategy player.
    """
    import os as _os
    env = _os.environ if env is None else env
    if env.get("TOM_GAME_BRAIN", "1") == "0":
        return False
    if getattr(prof, "colors", None) and getattr(prof, "genre", "") and not (goal or "").strip():
        return False
    return True


def brain_goal(goal: str, game: str) -> str:
    """The goal the brain works toward. "play X for me" with nothing more means: get into the game and
    keep making progress."""
    g = (goal or "").strip()
    if not g or re.fullmatch(r"(?:please\s+)?(?:play|autopilot)\s+.+?(?:\s+for me|\s+yourself)?[.!?]*", g, re.I):
        return (f"get past any menus into actual gameplay in {game}, then keep playing well: make progress "
                "and avoid dying")
    return g


def play_with_brain(key: str, backend, goal: str, *, seconds: float, stop=None, model: str = "",
                    think=None, prof=None, max_steps: int = 0) -> Dict[str, Any]:
    """Run the game brain on a ready backend and turn the result into TOM's reply."""
    prof = prof or profile_mod.load(key)
    if think is None:
        ok, chosen = brain_mod.vision_ready(model)
        if not ok:
            return {"status": "error", "response_type": "game_autopilot", "game": key, "played_by": "brain",
                    "brain_unavailable": True, "message": chosen}
        think = brain_mod.ollama_think(chosen)
    import os as _os
    evidence_dir = _os.path.join(_os.path.dirname(profile_mod.path_for(key)), "evidence")
    b = brain_mod.GameBrain(backend, think, key, goal, lessons=getattr(prof, "lessons", []),
                            controls=prof.controls, seconds=seconds, stop=stop,
                            max_steps=max_steps or max(20, int(seconds / 2)), evidence_dir=evidence_dir)
    res = b.run()
    prof = profile_mod.load(key)
    brain_mod.save_lessons(prof, res.lessons)
    prof.sessions += 1
    if res.goal_met:
        prof.goal_met += 1
    try:
        profile_mod.save(prof)
    except OSError:
        pass
    acted = sum(1 for s in res.steps if s.ok)
    status = "success" if res.outcome == "done" and res.goal_met else ("partial" if acted else "error")
    return {"status": status, "response_type": "game_autopilot", "game": key, "played_by": "brain",
            "goal": goal, "goal_met": res.goal_met, "verified": res.verified, "outcome": res.outcome,
            "session": res.as_dict(), "message": brain_mod.report(res)}


def play_android(name: str, goal: str, seconds: float, stop=None, model: str = "", package: str = "",
                 think=None, connect=None) -> Dict[str, Any]:
    """Play an Android game (BlueStacks) through ADB with the brain. Returns an error result when ADB
    isn't reachable, so the caller can fall back to the BlueStacks window."""
    from tools import android_game
    backend, msg = (connect or android_game.connect_backend)(name, package)
    if backend is None:
        return {"status": "error", "response_type": "game_autopilot", "game": name, "adb": False, "message": msg}
    out = play_with_brain(name, backend, brain_goal(goal, name), seconds=seconds, stop=stop, model=model,
                          think=think)
    out["adb"] = True
    out["message"] = f"{out['message']} (Played through Android Debug Bridge: {msg})"
    return out
