"""Play a game TOM didn't make, toward a goal, and try again when it fails.

This replaces blind exploration with a loop that knows what it is looking at:

    look → what state is this? (perceive) → act for that state → did the goal happen? → repeat

Menu, pause and death screens are handled as states, not as gameplay. That is the difference that
matters: at a menu the right move is Enter or a click, not holding W; on the death screen the right move
is to respawn and go again. Deaths are counted and retried up to `max_attempts`, so "until it succeeds"
means something checkable, and when it gives up it says why.

What it honestly cannot do: win a 3D action game. The perception is colour, motion and OCR, and the
decisions are a small local vision model plus heuristics. So the promise is bounded and stated in the
report — it recovers from menus, deaths and freezes, it keeps trying, and it tells you exactly what it
saw and did. No memory reading, no anti-cheat evasion.
"""
from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from tom_core.games import perceive, profile as profile_mod
from tom_core.games.perceive import WIN, Observation

# Kinds where the game wants a key held down to keep moving. Everything else gets burst movement.
CONTINUOUS_MOVE = ("action", "survival", "driving", "command")
MENU_WORDS = ("resume", "continue", "play", "start", "press any key", "single player", "new game", "ok")
DEATH_WORDS = ("respawn", "retry", "try again", "restart", "continue", "ok", "revive", "play again")
STUCK_SECONDS = 2.5


# ── what the owner asked for ───────────────────────────────────────────────
@dataclass
class Goal:
    text: str = "play"
    kind: str = "explore"          # explore | survive | reach | win
    seconds: float = 30.0
    target: str = ""

    def satisfied(self, text: str, elapsed: float, deaths: int) -> bool:
        """Whether the goal has been met, using only what can be seen."""
        if self.kind == "win":
            return bool(WIN.search(text or ""))
        if self.kind == "reach" and self.target:
            wanted = [w for w in perceive.words(self.target) if len(w) > 2]
            seen = set(perceive.words(text or ""))
            return bool(wanted) and all(w in seen for w in wanted)
        if self.kind == "survive":
            return elapsed >= self.seconds and deaths == 0
        return False


def describe_goal(goal: Goal) -> str:
    """A short, checkable phrasing of a goal, for showing back to the owner."""
    if goal.kind == "survive":
        return f"survive {goal.seconds:g}s"
    if goal.kind == "reach":
        return f"reach {goal.target}"
    return "win" if goal.kind == "win" else "play"


def parse_goal(text: str, default_seconds: float = 30.0) -> Goal:
    """Turn "survive 5 minutes in Green Hell" / "get to level 2" / "win a round" into a checkable goal."""
    raw = (text or "").strip()
    low = raw.lower()
    m = re.search(r"(\d+)\s*(seconds?|secs?|minutes?|mins?|hours?)", low)
    seconds = float(m.group(1)) * (60 if m.group(2).startswith(("min", "hour")) else 1) if m else 0.0
    if m and m.group(2).startswith("hour"):
        seconds *= 60
    if not seconds and re.search(r"\bsurvive\b", low):
        seconds = max(default_seconds, 120.0)          # "survive" with no time means keep going a while
    if re.search(r"\bsurvive\b|\bstay alive\b|\bdon'?t die\b", low):
        return Goal(raw, "survive", seconds or default_seconds)
    if re.search(r"\b(?:win|beat|defeat|finish|complete|clear|pass)\b", low):
        return Goal(raw, "win", seconds or default_seconds)
    reach = re.search(r"\b(?:get to|reach|go to|find|collect|obtain|arrive at|open|destroy|build)\b\s+(.+)",
                      low)
    if reach and len(reach.group(1).split()) <= 6:
        target = re.sub(r"\bin\b.*$|\bon\b.*$", "", reach.group(1)).strip(" .!")
        if target:
            return Goal(raw, "reach", seconds or default_seconds, target)
    return Goal(raw or "play", "explore", seconds or default_seconds)


# ── what to do at each moment ─────────────────────────────────────────────
@dataclass
class Action:
    hold: Set[str] = field(default_factory=set)
    tap: Set[str] = field(default_factory=set)
    look: Optional[Tuple[int, int]] = None
    click: Optional[str] = None            # click on-screen text (tapped games, menus)
    note: str = ""


class Backend:
    """Everything the loop needs from the outside world. Real play wraps capture + input; tests wrap
    scripted frames, so the whole loop runs with no game, no keyboard and no display."""

    def ready(self) -> bool:
        """False while the game's window is not in front (the loop waits rather than typing elsewhere)."""
        return True

    def frame(self):
        raise NotImplementedError

    def text(self) -> str:
        return ""

    def send(self, action: Action) -> bool:
        raise NotImplementedError

    def click(self, label: str) -> bool:
        return False

    def close(self) -> None:
        """Release capture and held keys. Called once, when the session ends."""

    def wait(self, seconds: float) -> None:
        time.sleep(seconds)


class AsyncReader:
    """Read the game's on-screen words on a background thread.

    OCR takes 0.3-0.8s per look. Done inline that caps the whole loop at about one decision a second —
    which is latency the player feels as "it reacts late". Here the loop keeps capturing and pressing at
    capture speed and simply uses the most recent reading.
    """

    def __init__(self, read: Callable[[], str], every: float = 1.2):
        self.read, self.every = read, every
        self.text = ""
        self.reads = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="tom-game-ocr", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(0.02):
            started = time.monotonic()
            try:
                text = self.read() or ""
            except Exception:
                text = ""
            self.text = text
            self.reads += 1
            self._stop.wait(max(0.0, self.every - (time.monotonic() - started)))

    def latest(self) -> str:
        return self.text

    def close(self) -> None:
        self._stop.set()


class StrategyPlayer:
    """Play with one of the real strategy players (the ones that read colours and plan).

    Used when a game's colours have been learned from the screen and its type recognised, so this is a
    strategy rather than exploration. The death overlay is left to the loop: a strategy guessing at it
    could press restart at the wrong moment.
    """

    def __init__(self, strategy):
        self.strategy = strategy
        self.frames = 0
        try:
            strategy.game_over = lambda frame: False
        except Exception:
            pass

    def act(self, obs: Observation, frame, now: float) -> Action:
        self.frames += 1
        move = self.strategy.act(frame, now)
        return Action(hold=set(getattr(move, "hold", ())), tap=set(getattr(move, "tap", ())),
                      look=getattr(move, "look", None))


class ChoicePoller:
    """Asks the vision model for the next key in the background, so the loop never stalls on it.
    The last answer is used until a newer one arrives."""

    def __init__(self, decide: Callable[[bytes, str, str], str], game: str, goal: str,
                 every: float = 1.6):
        from concurrent.futures import ThreadPoolExecutor
        self.decide, self.game, self.goal, self.every = decide, game, goal, every
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.pending: Any = None
        self.current = ""
        self.asked_at = 0.0
        self.answers = 0

    def tick(self, frame, now: float) -> str:
        if self.pending is not None and self.pending.done():
            try:
                self.current = (self.pending.result() or "").strip().upper()
            except Exception:
                self.current = ""
            self.pending, self.answers = None, self.answers + 1
        if self.pending is None and now - self.asked_at >= self.every and frame is not None:
            self.asked_at = now
            try:
                import cv2
                small = frame[::2, ::2]
                ok, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ok:
                    self.pending = self.pool.submit(self.decide, buf.tobytes(), self.game, self.goal)
            except Exception:
                self.pending = None
        return self.current

    def close(self) -> None:
        self.pool.shutdown(wait=False, cancel_futures=True)


class GamePlayer:
    """Chooses gameplay input for a game, from its profile kind. Keys only ever come from what the game
    answered to (the profile) plus the model's choice — never an invented binding."""

    def __init__(self, game: str, prof: profile_mod.GameProfile,
                 poller: Optional[ChoicePoller] = None):
        self.game, self.prof, self.poller = game, prof, poller
        self.turn = 0
        self.stuck_since: Optional[float] = None
        self.nudges = 0
        self.burst_at = 0.0
        self.burst_i = 0
        self.burst = 0.6

    def forward(self) -> str:
        return self.prof.forward() or ("W" if "W" in self.prof.responsive or not self.prof.responsive else "")

    def act(self, obs: Observation, frame, now: float) -> Action:
        if self.prof.kind == "turnbased":
            return self._tap_game(obs, now)
        return self._key_game(obs, frame, now)

    # ── tapped games (Ludo King, card/board games in an emulator) ──────────
    def _tap_game(self, obs: Observation, now: float) -> Action:
        self.turn += 1
        if self.turn % 4:                                   # one attempt every ~1s, not every tick
            return Action()
        seen = (obs.text or "").lower()
        for word in self.prof.click_words:
            if word in seen:
                return Action(click=word, note=f"tapped '{word}'")
        return Action(click="centre", note="no button word on screen — tapped the middle")

    def _burst_key(self, now: float) -> str:
        keys = sorted(self.prof.responsive) or [self.forward()]
        if now - self.burst_at >= self.burst:
            self.burst_at, self.burst_i = now, self.burst_i + 1
        return keys[self.burst_i % len(keys)]

    # ── keyed games ────────────────────────────────────────────────────────
    def _key_game(self, obs: Observation, frame, now: float) -> Action:
        choice = self.poller.tick(frame, now) if self.poller is not None else ""
        forward = self.forward()
        held: Set[str] = set()
        action = Action()
        if self.prof.kind == "driving":
            if forward:
                held.add(forward)                            # throttle stays down, always
            if choice in ("A", "LEFT"):
                held.add("A")
            elif choice in ("D", "RIGHT"):
                held.add("D")
            elif choice in ("S", "DOWN", "CTRL"):
                held.discard(forward)                        # brake
        elif choice and choice != "NONE":
            held.add(choice)
        elif forward and self.prof.kind in CONTINUOUS_MOVE:
            held.add(forward)                                    # 3D games: keep moving, that is how you play
        elif forward:
            # A grid or arcade game has no "forward": the discovered key is a direction, and holding one
            # direction forever drives into a wall (measured: holding A in Viper died in 3s). Move in
            # short bursts and change direction, which is what exploring an unknown game looks like.
            held.add(self._burst_key(now))
        # stuck: the screen has not moved for a while, so try the keys that change what is possible
        if not obs.moving:
            self.stuck_since = self.stuck_since or now
            if now - self.stuck_since >= STUCK_SECONDS:
                self.stuck_since = now
                self.nudges += 1
                act = self.prof.controls.get("action") or "SPACE"
                interact = self.prof.controls.get("interact")
                action.tap.add(act)
                if interact and self.nudges % 2 == 0:
                    action.tap.add(interact)
                action.look = (26 if self.nudges % 2 else -26, 0)
                action.note = "screen stopped moving — jumped and looked around"
                self.turn += 1
                return action
        else:
            self.stuck_since = None
        action.hold = held
        if self.turn % 40 == 0:
            action.look = (8, 0)                             # slow sweep so the view doesn't go stale
        self.turn += 1
        return action


# ── the session ────────────────────────────────────────────────────────────
@dataclass
class SessionResult:
    game: str
    goal: str
    goal_met: bool = False
    seconds_played: float = 0.0
    ticks: int = 0
    goal_kind: str = "explore"
    states: Dict[str, int] = field(default_factory=dict)
    deaths: int = 0
    recoveries: int = 0                # recoveries attempted
    recovered: int = 0                 # times the game actually left the death screen
    actions_sent: int = 0
    attempts: int = 1
    paused_s: float = 0.0
    stopped: str = "time elapsed"
    notes: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {**self.__dict__}


class PlaySession:
    """One bounded session with a goal: observe, dispatch by state, retry after deaths."""

    def __init__(self, game: str, backend: Backend, goal: Goal,
                 prof: Optional[profile_mod.GameProfile] = None,
                 decide: Optional[Callable[[bytes, str, str], str]] = None,
                 tick: float = 0.25, ocr_every: float = 1.2, max_attempts: int = 3,
                 stop=None, clock: Callable[[], float] = time.monotonic, async_ocr: bool = False,
                 strategy=None):
        self.game, self.backend, self.goal = game, backend, goal
        self.prof = prof or profile_mod.load(game)
        self.perceiver = perceive.Perceiver(read_text=backend.text)
        self.poller = ChoicePoller(decide, game, goal.text) if decide else None
        self.player = GamePlayer(game, self.prof, self.poller)
        self.strategy_player = StrategyPlayer(strategy) if strategy is not None else None
        self.tick, self.ocr_every, self.max_attempts = tick, ocr_every, max_attempts
        self.stop, self.clock = stop, clock
        self._dead_ticks = 0
        # production reads the screen in the background so OCR never stalls the play loop
        self.reader = AsyncReader(backend.text, ocr_every) if async_ocr else None

    def _click_words(self, words: Tuple[str, ...], text: str) -> Optional[str]:
        seen = (text or "").lower()
        for word in words:
            if word in seen:
                return word
        return None

    def run(self) -> SessionResult:
        result = SessionResult(game=self.game, goal=self.goal.text, goal_kind=self.goal.kind)
        start = self.clock()
        text, text_at, last_state = "", -1e9, ""          # read the screen once before the first action
        static_since: Optional[float] = None
        while self.clock() - start < self.goal.seconds:
            now = self.clock()
            elapsed = now - start
            if self.stop is not None and self.stop.is_set():
                result.stopped = "stopped by request"
                break
            if not self.backend.ready():
                result.paused_s = round(result.paused_s + self.tick, 2)
                self.backend.wait(self.tick)
                continue
            frame = self.backend.frame()
            if frame is None:
                result.stopped = "lost the game window"
                break
            if self.reader is not None:
                text = self.reader.latest()
            elif now - text_at >= self.ocr_every:
                text, text_at = self.backend.text() or "", now
            obs = self.perceiver.observe(frame, text)
            result.ticks += 1
            result.states[obs.state] = result.states.get(obs.state, 0) + 1
            if obs.state != last_state:
                # one death is one death: the overlay stays up for several looks, and counting each of
                # them would turn a single death into "died 3 times, gave up" (seen live 2026-10-28)
                if obs.state == "dead":
                    result.deaths += 1
                    result.recoveries += 1
                    result.evidence.append(f"{elapsed:5.1f}s  death #{result.deaths}")
                else:
                    self._dead_ticks = 0
                    if last_state == "dead":
                        result.recovered += 1
                result.evidence.append(f"{elapsed:5.1f}s  {last_state or 'start'} -> {obs.state}"
                                       + (f" ({obs.detail})" if obs.detail else ""))
                last_state = obs.state
            # a still, wordless screen for 20s is a freeze, not a pause — loading can stay quiet for a while
            if obs.state == "static" and not (obs.text or "").strip():
                static_since = static_since or now
                if now - static_since > 20.0:
                    result.notes.append("the screen stayed still and blank for 20s — it may be frozen")
                    result.stopped = "the screen stopped changing"
                    break
            else:
                static_since = None
            action = self._act(obs, frame, now, result)
            if action is not None and self.backend.send(action):
                result.actions_sent += 1
            if self.goal.kind != "survive" and self.goal.satisfied(text, elapsed, result.deaths):
                result.goal_met = True
                result.evidence.append(f"{elapsed:5.1f}s  goal met: {self.goal.text}")
                result.stopped = "goal reached"
                break
            if result.deaths >= self.max_attempts:
                result.stopped = (f"died {result.deaths} time(s); gave up after {result.deaths} "
                                  "attempt(s)")
                break
            # sleep only what is left of the tick: a fixed sleep on top of the work is how a 30 fps loop
            # quietly becomes a 12 fps one
            self.backend.wait(max(0.0, self.tick - (self.clock() - now)))
        result.seconds_played = round(self.clock() - start, 1)
        result.attempts = result.deaths + 1
        # surviving means lasting the whole time without dying — the loop stops on time, not failure
        if (self.goal.kind == "survive" and result.deaths == 0
                and result.seconds_played >= self.goal.seconds * 0.9):
            result.goal_met = True
            result.evidence.append(f"survived {result.seconds_played:g}s without dying")
        if self.reader is not None:
            self.reader.close()
        if self.poller is not None:
            result.notes.append(f"vision model answered {self.poller.answers} time(s)")
            self.poller.close()
        result.notes.append(f"saw {', '.join(f'{k}×{v}' for k, v in sorted(result.states.items()))}")
        return result

    def _act(self, obs: Observation, frame, now: float, result: SessionResult) -> Optional[Action]:
        """The state machine: what to do depends on what the game is showing."""
        if obs.state == "loading":
            return None                                     # nothing to press while it loads
        if obs.state == "static":
            # A still screen is normal play, not a menu: a 3D game with a standing-still camera, and any
            # turn-based game while the opponent thinks. Pressing Enter there would open menus, so play
            # on and let the player decide (look around, or tap the board).
            keyed = ("action", "survival", "driving", "command")
            if self.prof.kind == "turnbased" or (self.prof.kind in keyed and not (obs.text or "").strip()):
                return self.player.act(obs, frame, now)
        if obs.state in ("menu", "static"):
            word = self._click_words(MENU_WORDS, obs.text)
            # the button if it can be clicked, Enter if it can't — the backend skips the keys on a hit
            return Action(tap={"ENTER"}, click=word,
                          note=f"clicked '{word}'" if word else "pressed Enter to leave the menu")
        if obs.state == "paused":
            word = self._click_words(("resume", "continue", "back to game"), obs.text)
            return Action(tap={"ESC"}, click=word, note="resumed the game")
        if obs.state == "dead":
            self._dead_ticks += 1
            # A tapped game's buttons are clickable; a PC game's death overlay wants a key. Clicking text
            # there looks like it worked and changes nothing — seen live on Viper (17 clicks, still dead).
            word = self._click_words(DEATH_WORDS, obs.text) if self.prof.kind == "turnbased" else None
            if word:
                return Action(click=word, note=f"tapped '{word}' to go again")
            key = "ESC" if self._dead_ticks % 4 == 0 else "ENTER"      # try the other key if Enter fails
            if self._dead_ticks == 4:
                result.notes.append("Enter did not clear the death screen, so Escape was tried too")
            return Action(tap={key}, note="died — pressed Enter to respawn")
        if self.strategy_player is not None:
            return self.strategy_player.act(obs, frame, now)
        return self.player.act(obs, frame, now)


def play(game: str, backend: Backend, goal: Optional[Goal] = None, *,
         prof: Optional[profile_mod.GameProfile] = None, decide=None, max_attempts: int = 3,
         stop=None, seconds: float = 30.0, clock: Callable[[], float] = time.monotonic,
         tick: float = 0.25, ocr_every: float = 1.2, async_ocr: bool = False,
         strategy=None) -> SessionResult:
    """Run one session and remember what it measured. The profile is saved even when the goal fails —
    knowing that a game dies at 20 s or freezes in a menu is exactly what the next attempt needs."""
    goal = goal or Goal(seconds=seconds)
    session = PlaySession(game, backend, goal, prof=prof, decide=decide, max_attempts=max_attempts,
                          stop=stop, clock=clock, tick=tick, ocr_every=ocr_every,
                          async_ocr=async_ocr, strategy=strategy)
    result = session.run()
    try:
        profile_mod.record(game, result.as_dict())
    except Exception:
        pass                                            # a session must never fail because saving did
    return result


def report(result: SessionResult, prof: Optional[profile_mod.GameProfile] = None) -> str:
    """The honest summary shown to the owner: what was seen, what was done, how it ended."""
    played = result.seconds_played
    parts = [f"Played {result.game} for {played:g}s" + (f" toward: {result.goal}" if result.goal else "")
             + "."]
    if result.goal_met:
        parts.append("Goal met.")
    elif result.goal_kind != "explore":
        parts.append("Goal not met.")
    states = ", ".join(f"{k} {v}" for k, v in sorted(result.states.items()))
    parts.append(f"On screen: {states}." if states else "")
    if result.deaths:
        parts.append(f"Died {result.deaths} time(s) and got back into play {result.recovered} time(s).")
    if result.paused_s:
        parts.append(f"Paused {result.paused_s:g}s while another window was in front.")
    parts.append(f"{result.actions_sent} input(s) sent. Stopped: {result.stopped}.")
    if prof is not None:
        parts.append(profile_mod.describe(prof) + ".")
    return " ".join(p for p in parts if p)
