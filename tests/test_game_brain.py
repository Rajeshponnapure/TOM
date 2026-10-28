"""The game brain: understanding a game's screens and working toward a goal (tom_core/games/brain.py),
its PC-window and Android (ADB) backends, and the safety rules the model cannot override.

Everything runs with no game, no model and no display: a scripted menu game stands in for Minecraft's
title → worlds → create-world → in-world flow, and the "model" is a policy that only sees the prompt TOM
builds — so these tests also prove the prompt carries what a model needs.
"""
import json
import os
import re
import sys
import threading
import types

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tom_core.games import brain  # noqa: E402
from tom_core.games import profile as profile_mod  # noqa: E402


@pytest.fixture(autouse=True)
def profiles(tmp_path, monkeypatch):
    monkeypatch.setenv("TOM_GAME_PROFILE_DIR", str(tmp_path / "profiles"))
    return tmp_path / "profiles"


# ── a scripted menu game ───────────────────────────────────────────────────
SCREENS = {
    "title": [("Minecraft", (300, 40, 200, 40)), ("Play", (350, 200, 100, 30)), ("Settings", (350, 250, 100, 30)),
              ("Marketplace", (350, 300, 100, 30)), ("Sign In", (650, 20, 90, 24))],
    "worlds": [("Worlds", (340, 40, 120, 30)), ("Create New", (340, 120, 120, 30)), ("Back", (20, 20, 60, 24))],
    "create": [("Create New World", (300, 40, 200, 30)), ("World Name", (100, 120, 120, 24)),
               ("My World", (300, 120, 200, 24)), ("Activate Cheats OFF", (100, 200, 200, 24)),
               ("Create", (350, 400, 100, 30))],
    "create_cheats": [("Create New World", (300, 40, 200, 30)), ("World Name", (100, 120, 120, 24)),
                      ("My World", (300, 120, 200, 24)), ("Activate Cheats ON", (100, 200, 200, 24)),
                      ("Create", (350, 400, 100, 30))],
    "loading": [("Loading world", (320, 280, 160, 30))],
    "world": [],
}
COLORS = {"title": 40, "worlds": 80, "create": 120, "create_cheats": 140, "loading": 10, "world": 200}


class MenuGame(brain.BrainBackend):
    """Clicks change screens like the real menus do; the frame colour changes with the screen."""

    def __init__(self, start="title", platform="pc"):
        self.state = start
        self.platform = platform
        self.acts = []
        self.typed = []
        self.closed = False
        self.loading_left = 0

    def observe(self):
        if self.state == "loading":
            self.loading_left -= 1
            if self.loading_left <= 0:
                self.state = "world"
        frame = np.full((600, 800, 3), COLORS[self.state], np.uint8)
        els = [brain.Element(i, t, b) for i, (t, b) in enumerate(SCREENS[self.state], 1)]
        state = "gameplay" if self.state == "world" else ("loading" if self.state == "loading" else "menu")
        return brain.Screen(frame, 800, 600, els, state, 0.0, b"png")

    def act(self, action, screen):
        self.acts.append(action)
        if action["type"] == "type":
            self.typed.append(action["text"])
            return True, ""
        if action["type"] != "click":
            return True, ""
        x, y = action["x"] * 800, action["y"] * 600
        hit = next((e.text for e in screen.elements
                    if e.box[0] <= x <= e.box[0] + e.box[2] and e.box[1] <= y <= e.box[1] + e.box[3]), "")
        nxt = {("title", "Play"): "worlds", ("worlds", "Create New"): "create",
               ("create", "Activate Cheats OFF"): "create_cheats", ("create_cheats", "Create"): "loading",
               ("worlds", "Back"): "title"}.get((self.state, hit))
        if nxt:
            self.state = nxt
            if nxt == "loading":
                self.loading_left = 2
        return True, ""

    def wait(self, seconds):
        pass

    def close(self):
        self.closed = True


def element_id(prompt, text):
    m = re.search(r'#(\d+) "' + re.escape(text) + '"', prompt)
    return int(m.group(1)) if m else None


def menu_policy(prompt, png):
    """A stand-in vision model that reads only TOM's prompt."""
    assert "GOAL:" in prompt and "Actions:" in prompt
    if "The screen looks like: gameplay" in prompt:
        return json.dumps({"see": "standing in the world", "action": {"type": "done", "evidence": "in the world"}})
    if "The screen looks like: loading" in prompt:
        return json.dumps({"see": "loading", "action": {"type": "wait", "seconds": 2}})
    for label in ("Activate Cheats OFF", "Create New", "Play"):
        eid = element_id(prompt, label)
        if eid:
            return json.dumps({"see": f"a menu with {label}", "plan": "go in",
                               "action": {"type": "click", "element": eid}, "expect": "next screen"})
    eid = element_id(prompt, "Create")
    return json.dumps({"action": {"type": "click", "element": eid}})


def test_the_brain_walks_the_menus_into_a_new_world_with_cheats_on():
    game = MenuGame()
    res = brain.GameBrain(game, menu_policy, "Minecraft", "get into a world with cheats on", seconds=60).run()
    assert res.outcome == "done" and res.goal_met
    clicked = [a.get("element") for a in game.acts if a["type"] == "click"]
    assert len(clicked) == 4 and game.state == "world"
    assert game.closed                                        # backend released at the end
    assert any("Play" in x and "Worlds" in x for x in res.lessons)    # it learned where Play leads
    msg = brain.report(res)
    assert "I reached the goal" in msg and "vision model's reading" in msg   # honest: not independently verified


def test_learned_screens_are_fed_back_next_session():
    game = MenuGame()
    first = brain.GameBrain(game, menu_policy, "Minecraft", "enter a world").run()
    seen = {}

    def remember(prompt, png):
        seen.setdefault("prompt", prompt)
        return menu_policy(prompt, png)
    brain.GameBrain(MenuGame(), remember, "Minecraft", "enter a world", lessons=first.lessons).run()
    assert "What you learned about this game before" in seen["prompt"]
    assert first.lessons[0] in seen["prompt"]


def test_an_independent_check_marks_the_goal_verified():
    game = MenuGame(start="world")
    res = brain.GameBrain(game, menu_policy, "Minecraft", "be in the world",
                          check_goal=lambda s, t: s.state == "gameplay").run()
    assert res.outcome == "done" and res.verified and res.model_calls == 0


def test_done_before_doing_anything_is_not_credited():
    res = brain.GameBrain(MenuGame(start="world"), menu_policy, "Minecraft", "enter a world").run()
    assert res.outcome == "done" and not res.goal_met
    assert "already met before I did anything" in brain.report(res)


def test_a_move_that_does_nothing_twice_is_blocked_and_the_model_is_told():
    prompts = []

    def stubborn(prompt, png):
        prompts.append(prompt)
        eid = element_id(prompt, "Settings")         # Settings does nothing in this fake game
        return json.dumps({"action": {"type": "click", "element": eid}})
    res = brain.GameBrain(MenuGame(), stubborn, "Minecraft", "enter a world", max_steps=6).run()
    assert any("did nothing twice" in p for p in prompts)
    refused = [s for s in res.steps if not s.ok]
    assert refused and "did nothing" in refused[0].note
    assert sum(1 for s in res.steps if s.ok) == 2              # only two real clicks were sent


def test_ten_moves_without_effect_stop_the_session_as_stuck():
    keys = iter(["TAB", "Q", "E", "R", "F", "1", "2", "3", "4", "SPACE", "SHIFT", "CTRL"] * 3)

    def different_keys(prompt, png):          # always a new key, so nothing is blocked as a repeat
        return json.dumps({"action": {"type": "key", "key": next(keys)}})
    res = brain.GameBrain(MenuGame(), different_keys, "X", "goal", max_steps=40).run()
    assert res.outcome == "stuck" and len(res.steps) == 10
    assert "changed nothing" in brain.report(res)


def test_garbage_from_the_model_stops_after_four_replies():
    res = brain.GameBrain(MenuGame(), lambda p, i: "I think you should press play!", "X", "goal").run()
    assert res.outcome == "model" and res.invalid == 4
    assert "vision model" in brain.report(res)


def test_a_failing_model_call_is_reported_not_raised():
    def boom(prompt, png):
        raise TimeoutError("ollama timed out")
    res = brain.GameBrain(MenuGame(), boom, "X", "goal").run()
    assert res.outcome == "model"


def test_stop_ends_the_session():
    stop = threading.Event()
    stop.set()
    res = brain.GameBrain(MenuGame(), menu_policy, "X", "goal", stop=stop).run()
    assert res.outcome == "stopped" and res.model_calls == 0


def test_time_budget_is_respected():
    res = brain.GameBrain(MenuGame(), menu_policy, "X", "goal", seconds=0.0).run()
    assert res.outcome == "time"


def test_evidence_screenshot_is_saved(tmp_path):
    res = brain.GameBrain(MenuGame(), menu_policy, "Minecraft", "enter", evidence_dir=str(tmp_path / "ev")).run()
    assert res.evidence_path and open(res.evidence_path, "rb").read() == b"png"


# ── the rules the model cannot change ──────────────────────────────────────
def screen_of(name):
    return MenuGame(start=name).observe()


@pytest.mark.parametrize("label", ["Marketplace", "Sign In"])
def test_money_and_account_buttons_are_never_clicked(label):
    s = screen_of("title")
    eid = next(e.id for e in s.elements if e.text == label)
    action, why = brain.Guard().check({"type": "click", "element": eid}, s)
    # Marketplace is a shop screen, not a purchase: it may be opened. Sign In is refused.
    if label == "Sign In":
        assert action is None and "by hand" in why
    else:
        assert action is not None


def test_clicking_a_price_by_coordinates_is_refused_too():
    els = [brain.Element(1, "Buy 1720 Minecoins", (100, 100, 200, 30))]
    s = brain.Screen(None, 800, 600, els)
    action, why = brain.Guard().check({"type": "click", "x": 200 / 800, "y": 115 / 600}, s)
    assert action is None and "by hand" in why
    action, _ = brain.Guard().check({"type": "click", "x": 0.9, "y": 0.9}, s)
    assert action is not None                                      # elsewhere on the screen is fine


def test_typing_on_a_password_or_payment_screen_is_refused():
    s = brain.Screen(None, 800, 600, [brain.Element(1, "Password", (10, 10, 100, 20))])
    action, why = brain.Guard().check({"type": "type", "text": "hunter2"}, s)
    assert action is None and "password" in why


def test_invalid_actions_are_explained_to_the_model():
    s = screen_of("title")
    g = brain.Guard()
    assert g.check({"type": "click", "element": 99}, s)[1].startswith("there is no element #99")
    assert "isn't allowed" in g.check({"type": "key", "key": "F13"}, s)[1]
    assert "not an action" in g.check({"type": "hack"}, s)[1]
    assert "1-80" in g.check({"type": "type", "text": "x" * 200}, s)[1]
    assert "reflex player" in g.check({"type": "autoplay"}, s)[1]  # no reflex player on this backend


def test_values_are_normalised_and_clamped():
    s = screen_of("title")
    g = brain.Guard()
    a, _ = g.check({"type": "click", "x": 52, "y": 31}, s)          # percent → fraction
    assert a["x"] == pytest.approx(0.52) and a["y"] == pytest.approx(0.31)
    a, _ = g.check({"type": "hold", "keys": ["w", "Shift"], "seconds": 60}, s)
    assert a["keys"] == ["W", "SHIFT"] and a["seconds"] == brain.MAX_HOLD
    a, _ = g.check({"type": "key", "key": "Return"}, s)
    assert a["key"] == "ENTER"
    a, _ = g.check({"type": "look", "dx": 5000, "dy": 0}, s)
    assert a["dx"] == brain.MAX_LOOK


def test_touch_screens_have_touch_actions():
    s = screen_of("title")
    g = brain.Guard("touch")
    a, _ = g.check({"type": "hold", "x": 0.15, "y": 0.8, "seconds": 2}, s)
    assert a == {"type": "hold", "x": 0.15, "y": 0.8, "seconds": 2.0}
    assert g.check({"type": "look", "dx": 10}, s)[0] is None        # no mouse on a phone
    a, _ = g.check({"type": "swipe", "x": 0.5, "y": 0.5, "x2": 0.8, "y2": 0.5}, s)
    assert a["x2"] == 0.8


# ── reading the screen and the model ───────────────────────────────────────
def test_a_row_of_buttons_becomes_separate_elements():
    W = types.SimpleNamespace
    line = W(words=[W(text="Play", box=(100, 50, 40, 20)), W(text="Settings", box=(300, 50, 70, 20)),
                    W(text="Create", box=(500, 50, 60, 20)), W(text="New", box=(565, 50, 35, 20))])
    els = brain.elements_from_lines([line, W(words=[W(text="|", box=(0, 0, 2, 2))])])
    assert [e.text for e in els] == ["Play", "Settings", "Create New"]
    assert [e.id for e in els] == [1, 2, 3]


@pytest.mark.parametrize("reply,typ", [
    ('```json\n{"see":"menu","action":{"type":"click","element":2}}\n```', "click"),
    ('Sure! {"action": "key", "key": "ENTER"}', "key"),
    ('{"type": "wait", "seconds": 2}', "wait"),
])
def test_model_replies_in_several_shapes_are_understood(reply, typ):
    d = brain.parse_decision(reply)
    assert d is not None and d.action["type"] == typ


def test_prompt_lists_elements_with_positions_and_history():
    s = screen_of("title")
    step = brain.Step(1, "x", "menu", 'click "Play"', True, False)
    p = brain.build_prompt("Minecraft", "make a world", s, [step], "pc", warning="careful")
    assert '#2 "Play" @ (50%, 36%)' in p
    assert "NO visible change" in p and "WARNING: careful" in p and "never buy anything" in p


def test_vision_model_choice_and_honest_errors(monkeypatch):
    monkeypatch.delenv("TOM_VISION_MODEL", raising=False)
    assert brain.pick_vision_model(["llama3.2:3b", "qwen2.5vl:7b"]) == "qwen2.5vl:7b"
    assert brain.pick_vision_model(["llama3.2:3b"]) == ""
    monkeypatch.setenv("TOM_VISION_MODEL", "llava")
    assert brain.pick_vision_model(["llava:13b", "qwen2.5vl:7b"]) == "llava:13b"
    ok, why = brain.vision_ready(installed=["llama3.2:3b"])
    assert not ok and "ollama pull" in why
    monkeypatch.setattr(brain, "installed_models", lambda *a, **k: None)
    ok, why = brain.vision_ready()
    assert not ok and "Ollama isn't running" in why


# ── Android / BlueStacks over ADB ──────────────────────────────────────────
from tools import android_game  # noqa: E402


class FakeAdb:
    def __init__(self, connectable=("127.0.0.1:5565",), already=()):
        self.calls = []
        self.connected = list(already)
        self.connectable = connectable

    def __call__(self, cmd, timeout=15.0, binary=False):
        self.calls.append(list(cmd))
        args = list(cmd)[1:]
        if args == ["devices"]:
            body = "List of devices attached\n" + "".join(f"{d}\tdevice\n" for d in self.connected)
            return 0, body.encode()
        if args[:1] == ["connect"]:
            if args[1] in self.connectable:
                self.connected.append(args[1])
            return 0, b""
        if "screencap" in args:
            import cv2
            ok, buf = cv2.imencode(".png", np.full((720, 1280, 3), 90, np.uint8))
            return 0, buf.tobytes()
        if "dumpsys" in args:
            return 0, b"mCurrentFocus=Window{1 u0 com.mojang.minecraftpe/com.mojang.minecraftpe.MainActivity}"
        return 0, b""


def test_adb_text_is_escaped_for_the_device_shell():
    assert android_game.text_arg("My World") == "My%sWorld"
    assert android_game.text_arg("/tp ~ ~5 ~") == "/tp%s\\~%s\\~5%s\\~"
    assert android_game.text_arg("it's") == "it\\'s"
    assert android_game.text_arg("100%") is None and android_game.text_arg("namaste 🙏") is None


def test_bluestacks_port_is_found_in_its_config_and_connected():
    fake = FakeAdb(connectable=("127.0.0.1:5565",))
    adb = android_game.Adb("adb", run=fake)
    ok, msg = adb.connect(env={}, read_conf=lambda: 'bst.instance.Pie64.status.adb_port="5565"\n')
    assert ok and adb.serial == "127.0.0.1:5565"
    assert ["adb", "connect", "127.0.0.1:5565"] in fake.calls


def test_an_already_connected_device_is_used_and_env_wins():
    adb = android_game.Adb("adb", run=FakeAdb(already=("emulator-5554",)))
    assert adb.connect(env={})[0] and adb.serial == "emulator-5554"
    fake = FakeAdb(connectable=("10.0.0.5:5555",), already=("emulator-5554",))
    adb = android_game.Adb("adb", run=fake)
    assert adb.connect(env={"BLUESTACKS_ADB": "10.0.0.5:5555"})[0] and adb.serial == "10.0.0.5:5555"


def test_no_adb_explains_how_to_turn_it_on():
    ok, msg = android_game.Adb("", run=FakeAdb()).connect(env={})
    assert not ok and "Android Debug Bridge" in msg
    ok, msg = android_game.Adb("adb", run=FakeAdb(connectable=())).connect(env={}, read_conf=lambda: "")
    assert not ok and "BLUESTACKS_ADB" in msg


def test_adb_backend_taps_exact_pixels_and_reads_the_android_screen():
    fake = FakeAdb(already=("127.0.0.1:5555",))
    adb = android_game.Adb("adb", "127.0.0.1:5555", run=fake)
    be = android_game.AdbBackend(adb, "com.mojang.minecraftpe", read_lines=lambda f: [])
    assert be.ready()
    s = be.observe()
    assert (s.width, s.height) == (1280, 720)
    assert be.act({"type": "click", "x": 0.5, "y": 0.25}, s)[0]
    assert fake.calls[-1][-4:] == ["input", "tap", "640", "180"]
    be.act({"type": "hold", "x": 0.1, "y": 0.8, "seconds": 1.5}, s)
    assert fake.calls[-1][-6:] == ["swipe", "128", "576", "128", "576", "1500"]
    be.act({"type": "type", "text": "My World"}, s)
    assert fake.calls[-1][-2:] == ["text", "My%sWorld"]
    be.act({"type": "key", "key": "BACK"}, s)
    assert fake.calls[-1][-2:] == ["keyevent", "4"]


def test_bluestacks_shortcut_records_the_android_package():
    from tools import game_library

    def read(lnk):
        return (r"C:\Program Files\BlueStacks_nxt\HD-Player.exe",
                "--instance Pie64 --cmd launchApp --package com.mojang.minecraftpe")
    import glob as glob_mod
    folder = os.path.join(os.path.dirname(__file__), "..", ".pytest_tmp", "lnk")
    os.makedirs(folder, exist_ok=True)
    open(os.path.join(folder, "Minecraft.lnk"), "w").close()
    try:
        games = game_library.shortcut_games([folder], read=read)
    finally:
        for f in glob_mod.glob(os.path.join(folder, "*.lnk")):
            os.remove(f)
    assert games[0].launcher == "BlueStacks" and games[0].package == "com.mojang.minecraftpe"


# ── wiring: when the brain is used, and what TOM says ─────────────────────
def test_when_the_brain_drives_and_what_goal_it_gets():
    from tools import game_play
    prof = profile_mod.GameProfile(game="Viper", colors={"player": [1, 2, 3]}, genre="snake")
    assert not game_play.use_brain(prof, "")                       # learned strategy player kept
    assert game_play.use_brain(prof, "get to level 3")
    assert game_play.use_brain(profile_mod.GameProfile(game="Minecraft"), "")
    assert not game_play.use_brain(profile_mod.GameProfile(game="X"), "do it", env={"TOM_GAME_BRAIN": "0"})
    assert "get past any menus" in game_play.brain_goal("play minecraft for me", "Minecraft")
    assert game_play.brain_goal("build a house", "Minecraft") == "build a house"


def test_play_with_brain_saves_what_it_learned(profiles):
    from tools import game_play
    out = game_play.play_with_brain("Minecraft", MenuGame(), "enter a world", seconds=60, think=menu_policy)
    assert out["status"] == "success" and out["played_by"] == "brain" and out["goal_met"]
    saved = profile_mod.load("Minecraft")
    assert saved.lessons and saved.sessions == 1 and saved.goal_met == 1


def test_play_with_brain_without_a_vision_model_says_what_to_install(monkeypatch):
    from tools import game_play
    monkeypatch.setattr(brain, "installed_models", lambda *a, **k: ["llama3.2:3b"])
    out = game_play.play_with_brain("Minecraft", MenuGame(), "enter", seconds=10)
    assert out["status"] == "error" and out["brain_unavailable"] and "ollama pull" in out["message"]


def test_android_route_reports_adb_problems_for_fallback():
    from tools import game_play
    out = game_play.play_android("Minecraft", "", 10, connect=lambda n, p: (None, "no adb"))
    assert out["status"] == "error" and out["adb"] is False
    out = game_play.play_android("Minecraft", "enter a world", 60, think=menu_policy,
                                 connect=lambda n, p: (MenuGame(platform="touch"), "Connected."))
    assert out["adb"] and out["goal_met"] and "Android Debug Bridge" in out["message"]


def test_play_live_hands_an_installed_game_to_the_brain(monkeypatch):
    from tools import game_autopilot, game_library, game_play
    from tom_core.games import studio
    monkeypatch.delenv("TOM_GAME_BRAIN", raising=False)
    monkeypatch.setattr(studio, "find_made_game", lambda name: None)
    monkeypatch.setattr(game_library, "find_game", lambda name: None)
    monkeypatch.setattr(game_autopilot, "find_window", lambda w: (7, "Minecraft"))
    monkeypatch.setattr(game_autopilot, "focus_window", lambda h: True)
    monkeypatch.setattr(game_autopilot, "set_dpi_aware", lambda: None)
    monkeypatch.setattr(game_play, "WindowBackend", lambda hwnd, keys, screen=None: object())
    monkeypatch.setattr(game_play, "BrainWindowBackend", lambda window, autoplay=None: MenuGame())
    out = game_play.play_live("Minecraft", seconds=60, goal="get into a world with cheats on", think=menu_policy)
    assert out["played_by"] == "brain" and out["goal_met"] and out["started"] is False


# ── the agent: a Minecraft task when the game isn't in a world yet ─────────
def _agent_for_minecraft(monkeypatch, prepared, window_after_launch=(9, "Minecraft")):
    import asyncio
    from agent import TomAgent
    from tools import game_autopilot as ga, game_library, game_play, game_tasks
    a = TomAgent.__new__(TomAgent)
    events = {"launched": 0, "ran": [], "prep_goals": []}
    info = game_library.Game("Minecraft", "BlueStacks", "mc.lnk", window="BlueStacks App Player",
                             package="com.mojang.minecraftpe")
    monkeypatch.setattr(game_library, "find_game", lambda q: info)

    async def launch(game):
        events["launched"] += 1
        return {"status": "success", "message": "started"}
    monkeypatch.setattr(game_library, "launch", launch)
    monkeypatch.setattr(ga, "find_window", lambda w: None)
    monkeypatch.setattr(ga, "wait_for_window", lambda w, t, poll=0.5: window_after_launch)
    monkeypatch.setattr(ga, "focus_window", lambda h: True)

    def play_live(game, seconds, stop, model, decide, wait, goal, **kw):
        events["prep_goals"].append(goal)
        return prepared
    monkeypatch.setattr(game_play, "play_live", play_live)
    monkeypatch.setattr(TomAgent, "_autopilot_model", lambda self: "qwen2.5vl:7b")

    def run(plan, driver):
        events["ran"].append(plan.commands)
        return {"status": "success", "replies": [{"kind": "done"}], "message": "Built a house."}
    monkeypatch.setattr(game_tasks, "run_minecraft", run)
    monkeypatch.setattr(game_tasks, "MinecraftDriver", lambda hwnd: object())
    allowed = types.SimpleNamespace(allowed=True)
    monkeypatch.setattr(TomAgent, "_game_gate", lambda self, g, summary, payload: allowed)
    out = asyncio.run(a.execute_game_task({"game": "Minecraft", "task": "build a house"}))
    return out, events


def test_minecraft_not_open_is_started_walked_into_a_world_and_then_built(monkeypatch):
    out, ev = _agent_for_minecraft(monkeypatch, {"status": "success", "goal_met": True, "message": "in the world"})
    assert ev["launched"] == 1 and len(ev["prep_goals"]) == 1
    assert "Activate Cheats" in ev["prep_goals"][0] and "Do NOT turn cheats on in an existing world" in ev["prep_goals"][0]
    assert ev["ran"] and out["status"] == "success" and out["preparation"]["goal_met"]


def test_minecraft_menus_it_cannot_get_through_are_reported_and_nothing_is_typed(monkeypatch):
    out, ev = _agent_for_minecraft(monkeypatch, {"status": "partial", "goal_met": False,
                                                 "message": "Time ran out before the goal."})
    assert out["status"] == "needs_input" and "couldn't get into a world" in out["message"]
    assert ev["ran"] == []
