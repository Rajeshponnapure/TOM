"""Playing an installed game with understanding: state perception, goals, retries and per-game memory.

Every test here runs with no game, no window and no keyboard — a scripted backend supplies the frames
and the on-screen words, and a fake clock makes a three-second session take milliseconds. The point is
that the loop's *decisions* are checkable: it leaves menus, notices deaths, retries, and says what it saw.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from tom_core.games import discover, perceive, play_loop
from tom_core.games import profile as profiles


# ── fakes ──────────────────────────────────────────────────────────────────
class Clock:
    """Time only moves when the loop waits, so a session's length is exactly its ticks."""

    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def wait(self, seconds):
        self.t += seconds


class Scripted(play_loop.Backend):
    """A backend whose screen states and words are scripted: (moving, text) per look."""

    def __init__(self, looks, clock=None, ready=True, frame_none=False):
        self.looks = looks
        self.clock = clock
        self.ready_state = ready
        self.frame_none = frame_none
        self.actions = []
        self.clicks = []
        self.i = 0
        self.text_i = 0
        self.dark = False

    def ready(self):
        return self.ready_state

    def frame(self):
        if self.frame_none:
            return None
        moving = self.looks[min(self.i, len(self.looks) - 1)][0]
        self.i += 1
        self.dark = (not self.dark) if moving else self.dark
        return np.full((60, 100, 3), 160 if self.dark else 20, dtype=np.uint8)

    def text(self):
        # the words belong to the look that was just captured, not to a separate counter
        i = max(0, self.i - 1)
        return self.looks[min(i, len(self.looks) - 1)][1]

    def send(self, action):
        self.actions.append(action)
        if action.click:                        # like the real backend: the button, else the fallback key
            return self.click(action.click)
        return True

    def click(self, label):
        self.clicks.append(label)
        return True

    def wait(self, seconds):
        if self.clock is not None:
            self.clock.wait(seconds)
        else:
            time.sleep(min(seconds, 0.02))          # a real (tiny) sleep, for latency tests


def run(looks, goal=None, game="Green Hell", seconds=3.0, prof=None, **kw):
    clock = Clock()
    backend = Scripted(looks, clock=clock)
    goal = goal or play_loop.Goal("play", "explore", seconds)
    kw.setdefault("ocr_every", 0.25)            # in tests, read the words on the look they belong to
    result = play_loop.play(game, backend, goal, prof=prof or profiles.load(game),
                            clock=clock, **kw)
    return result, backend


# ── perception ─────────────────────────────────────────────────────────────
def test_death_screen_is_not_mistaken_for_a_menu():
    # a death overlay also offers "Continue", so death has to win over menu words
    obs = perceive.classify("You died. Continue? Respawn", 0.0)
    assert obs.state == "dead"


@pytest.mark.parametrize("text,state", [
    ("Loading ...", "loading"),
    ("Paused — Resume", "paused"),
    ("Press any key to start", "menu"),
    ("Main menu: New game / Load game / Quit", "menu"),
    ("", "static"),
])
def test_text_states(text, state):
    assert perceive.classify(text, 0.0).state == state


def test_moving_screen_with_no_words_is_gameplay():
    assert perceive.classify("", 0.05).state == "gameplay"


def test_perceiver_smooths_a_single_still_frame():
    """One hitchy frame in a moving game must not read as a frozen screen."""
    p = perceive.Perceiver()
    moving_a = np.zeros((40, 40, 3), np.uint8)
    moving_b = np.full((40, 40, 3), 200, np.uint8)
    for _ in range(3):
        p.observe(moving_a)
        p.observe(moving_b)
    obs = p.observe(moving_b)                     # identical to the previous frame: one still look
    assert obs.state == "gameplay"


def test_frame_activity_measures_change():
    a = np.zeros((60, 60, 3), np.uint8)
    b = a.copy()
    b[10:50, 10:50] = 255
    assert perceive.frame_activity(a, b) > 0.3
    assert perceive.frame_activity(a, a.copy()) == 0.0
    assert perceive.frame_activity(None, b) == 0.0


# ── goals ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("text,kind,target", [
    ("survive 5 minutes in Green Hell", "survive", ""),
    ("stay alive for 40 seconds", "survive", ""),
    ("win a round of Ludo King", "win", ""),
    ("beat the first level", "win", ""),
    ("get to level 3", "reach", "level 3"),
    ("find water in Green Hell", "reach", "water"),
    ("play some game", "explore", ""),
])
def test_parse_goal(text, kind, target):
    goal = play_loop.parse_goal(text, default_seconds=20.0)
    assert goal.kind == kind and goal.target == target


def test_goal_time_is_parsed_and_capped_by_the_phrase():
    assert play_loop.parse_goal("survive 2 minutes", 20).seconds == 120.0
    assert play_loop.parse_goal("survive 30 seconds", 20).seconds == 30.0
    assert play_loop.parse_goal("survive", 20).seconds == 120.0      # no time given: keep going a while


def test_win_goal_is_met_only_by_win_words():
    goal = play_loop.Goal("win", "win", 30)
    assert goal.satisfied("Victory! You win", 5.0, 0)
    assert not goal.satisfied("You died", 5.0, 1)


def test_reach_goal_needs_the_target_words():
    goal = play_loop.Goal("reach the camp", "reach", 30, "the camp")
    assert goal.satisfied("You reached the camp", 5.0, 0)
    assert not goal.satisfied("You reached the river", 5.0, 0)


# ── the loop ───────────────────────────────────────────────────────────────
def test_menu_is_left_by_pressing_enter_not_by_playing():
    result, backend = run([(False, "Main menu — Quit")] * 4 + [(True, "")] * 20)
    assert result.states.get("menu", 0) >= 1
    assert result.states.get("gameplay", 0) >= 1
    menu_actions = [a for a in backend.actions if "ENTER" in a.tap]
    assert menu_actions, "the loop should press Enter to leave a menu with no clickable button"
    assert all(a.hold == set() for a in menu_actions), "no gameplay keys while still at the menu"


def test_menu_button_is_clicked_when_it_can_be_seen():
    """'Press any key to start' is a menu we can click, which beats pressing Enter blindly."""
    result, backend = run([(False, "Press any key to start")] * 20)
    assert backend.clicks, "a visible menu button should be clicked"
    assert backend.clicks[0] in play_loop.MENU_WORDS
    assert not any(a.hold for a in backend.actions)


def test_death_is_counted_and_retried():
    looks = [(True, "")] * 5 + [(False, "You died")] * 5
    result, backend = run(looks, goal=play_loop.Goal("play", "explore", 6.0), max_attempts=3)
    assert result.deaths >= 1
    assert result.recoveries == result.deaths
    assert any("ENTER" in a.tap or a.click for a in backend.actions)


def test_gives_up_after_max_attempts():
    # die, play again, die, play again — two separate deaths, then stop
    result, _ = run([(False, "You died"), (True, "")] * 40,
                    goal=play_loop.Goal("play", "explore", 20.0), max_attempts=2)
    assert result.deaths == 2
    assert "gave up" in result.stopped


def test_one_death_on_screen_counts_once():
    """The death overlay stays up for many looks; that is one death, not one per look."""
    result, _ = run([(True, "")] * 4 + [(False, "You died")] * 40,
                    goal=play_loop.Goal("play", "explore", 6.0), max_attempts=3)
    assert result.deaths == 1 and result.recoveries == 1
    assert result.stopped == "time elapsed"


def test_a_pc_game_death_screen_is_answered_with_a_key_not_a_click():
    """Clicking "play again" looks like it worked and changes nothing — measured on Viper, 2026-10-28."""
    result, backend = run([(False, "Game over — Play again")] * 20, game="Green Hell",
                          goal=play_loop.Goal("play", "explore", 2.0), max_attempts=1)
    assert backend.clicks == []
    assert any("ENTER" in a.tap for a in backend.actions)


def test_escape_is_tried_when_enter_does_not_clear_the_death_screen():
    result, backend = run([(False, "You died")] * 40, game="Green Hell",
                          goal=play_loop.Goal("play", "explore", 3.0), max_attempts=3)
    keys = [k for a in backend.actions for k in a.tap]
    assert "ESC" in keys, "a game whose respawn is not Enter must get a second key"
    assert any("Escape was tried" in n for n in result.notes)


def test_recovery_is_only_claimed_when_the_game_actually_resumed():
    result, _ = run([(True, "")] * 4 + [(False, "You died")] * 4 + [(True, "")] * 40,
                    goal=play_loop.Goal("play", "explore", 4.0), max_attempts=3)
    assert result.deaths == 1 and result.recovered == 1
    assert "got back into play 1 time" in play_loop.report(result)


def test_survive_goal_is_met_without_dying():
    result, _ = run([(True, "")] * 60, goal=play_loop.Goal("survive", "survive", 2.0))
    assert result.goal_met and result.deaths == 0 and result.stopped != "goal reached"


def test_survive_goal_fails_after_a_death():
    looks = [(True, "")] * 4 + [(False, "Game over")] * 40
    result, _ = run(looks, goal=play_loop.Goal("survive", "survive", 2.0), max_attempts=1)
    assert not result.goal_met and result.deaths == 1


def test_win_goal_stops_the_session_early():
    result, _ = run([(True, "")] * 200, goal=play_loop.Goal("win", "win", 10.0),
                    prof=None)
    assert not result.goal_met


def test_a_winning_screen_ends_the_session():
    """Win words on screen end the run before the clock does."""
    clock = Clock()
    backend = Scripted([(True, "")] * 200, clock=clock)
    backend.text = lambda: "Victory! You win"          # every OCR read says the game was won
    result = play_loop.play("Ludo King", backend, play_loop.Goal("win", "win", 30.0),
                            prof=profiles.load("Ludo King"), clock=clock)
    assert result.goal_met and result.stopped == "goal reached"
    assert result.seconds_played < 5.0


def test_paused_while_another_window_is_in_front():
    clock = Clock()
    backend = Scripted([(True, "")] * 50, clock=clock, ready=False)
    result = play_loop.play("Green Hell", backend, play_loop.Goal("play", "explore", 2.0),
                            prof=profiles.load("Green Hell"), clock=clock)
    assert result.paused_s > 0 and result.actions_sent == 0


def test_losing_the_window_stops_the_session():
    clock = Clock()
    backend = Scripted([(True, "")] * 20, clock=clock, frame_none=True)
    result = play_loop.play("Green Hell", backend, play_loop.Goal("play", "explore", 5.0),
                            prof=profiles.load("Green Hell"), clock=clock)
    assert result.stopped == "lost the game window"


def test_a_still_screen_in_a_3d_game_does_not_open_the_menu():
    """A standing-still camera is not a menu: pressing Enter there would open menus."""
    result, backend = run([(False, "")] * 40, game="Green Hell",
                          goal=play_loop.Goal("play", "explore", 4.0))
    assert not any("ENTER" in a.tap for a in backend.actions)
    assert any(a.look for a in backend.actions), "it should look around when nothing moves"


def test_stop_event_ends_the_session():
    import threading
    stop = threading.Event()
    stop.set()
    result, backend = run([(True, "")] * 50, goal=play_loop.Goal("play", "explore", 5.0), stop=stop)
    assert result.stopped == "stopped by request" and backend.actions == []


def test_tapped_game_clicks_the_button_words():
    result, backend = run([(False, "ROLL THE DICE")] * 40, game="Ludo King",
                          goal=play_loop.Goal("play", "explore", 3.0))
    assert "roll" in backend.clicks


def test_tapped_game_clicks_the_middle_when_no_button_is_readable():
    result, backend = run([(False, "")] * 40, game="Ludo King",
                          goal=play_loop.Goal("play", "explore", 3.0))
    assert "centre" in backend.clicks


def test_progress_is_saved_even_when_the_goal_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("TOM_GAME_PROFILE_DIR", str(tmp_path))
    result, _ = run([(True, "")] * 40, game="Green Hell",
                    goal=play_loop.Goal("reach camp", "reach", 2.0, "camp"))
    saved = profiles.load("Green Hell")
    assert saved.sessions == 1 and not result.goal_met
    assert saved.states.get("gameplay", 0) > 0


def test_report_says_what_was_seen_and_done():
    result, _ = run([(False, "You died")] * 12 + [(True, "")] * 20,
                    goal=play_loop.Goal("play", "explore", 3.0))
    text = play_loop.report(result)
    assert "Played Green Hell" in text and "On screen" in text and "Stopped:" in text


# ── per-game memory ────────────────────────────────────────────────────────
def test_profile_roundtrip_and_growth(tmp_path, monkeypatch):
    monkeypatch.setenv("TOM_GAME_PROFILE_DIR", str(tmp_path))
    prof = profiles.load("Green Hell")
    assert prof.kind == "survival" and prof.window == "Green Hell"
    prof.controls = {"forward": "Z"}
    profiles.save(prof)
    assert profiles.load("Green Hell").controls == {"forward": "Z"}
    profiles.record("Green Hell", {"states": {"gameplay": 7}, "deaths": 2, "goal_met": True,
                                   "seconds_played": 12.5, "goal": "survive"})
    grown = profiles.load("Green Hell")
    assert grown.sessions == 1 and grown.deaths == 2 and grown.goal_met == 1
    assert grown.best["seconds"] == 12.5 and grown.states["gameplay"] == 7
    assert grown.controls == {"forward": "Z"}, "a session must not wipe what was learned"
    assert "played 1 time" in profiles.describe(grown)


def test_every_installed_game_has_known_metadata():
    for name in ("Marvel's Spider-Man 2", "Green Hell", "over the hill", "Ludo King", "Minecraft"):
        info = profiles.known_for(name)
        assert info, f"{name} should be known"
        assert info["kind"] in profiles.KINDS and info["window"]


def test_roles_come_from_measurements_not_guesses():
    assert profiles.roles_from({"A": 0.9})["forward"] == "A"      # not hard-coded to W
    assert profiles.roles_from({"W": 0.001}) == {}                # nothing visible → no claim
    roles = profiles.roles_from({"W": 0.4, "E": 0.2, "Q": 0.1})
    assert roles["forward"] == "W" and roles["action"] == "E" and roles["interact"] == "Q"


def test_unknown_game_falls_back_to_a_probe_list():
    assert profiles.known_for("Some Game Nobody Has") == {}
    assert profiles.candidates_for("Some Game Nobody Has") == profiles.DEFAULT_CANDIDATES


# ── control discovery ──────────────────────────────────────────────────────
def test_discovery_finds_the_key_that_actually_does_something(tmp_path, monkeypatch):
    monkeypatch.setenv("TOM_GAME_PROFILE_DIR", str(tmp_path))
    frames = [np.zeros((40, 60, 3), np.uint8)]
    pressed = []

    def frame():
        return frames[-1]

    def press(key):
        pressed.append(key)
        if key == "A":
            frames.append(np.full((40, 60, 3), 220, np.uint8))     # only A changes the screen
        return True

    prof = discover.learn("over the hill", press, frame, keys=["W", "A", "SPACE"],
                          settle=0.01, wait=lambda s: None)
    assert prof.controls.get("forward") == "A"
    assert "W" not in prof.responsive and "SPACE" not in prof.responsive
    assert prof.probed and "A" in pressed


def test_discovery_never_blindly_presses_menu_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("TOM_GAME_PROFILE_DIR", str(tmp_path))
    pressed = []
    discover.learn("Green Hell", lambda k: (pressed.append(k), True)[1],
                   lambda: np.zeros((20, 20, 3), np.uint8), keys=["ESC", "TAB", "ENTER", "E"],
                   settle=0.01, wait=lambda s: None)
    assert pressed == ["E"], "ESC/TAB/ENTER open menus and consoles, so they are not probed"
    assert discover.describe(profiles.load("Green Hell")).startswith("None of the keys"), \
        "nothing responded, so it must not claim a discovery"


def test_discovery_is_remembered_between_sessions(tmp_path, monkeypatch):
    monkeypatch.setenv("TOM_GAME_PROFILE_DIR", str(tmp_path))
    frames = [np.zeros((30, 30, 3), np.uint8)]
    discover.learn("Minecraft", lambda k: (frames.append(np.full((30, 30, 3), 99, np.uint8)), True)[1],
                   lambda: frames[-1], keys=["W"], settle=0.01, wait=lambda s: None)
    again = profiles.load("Minecraft")
    assert again.probed and again.controls.get("forward") == "W"
    assert "working keys" in " ".join(again.notes)


# ── latency and movement ───────────────────────────────────────────────────
def test_slow_screen_reading_does_not_stall_the_play_loop():
    """OCR takes 0.3-0.8s. Done inline it caps the loop at ~1 decision/s, which is felt as latency."""
    backend = Scripted([(True, "")] * 500)
    backend.text = lambda: (time.sleep(0.4), "Press any key")[1]
    started = time.monotonic()
    result = play_loop.play("Green Hell", backend, play_loop.Goal("play", "explore", 0.6),
                            tick=0.02, ocr_every=0.1, async_ocr=True)
    elapsed = time.monotonic() - started
    assert elapsed < 1.6, f"a slow read blocked the loop ({elapsed:.2f}s for a 0.6s session)"
    assert result.ticks > 10, "the loop should keep looking and pressing while OCR runs"


def test_the_loop_keeps_its_target_rate_with_a_slow_reader():
    """With OCR off the hot path the loop runs at its target rate instead of one decision per read."""
    class Costed(play_loop.Backend):
        def frame(self):
            return np.full((120, 160, 3), 25, np.uint8)

        def text(self):
            time.sleep(0.15)
            return ""

        def send(self, action):
            return True

    result = play_loop.play("CostTest", Costed(), play_loop.Goal("play", "explore", 0.6),
                            prof=profiles.GameProfile(game="CostTest", kind="action",
                                                      controls={"forward": "W"}, probed=True),
                            tick=1 / 30, ocr_every=0.2, async_ocr=True, decide=lambda *a: "NONE")
    rate = result.ticks / max(result.seconds_played, 0.1)
    assert rate > 15, f"only {rate:.1f} looks/s with a 150 ms reader"


def test_async_reader_returns_immediately():
    from tom_core.games.play_loop import AsyncReader
    calls = {"n": 0}

    def slow():
        calls["n"] += 1
        time.sleep(0.3)
        return "You died"

    reader = AsyncReader(slow, every=0.05)
    started = time.monotonic()
    for _ in range(20):
        reader.latest()
        time.sleep(0.01)
    assert time.monotonic() - started < 0.35, "latest() must never wait on the OCR thread"
    time.sleep(0.35)
    assert calls["n"] >= 1 and reader.latest() == "You died"
    reader.close()


def test_a_grid_game_tries_directions_instead_of_driving_into_one_wall():
    """Holding one direction forever was the instant death: Viper, three deaths in six seconds."""
    prof = profiles.load("Box Game")
    prof.kind, prof.responsive = "unknown", {"W": 0.5, "A": 0.5, "S": 0.5, "D": 0.5}
    clock = Clock()
    backend = Scripted([(True, "")] * 300, clock=clock)
    play_loop.play("Box Game", backend, play_loop.Goal("play", "explore", 6.0),
                   prof=prof, clock=clock, ocr_every=0.25)
    tried = {key for action in backend.actions for key in action.hold}
    assert len(tried) >= 3, f"it should explore several directions, tried only {tried}"


def test_a_3d_game_keeps_moving_forward():
    """A 3D game is the opposite: standing still is the mistake, so forward stays held."""
    prof = profiles.load("Green Hell")
    prof.responsive, prof.controls = {"W": 0.5}, {"forward": "W"}
    clock = Clock()
    backend = Scripted([(True, "")] * 300, clock=clock)
    play_loop.play("Green Hell", backend, play_loop.Goal("play", "explore", 4.0), prof=prof,
                   clock=clock, ocr_every=0.25)
    holding = [a for a in backend.actions if a.hold]
    assert holding and all("W" in a.hold for a in holding)


# ── wiring ─────────────────────────────────────────────────────────────────
def test_play_installed_game_delegates_to_the_loop(monkeypatch):
    from tools import game_autopilot, game_play
    seen = {}

    def fake(*args, **kwargs):
        seen["args"] = args
        return {"status": "success", "message": "ok"}

    monkeypatch.setattr(game_play, "play_live", fake)
    out = game_autopilot.play_installed_game("Green Hell", 15, None, "m", None, 100.0, "survive")
    assert out["message"] == "ok" and seen["args"][0] == "Green Hell" and seen["args"][1] == 15


def test_a_game_tom_made_is_played_by_its_own_strategy(monkeypatch):
    """A made game must never fall into the generic explorer — its strategy plays it far better."""
    from tools import game_autopilot, game_play
    from tom_core.games import studio
    seen = {}
    monkeypatch.setattr(studio, "find_made_game", lambda name: {"title": "Viper", "path": "x"})
    monkeypatch.setattr(game_autopilot, "play_made_game",
                        lambda made, **k: (seen.update(made=made), {"status": "success"})[1])
    out = game_play.play_live("Viper", seconds=5.0)
    assert out["played_by"] == "its own strategy" and seen["made"]["title"] == "Viper"


def test_an_installed_game_still_uses_the_state_loop(monkeypatch):
    from tools import game_autopilot, game_play
    from tom_core.games import profile as profiles_mod, studio
    from tools import game_library
    monkeypatch.setattr(studio, "find_made_game", lambda name: None)
    monkeypatch.setenv("TOM_GAME_BRAIN", "0")                              # this test is about the state loop
    monkeypatch.setattr(game_library, "find_game", lambda name: None)      # no Steam/desktop scan in a test
    monkeypatch.setattr(game_autopilot, "find_window", lambda w: (7, "Green Hell"))
    monkeypatch.setattr(game_autopilot, "focus_window", lambda h: True)
    monkeypatch.setattr(game_autopilot, "set_dpi_aware", lambda: None)
    monkeypatch.setattr(profiles_mod, "load", lambda n: profiles_mod.GameProfile(game=n, probed=True))
    monkeypatch.setattr(game_play, "WindowBackend", lambda hwnd, keys, screen=None: _FakeBackend())
    out = game_play.play_live("Green Hell", seconds=0.4, decide=lambda *a: "NONE")
    assert out["played_by"] == "state loop" and out["game"] == "Green Hell"


class _FakeBackend(play_loop.Backend):
    def frame(self):
        return np.full((40, 60, 3), 30, np.uint8)

    def text(self):
        return ""

    def send(self, action):
        return True

    def wait(self, seconds):
        time.sleep(min(seconds, 0.005))


def test_window_backend_refuses_to_type_into_another_window(monkeypatch):
    """The safety rule: if something else is in front, no input is sent."""
    from tools import game_autopilot, game_play
    monkeypatch.setattr(game_autopilot, "is_foreground", lambda hwnd: False)
    monkeypatch.setattr(game_autopilot, "_window_alive", lambda hwnd: True)
    monkeypatch.setattr(game_autopilot, "focus_window", lambda hwnd: False)
    keys = game_autopilot.KeyState(send=lambda k, down: True)
    backend = game_play.WindowBackend(1234, keys)
    assert backend.ready() is False
    assert backend.send(play_loop.Action(hold={"W"})) is False
    assert keys.down == set()
